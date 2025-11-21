# Separated nodes from llm_search.py and external_llm.py
import asyncio
from typing import cast

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from loguru import logger

from graph.common.state import State
from graph.constants import (
    COLOR_EXPERT,
    FITTING_COORDINATOR,
    HISTORY_WINDOW_LARGE,
    HISTORY_WINDOW_MEDIUM,
    HISTORY_WINDOW_SMALL,
    SHOW_CACHED,
    SKIP_STREAM,
    STYLE_ANALYST,
    IntentTypes,
    SSETypes,
    StateName,
    StatusUpdateTypes,
)
from graph.model.api_schema import StatusUpdate
from graph.model.graph_schemas import ClothSearch, UserIntent
from graph.prompt import (
    chatbot_prompt_gathering,
    chatbot_prompt_gathering_unclear,
    chatbot_prompt_search_ready,
    chatbot_prompt_search_ready_unclear,
    extraction_prompt,
    generation_prompt,
    info_qa_prompt,
    intent_prompt_gathering,
    intent_prompt_refinement,
    update_prompt,
)
from graph.utils.messages import create_message
from llm import get_llm_model

# 공통 LLM 설정
llm = get_llm_model('google/gemini-2.5-flash-lite')


extraction_llm = extraction_prompt | llm.with_structured_output(ClothSearch).with_config(tags=[SKIP_STREAM])

generation_llm = generation_prompt | llm

update_llm = (update_prompt | llm.with_structured_output(ClothSearch)).with_config(tags=[SKIP_STREAM])

intent_classifier_gathering_chain = intent_prompt_gathering | llm.with_structured_output(UserIntent).with_config(tags=[SKIP_STREAM])
intent_classifier_refinement_chain = intent_prompt_refinement | llm.with_structured_output(UserIntent).with_config(tags=[SKIP_STREAM])


async def intent_classify_node(state: State):
    """1, 2단계 의도 분류를 통합하여 한 번에 처리하는 노드"""
    logger.info('\n--- 노드 실행: classify_node ---')
    writer = get_stream_writer()
    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(state=StatusUpdateTypes.START, content='의도 분류 시작', task_id='intent_classify').model_dump(),
        },
    )
    user_message = state.get(StateName.USER_MESSAGE)
    is_info_gathering_complete = state.get(StateName.IS_INFO_GATHERING_COMPLETE, False)
    current_search_info = cast(ClothSearch, state.get(StateName.CLOTH_SEARCH, ClothSearch()))

    if is_info_gathering_complete:
        logger.info('- 분류 모드: Refinement (정보 수집 완료)')
        # 입력 데이터에 'cloth_search'를 포함시킵니다.
        input_data_1 = {
            StateName.USER_MESSAGE: user_message,
            StateName.CLOTH_SEARCH: current_search_info.model_dump(),
            # 'is_info_gathering_complete'는 프롬프트 변수가 아니므로 제거해도 됩니다.
        }
        intent_classifier_chain = intent_classifier_refinement_chain
    else:
        logger.info('- 분류 모드: Gathering (정보 수집 중)')
        input_data_1 = {
            StateName.USER_MESSAGE: user_message,
        }
        intent_classifier_chain = intent_classifier_gathering_chain

    # 1단계: 빠른 초벌 분류
    result = cast(
        UserIntent,
        await intent_classifier_chain.ainvoke(input_data_1),  # 수정된 input_data_1 사용
    )
    logger.info(f'1차 분류 결과: {result.intent}')

    # 2단계: unclear시 메시지 길이 기반 적응형 재분류
    if result.intent == IntentTypes.UNCLEAR:
        logger.info('의도가 불분명하여 재분류를 시도합니다.')

        # 메시지 길이로 필요한 컨텍스트 윈도우 결정
        msg_length = len(user_message.strip()) if user_message else 0

        if msg_length <= 5:
            context_window = HISTORY_WINDOW_LARGE
            logger.info(f'초단답 감지 (길이: {msg_length}자) → 확장 컨텍스트 {context_window}개')
        elif msg_length <= 15:
            context_window = HISTORY_WINDOW_MEDIUM
            logger.info(f'짧은 메시지 (길이: {msg_length}자) → 중간 컨텍스트 {context_window}개')
        else:
            context_window = HISTORY_WINDOW_SMALL
            logger.info(f'일반 메시지 (길이: {msg_length}자) → 기본 컨텍스트 {context_window}개')

        # 대화 히스토리에서 컨텍스트 추출
        context = '\n'.join([msg.pretty_repr() for msg in state['messages'][-context_window:]])
        if is_info_gathering_complete:
            input_data_2 = {
                StateName.USER_MESSAGE: context,  # user_message 대신 context 사용
                StateName.CLOTH_SEARCH: current_search_info.model_dump(),
            }
        else:
            input_data_2 = {
                StateName.USER_MESSAGE: context,  # user_message 대신 context 사용
            }

        result = cast(UserIntent, await intent_classifier_chain.ainvoke(input_data_2))
        logger.info(f'2차 분류 결과: {result.intent}')

        # 3단계: 여전히 unclear면 chatbot으로 폴백
        if result.intent == IntentTypes.UNCLEAR:
            logger.warning('2차 분류에서도 unclear - chatbot으로 폴백하여 명확화 유도')
            # writer(
            #     {
            #         'type': SSETypes.STATUS,
            #         'content': StatusUpdate(state=StatusUpdateTypes.END, content='명확화가 필요해요', task_id='intent_classify').model_dump(),
            #     }
            # )
            return {
                StateName.INTENT: IntentTypes.CHATBOT,
                StateName.IS_UNCLEAR_FALLBACK: True,
            }

    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(state=StatusUpdateTypes.END, content='의도 분류 완료', task_id='intent_classify').model_dump(),
        },
    )

    return {
        StateName.INTENT: result.intent,
    }


# --- 정보 수집 관련 노드 ---
async def information_gathering_node(state: State):
    """정보를 수집하고 상태를 업데이트하는 노드"""
    writer = get_stream_writer()
    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(
                state=StatusUpdateTypes.START, content='요청하신 내용을 분석 중이에요...', task_id='information_gathering'
            ).model_dump(),
        },
    )
    logger.info('\n--- 노드 실행: information_gathering_node ---')
    last_user_message = state.get(StateName.USER_MESSAGE)

    logger.info(f"- 정보 추루 LLM 호출: last_user_message: '{last_user_message}'")
    extracted_info = cast(
        ClothSearch,
        await extraction_llm.ainvoke(
            {
                StateName.USER_MESSAGE: last_user_message,
            },
        ),
    )

    current_search_info = cast(ClothSearch, state.get(StateName.CLOTH_SEARCH, ClothSearch()))
    # logger.info(f'- 추출된 정보: {extracted_info}')
    logger.info(f'- current_search_info: {current_search_info}')
    updated_data = {k: v for k, v in extracted_info.model_dump().items() if v is not None and v != ''}
    logger.info(f'- updated_data: {updated_data}')
    if updated_data:
        current_search_info = current_search_info.model_copy(update=updated_data)

    logger.info(f'- 업데이트된 검색 상태: {current_search_info}')

    missing_fields = [field for field, value in current_search_info.model_dump().items() if value is None]

    updates = {StateName.CLOTH_SEARCH: current_search_info}
    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(state=StatusUpdateTypes.END, content='요청하신 내용을 분석했어요!', task_id='information_gathering').model_dump(),
        },
    )
    if not missing_fields:
        logger.info('- 모든 정보 수집 완료')
        updates[StateName.IS_INFO_GATHERING_COMPLETE] = True
    else:
        logger.info(f'- 부족한 정보: {missing_fields}')

        # 수집된 정보를 사람이 읽기 좋게 변환
        collected_data = {k: v for k, v in current_search_info.model_dump().items() if v is not None}

        # 수집된 정보가 있으면 포맷팅, 없으면 "없음"
        collected_info_str = '\n'.join([f'- {k}: {v}' for k, v in collected_data.items()]) if collected_data else '(아직 수집된 정보가 없습니다)'

        generation_response = await generation_llm.ainvoke(
            {
                'missing_fields': ', '.join(missing_fields),
                'collected_info': collected_info_str,
            }
        )
        updates[StateName.MESSAGES] = [create_message(message_type='ai', content=generation_response.content)]
        updates[StateName.IS_INFO_GATHERING_COMPLETE] = False

    return updates


# 새로운 정보 업데이트 노드
async def information_update_node(state: State):
    """기존 검색 조건을 사용자의 피드백에 따라 수정하는 노드"""
    logger.info('\n--- 노드 실행: information_update_node ---')
    writer = get_stream_writer()
    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(state=StatusUpdateTypes.START, content='검색 조건을 수정 중이에요...', task_id='information_update').model_dump(),
        },
    )
    user_message = state.get(StateName.USER_MESSAGE)
    current_search_info = cast(ClothSearch, state.get(StateName.CLOTH_SEARCH))

    logger.info(f'- 기존 검색 조건: {current_search_info.model_dump_json(indent=2)}')
    logger.info(f"- LLM (수정) 호출: '{user_message}'")

    # LLM을 호출하여 어떤 정보를 업데이트할지 판단
    updated_info = cast(
        ClothSearch,
        await update_llm.ainvoke(
            {
                'existing_search_criteria': current_search_info.model_dump(),
                'user_message': user_message,
            }
        ),
    )
    logger.info(f'- LLM이 반환한 수정 정보: {updated_info}')

    update_data = {k: v for k, v in updated_info.model_dump().items() if v is not None}

    # 조건 변경 없음 = 이전 검색 결과로 부터 빠르게 다음 이미지 보여주기
    if not update_data:
        logger.info('- 변경된 정보가 없으므로 => 이전 검색 결과로 부터 다음 인덱스 검색 결과 출력')
        writer(
            {
                'type': SSETypes.STATUS,
                'content': StatusUpdate(state=StatusUpdateTypes.END, content='다음 결과를 불러올게요!', task_id='information_update').model_dump(),
            }
        )
        return {
            StateName.LAST_UPDATED_FIELDS: [SHOW_CACHED],
        }

    final_search_info = current_search_info.model_copy(update=update_data)
    logger.info(f'- 최종 업데이트된 검색 조건: {final_search_info.model_dump_json(indent=2)}')
    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(state=StatusUpdateTypes.END, content='검색 조건을 수정했어요!', task_id='information_update').model_dump(),
        },
    )

    return {
        StateName.CLOTH_SEARCH: final_search_info,
        StateName.LAST_UPDATED_FIELDS: list(update_data.keys()),
        StateName.EXPERT_SEARCH_CACHE: {},  # 캐시 초기화
        StateName.SHOWN_IN_PRODUCT_IDS: set(),  # shown_ids 초기화
        StateName.EXPERT_OFFSETS: {
            COLOR_EXPERT: 0,
            STYLE_ANALYST: 0,
            FITTING_COORDINATOR: 0,
        },
    }


async def handle_inappropriate_node(state: State, config: RunnableConfig):
    """부적절한 질문 처리 노드"""
    logger.info('\n--- 노드 실행: handle_inappropriate_node ---')
    writer = get_stream_writer()
    response = '죄송합니다. 해당 질문에는 답변해 드릴 수 없습니다. 의류 추천과 관련하여 도움이 필요하시면 말씀해주세요.'

    # content를 청크 단위로 나누어 토큰 스트리밍
    chunk_size = 8
    for i in range(0, len(response), chunk_size):
        chunk = response[i : i + chunk_size]
        writer({'type': SSETypes.TOKEN, 'content': chunk})
        await asyncio.sleep(0.1)  # 0.1초 대기

    return {
        StateName.MESSAGES: [create_message(message_type='ai', content=response)],
    }


async def info_qa_node(state: State):
    """정보 질문 처리 노드 - 연속 질문 대응"""
    logger.info('\n--- 노드 실행: info_qa_node ---')

    # 최근 5개 메시지 전달 (정보 질문은 보통 짧은 연속 대화)
    recent_messages = state.get(StateName.MESSAGES, [])[-HISTORY_WINDOW_MEDIUM:]

    # 실제 구현 시에는 웹 검색 등의 도구를 사용하여 전문적인 답변 제공
    chain = info_qa_prompt | llm
    response = await chain.ainvoke(
        {
            'messages': recent_messages,
            StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE),
        }
    )
    return {
        StateName.MESSAGES: [create_message(message_type='ai', content=response.content)],
    }


async def chatbot(state: State, config: RunnableConfig) -> dict:
    """일상 대화 처리, 검색 복귀 유도, 불명확한 의도 명확화"""
    logger.info('\n--- 노드 실행: chatbot ---')

    recent_messages = state.get(StateName.MESSAGES, [])[-HISTORY_WINDOW_LARGE:]

    # cloth_search 상태도 함께 전달
    cloth_search = state.get(StateName.CLOTH_SEARCH.value)
    cloth_search_info = cloth_search.model_dump() if cloth_search else {}

    is_gathering_complete = state.get(StateName.IS_INFO_GATHERING_COMPLETE, False)

    # 1순위: UNCLEAR 상황인지 먼저 체크
    is_unclear_fallback = state.get(StateName.IS_UNCLEAR_FALLBACK, False)

    if is_gathering_complete:
        if is_unclear_fallback:
            logger.info('UNCLEAR 상화 모드 (Search Ready)')
            chain = chatbot_prompt_search_ready_unclear | llm
            input_data = {
                'messages': recent_messages,
                StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE),
                'cloth_search': cloth_search_info,
            }
        else:
            # ✅ 상황 2: 검색 준비 완료 (2번째 목적)
            logger.info('검색 준비 완료 모드')
            chain = chatbot_prompt_search_ready | llm
            input_data = {
                'messages': recent_messages,
                StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE),
                'cloth_search': cloth_search_info,
            }
    else:
        missing_fields = [f for f, v in cloth_search_info.items() if v is None] if cloth_search_info else []
        if is_unclear_fallback:
            logger.info('UNCLEAR 상황 모드 (Gathering)')
            chain = chatbot_prompt_gathering_unclear | llm
            input_data = {
                'messages': recent_messages,
                StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE),
                'cloth_search': cloth_search_info,
                'missing_fields': missing_fields,
            }
        else:
            logger.info('정보 수집 중 모드')
            chain = chatbot_prompt_gathering | llm
            input_data = {
                'messages': recent_messages,
                StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE),
                'cloth_search': cloth_search_info,
                'missing_fields': missing_fields,
            }

    response = await chain.ainvoke(input_data)

    # 중요: 사용한 fallback 플래그는 응답 후 반드시 초기화
    if is_unclear_fallback:
        return {
            StateName.MESSAGES: [create_message(message_type='ai', content=response.content)],
            StateName.IS_UNCLEAR_FALLBACK: False,
        }
    else:
        return {
            StateName.MESSAGES: [create_message(message_type='ai', content=response.content)],
        }


# TODO: 반환할 state 수정 필요 (utils.py의 get_inital_state와 비교해서 수정필요)
# CHECK : 여기서 미리 만들어진 템플릿으로 부터 필요한 정보를 parsing 해야 한다면 information_gathering_node로 이동해야 하고, 아니면 바로 search_node로 이동가능 ?
def prepare_template_search_node(state: State) -> dict:
    """미리 정의된 템플릿 검색을 위한 상태를 준비하는 노드"""
    logger.info('\n--- 노드 실행: prepare_template_search_node ---')
    return {
        StateName.IS_INFO_GATHERING_COMPLETE: True,
        StateName.CLOTH_SEARCH: ClothSearch(),  # 빈 ClothSearch 모델로 초기화
    }


async def prepare_search_message_node(state: State) -> dict:
    """검색 서브그래프에 진입하기 전, 사용자에게 전달할 메시지를 생성하는 노드"""
    logger.info('\n--- 노드 실행: prepare_search_message_node ---')
    writer = get_stream_writer()

    last_updated_fields = state.get(StateName.LAST_UPDATED_FIELDS, [])

    # Case 1: "다른거 보여줘" 요청 시 (캐시 활용)
    if SHOW_CACHED in last_updated_fields:
        message_content = '네, 다른 코디를 찾아볼게요!'

        # content를 청크 단위로 나누어 토큰 스트리밍
        chunk_size = 5
        for i in range(0, len(message_content), chunk_size):
            chunk = message_content[i : i + chunk_size]
            writer({'type': SSETypes.TOKEN, 'content': chunk})
            await asyncio.sleep(0.1)  # 0.1초 대기

        message = create_message(message_type='ai', content=message_content)

    # Case 2: 새로운 검색 또는 조건 변경 시
    else:
        cloth_search = state.get(StateName.CLOTH_SEARCH)
        if cloth_search:
            # cloth_search 객체에서 사람이 읽기 좋은 형태로 변환
            criteria = []
            if cloth_search.tpo:
                criteria.append(f"'{cloth_search.tpo}' 상황에 어울리는")
            if cloth_search.style:
                criteria.append(f"'{cloth_search.style}' 스타일의")
            if cloth_search.color:
                criteria.append(f"'{cloth_search.color}' 색상을 활용한")

            criteria_str = ' '.join(criteria)
            message_content = f'알겠습니다! {criteria_str} 코디를 찾아볼게요. 잠시만 기다려주세요.'

            # content를 청크 단위로 나누어 토큰 스트리밍
            chunk_size = 10
            for i in range(0, len(message_content), chunk_size):
                chunk = message_content[i : i + chunk_size]
                writer({'type': SSETypes.TOKEN, 'content': chunk})
                await asyncio.sleep(0.1)  # 0.1초 대기

            message = create_message(message_type='ai', content=message_content)
        else:
            # 혹시 모를 예외 상황
            return {}

    return {StateName.MESSAGES: [message]}
