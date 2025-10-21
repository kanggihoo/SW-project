# Separated nodes from llm_search.py and external_llm.py
from typing import cast

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from loguru import logger

from graph.common.state import State
from graph.constants import (
    COLOR_EXPERT,
    FITTING_COORDINATER,
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
from graph.prompt import chatbot_prompt, extraction_prompt, generation_prompt, info_qa_prompt, intent_classifier_prompt, update_prompt
from graph.utils.messages import create_message
from llm import get_llm_model

# 공통 LLM 설정
llm = get_llm_model('google/gemini-2.5-flash-lite')


intent_classifier_chain = intent_classifier_prompt | llm.with_structured_output(UserIntent).with_config(tags=[SKIP_STREAM])

extraction_llm = extraction_prompt | llm.with_structured_output(ClothSearch).with_config(tags=[SKIP_STREAM])

generation_llm = generation_prompt | llm

update_llm = update_prompt | llm.with_structured_output(ClothSearch)


async def intent_classify_node(state: State):
    """1, 2단계 의도 분류를 통합하여 한 번에 처리하는 노드"""
    logger.info('\n--- 노드 실행: unified_classify_node ---')
    writer = get_stream_writer()
    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(state=StatusUpdateTypes.START, content='의도 분류 시작', task_id='intent_classify').model_dump(),
        },
    )
    user_message = state.get(StateName.USER_MESSAGE)
    is_info_gathering_complete = state.get(StateName.IS_INFO_GATHERING_COMPLETE, False)

    # 1단계: 빠른 초벌 분류
    result = cast(
        UserIntent,
        await intent_classifier_chain.ainvoke(
            {
                StateName.USER_MESSAGE: user_message,
                StateName.IS_INFO_GATHERING_COMPLETE: is_info_gathering_complete,
            }
        ),
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

        result = cast(
            UserIntent,
            await intent_classifier_chain.ainvoke(
                {
                    StateName.USER_MESSAGE: context,
                    StateName.IS_INFO_GATHERING_COMPLETE: is_info_gathering_complete,
                }
            ),
        )
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
            return {StateName.INTENT: IntentTypes.CHATBOT}

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

    logger.info(f"- LLM (추출) 호출: '{last_user_message}'")
    extracted_info = cast(
        ClothSearch,
        await extraction_llm.ainvoke(
            {
                StateName.USER_MESSAGE: last_user_message,
            },
        ),
    )

    current_search_info = cast(ClothSearch, state.get(StateName.CLOTH_SEARCH, ClothSearch()))
    logger.info(f'- 추출된 정보: {extracted_info}')
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
                StateName.USER_NAME: state.get(StateName.USER_NAME),
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
            FITTING_COORDINATER: 0,
        },
    }


def handle_inappropriate_node(state: State):
    """부적절한 질문 처리 노드"""
    logger.info('\n--- 노드 실행: handle_inappropriate_node ---')
    response = '죄송합니다. 해당 질문에는 답변해 드릴 수 없습니다. 의류 추천과 관련하여 도움이 필요하시면 말씀해주세요.'
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
    """일상 대화 처리 및 검색으로 복귀 유도"""
    logger.info('\n--- 노드 실행: chatbot ---')

    # 대화 히스토리 전달 (최근 7개)
    recent_messages = state.get(StateName.MESSAGES, [])[-HISTORY_WINDOW_LARGE:]

    # cloth_search 상태도 함께 전달
    cloth_search = state.get(StateName.CLOTH_SEARCH.value)
    cloth_search_info = cloth_search.model_dump() if cloth_search else {}

    is_gathering_complete = state.get(StateName.IS_INFO_GATHERING_COMPLETE, False)

    chain = chatbot_prompt | llm
    response = await chain.ainvoke(
        {
            'messages': recent_messages,
            StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE),
            'cloth_search': cloth_search_info,
            'is_gathering_complete': is_gathering_complete,
        },
    )
    return {
        StateName.MESSAGES: [create_message(message_type='ai', content=response.content)],
    }


# TODO: 반환할 state 수정 필요 (utils.py의 get_inital_state와 비교해서 수정필요)
def prepare_template_search_node(state: State) -> dict:
    """미리 정의된 템플릿 검색을 위한 상태를 준비하는 노드"""
    logger.info('\n--- 노드 실행: prepare_template_search_node ---')
    return {
        StateName.IS_INFO_GATHERING_COMPLETE: True,
        StateName.CLOTH_SEARCH: ClothSearch(),  # 빈 ClothSearch 모델로 초기화
    }
