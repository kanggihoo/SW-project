# Separated nodes from llm_search.py and external_llm.py
import json
from typing import cast

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from loguru import logger

from db.services.search import SearchService
from graph.common.state import State
from graph.common.utils import external_streaming_llm
from graph.constants import (
    COLOR_EXPERT,
    CONFIG,
    FITTING_COORDINATER,
    HTTP_SESSION,
    SEARCH_SERVICE,
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
    chatbot_prompt,
    extraction_prompt,
    generation_prompt,
    info_qa_prompt,
    intent_classifier_prompt,
    update_prompt,
)
from graph.utils.messages import create_message
from llm import get_llm_model


async def external_llm_node(state: State, config: RunnableConfig) -> dict:
    """외부 LLM 스트리밍 결과를 반환하는 노드 - 사용자 입력을 분석하여 검색 쿼리 생성"""
    host = 'https://the-first-take.com'
    path = 'llm/api/expert/single/stream'
    api_endpoint = f'{host}/{path}'

    text = state[StateName.USER_MESSAGE.value]
    current_expert = state.get(StateName.CURRENT_EXPERT.value)
    writer = get_stream_writer()
    response_text = ''

    content = StatusUpdate(state=StatusUpdateTypes.START, content=f'{current_expert} 의류 조합 분석 시작', task_id=current_expert).model_dump()
    writer({'type': SSETypes.STATUS.value, 'content': content})

    try:
        async for chunk in external_streaming_llm(
            text,
            api_endpoint,
            http_session=config.get(CONFIG, {}).get(HTTP_SESSION),
            expert_type=current_expert,
        ):
            chunk = chunk.strip()
            if chunk.startswith('data: '):
                data = chunk[6:]
                parsed = json.loads(data)
                # logger.info(f'parsed: {parsed}')
                match parsed['type']:
                    case SSETypes.TOKEN:
                        response_text += parsed['content']
                        writer({'type': SSETypes.TOKEN, 'content': parsed['content']})
                    case SSETypes.STATUS:
                        writer({'type': SSETypes.STATUS, 'content': parsed['content']})
                    case SSETypes.END:
                        content = StatusUpdate(
                            state=StatusUpdateTypes.END,
                            content=f'{current_expert} 분석 완료',
                            task_id=current_expert,
                        ).model_dump()
                        writer({'type': SSETypes.STATUS, 'content': content})
                        break
    except Exception as e:
        logger.error(f'Error in external external_llm_node : {e}', exc_info=True)
        response_text = '의류 분석 중 오류가 발생했습니다.'
        content = StatusUpdate(
            state=StatusUpdateTypes.ERROR,
            content=f'{current_expert} 분석 오류',
            task_id=current_expert,
            error_details=str(e),
        ).model_dump()
        writer({'type': SSETypes.STATUS.value, 'content': content})

    # dict로 반환하여 전문가별 의견 누적 저장
    current_opinions = state.get(StateName.EXPERT_OPINIONS.value, {})
    current_opinions[current_expert] = response_text
    return {StateName.EXPERT_OPINIONS: current_opinions}


async def search_node(state: State, config: RunnableConfig) -> dict:
    """외부 LLM 결과를 기반으로 벡터 검색을 수행하는 노드"""
    writer = get_stream_writer()
    writer(
        {
            'type': SSETypes.STATUS.value,
            'content': StatusUpdate(state=StatusUpdateTypes.START, content='이미지 검색 시작', task_id='search').model_dump(),
        }
    )

    expert_opinions = state[StateName.EXPERT_OPINIONS.value]
    current_expert = state[StateName.CURRENT_EXPERT.value]
    current_expert_opinion = expert_opinions.get(current_expert, '')
    search_service: SearchService = config.get(CONFIG, {}).get(SEARCH_SERVICE, '')
    try:
        # TODO : 반환된 값에 대한 리랭킹 필요(K개 반환, Fallback 처리)
        # TODO : K는 config에 담아서 제공
        search_result = await search_service.search_by_query(current_expert_opinion, limit=5)

        writer(
            {
                'type': SSETypes.STATUS.value,
                'content': StatusUpdate(state=StatusUpdateTypes.END, content='이미지 검색 완료!', task_id='search').model_dump(),
            }
        )
        cached_results = {
            'TOP': [],
            'BOTTOM': [],
        }
        product_ids = {
            'TOP': None,
            'BOTTOM': None,
        }
        if search_result and 'data' in search_result:
            for item in search_result['data']:
                product_id = item.get('product_id').strip()
                main_category = item.get('main_category')

                if main_category == 'TOP' and product_ids.get('TOP') is None:
                    product_ids['TOP'] = product_id
                elif main_category == 'BOTTOM' and product_ids.get('BOTTOM') is None:
                    product_ids['BOTTOM'] = product_id
                else:
                    cached_results[main_category].append(product_id)
        else:
            raise ValueError(f'Search result is empty | search_result: {search_result}')

        # CHECK : 메타 데이터에 대한 구조 지정? , 보여준 데이터 업데이트 필요 (SHOWN_IN_PRODUCT_IDS 업데이트 해야할듯)
        metadata = {'type': 'refer', 'expert_type': current_expert, 'product_ids': [product_ids.get('TOP'), product_ids.get('BOTTOM')]}

        updated_cache = state.get(StateName.EXPERT_SEARCH_CACHE.value, {})
        updated_cache[current_expert] = cached_results

        search_result_message = create_message(message_type='ai', content=current_expert_opinion, metadata=metadata)
        return {
            StateName.MESSAGES: [search_result_message],
            StateName.EXPERT_SEARCH_CACHE: updated_cache,
        }

    except Exception as e:
        logger.error(f'Error in search node: {e}', exc_info=True)
        writer(
            {
                'type': SSETypes.STATUS,
                'content': StatusUpdate(
                    state=StatusUpdateTypes.ERROR,
                    content='이미지 검색 오류',
                    task_id='search',
                    error_details=str(e),
                ).model_dump(),
            }
        )

        error_message = create_message(message_type='ai', content='이미지 검색 중 오류가 발생했습니다.')

        return {StateName.MESSAGES: [error_message]}


# async def call_external_llm_node(state: State, config: RunnableConfig):
#     """외부 LLM 스트리밍 결과를 반환하는 노드"""
#     text = state[StateName.MESSAGES.value][-1].content
#     api_endpoint = config.get(CONFIG, {}).get(API_ENDPOINT, '')
#     if api_endpoint is None:
#         raise ValueError('api_endpoint is required')

#     http_session = config.get('configurable', {}).get('http_session')
#     if http_session is None:
#         raise ValueError('http_session is required')

#     writer = get_stream_writer()
#     response_text = ''
#     # TODO : 각 전문가 연결
#     # color_expert, fitting_coordinater, style_anal
#     external_agent_name = state['current_expert']

#     content = StatusUpdate(
#         state='start',
#         content=f'{external_agent_name} 의류 조합 분석 시작',
#         task_id=external_agent_name,
#     ).model_dump()
#     writer({'type': SSETypes.STATUS.value, 'content': content})

#     async for chunk in external_streaming_llm(
#         text,
#         api_endpoint=api_endpoint,
#         http_session=http_session,
#         expert_type=external_agent_name,
#     ):
#         chunk = chunk.strip()
#         if chunk.startswith('data: '):
#             data = chunk[6:]
#             parsed = json.loads(data)
#             match parsed['type']:
#                 case SSETypes.TOKEN.value:
#                     response_text += parsed['content']
#                     writer({'type': SSETypes.TOKEN.value, 'content': parsed['content']})
#                 case SSETypes.STATUS.value:
#                     writer({'type': SSETypes.STATUS.value, 'content': parsed['content']})
#                 case SSETypes.END.value:
#                     content = StatusUpdate(
#                         state='end',
#                         content=f'{external_agent_name} 분석 완료',
#                         task_id=external_agent_name,
#                     ).model_dump()
#                     writer({'type': SSETypes.STATUS.value, 'content': content})

#     return {
#         'messages': [create_message(message_type='ai', content=response_text)],
#         'metadata': 'external_llm_response',
#     }


# product_info_agent = create_react_agent(
#     model=model,
#     tools=[product_info],
#     prompt='You are a product info agent. You are given a product name and you need to fetch the product information.',
#     name=NodeName.PRODUCT_INFO_AGENT,
# )
# LLM 1: 의도 분류기


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

    # 2단계: 불분명 시 심층 재분류
    if result.intent == IntentTypes.UNCLEAR:
        logger.info('의도가 불분명하여 재분류를 시도합니다.')
        context = '\n'.join([msg.pretty_repr() for msg in state['messages'][-3:]])
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
    writer(
        {
            'type': SSETypes.STATUS,
            'content': StatusUpdate(state=StatusUpdateTypes.END, content='의도 분류 완료', task_id='intent_classify').model_dump(),
        },
    )

    return {StateName.INTENT: result.intent}


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
    extracted_info = cast(ClothSearch, await extraction_llm.ainvoke({StateName.USER_MESSAGE: last_user_message}))

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
        logger.info('- LLM (질문 생성) 호출')
        generation_response = await generation_llm.ainvoke(
            {'missing_fields': ', '.join(missing_fields), StateName.USER_NAME: state.get(StateName.USER_NAME)}
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


async def pop_next_expert_node(state: State, config: RunnableConfig) -> dict:
    """전문가 리스트에서 다음 전문가를 꺼내 'current_expert'로 설정"""
    experts_to_run = state[StateName.EXPERTS_TO_RUN.value]
    if not isinstance(experts_to_run, list) or len(experts_to_run) == 0:
        raise ValueError('experts_to_run is required')

    current_expert = experts_to_run.pop(0)
    logger.info(f' (이번 실행 전문가: {current_expert})')
    return {
        StateName.CURRENT_EXPERT: current_expert,
        StateName.EXPERTS_TO_RUN: experts_to_run,
    }


async def get_cached_item_node(state: State) -> dict:
    """캐시에서 다음으로 보여줄, 중복되지 않는 상품을 찾는 노드

    prepare_cache_cycle_node에서 offset을 "보여줄 상품의 인덱스"로 설정했으므로
    해당 offset의 TOP, BOTTOM 상품을 가져오기만 함
    """
    current_expert = state[StateName.CURRENT_EXPERT.value]
    expert_cache = state.get(StateName.EXPERT_SEARCH_CACHE.value, {})
    expert_offsets = state.get(StateName.EXPERT_OFFSETS.value, {})
    shown_ids = state.get(StateName.SHOWN_IN_PRODUCT_IDS.value, set())
    expert_opinions = state.get(StateName.EXPERT_OPINIONS.value, {})

    # 현재 전문가의 캐시와 오프셋 가져오기
    current_offset = expert_offsets.get(current_expert, 0)
    cached_by_category = expert_cache.get(current_expert, {})

    top_list = cached_by_category.get('TOP', [])
    bottom_list = cached_by_category.get('BOTTOM', [])

    # prepare에서 설정한 offset 위치의 상품 가져오기
    top_product_id = top_list[current_offset] if current_offset < len(top_list) else None
    bottom_product_id = bottom_list[current_offset] if current_offset < len(bottom_list) else None

    # shown_ids에 추가
    if top_product_id:
        shown_ids.add(top_product_id)
    if bottom_product_id:
        shown_ids.add(bottom_product_id)

    metadata = {'type': 'refer', 'expert_type': current_expert, 'product_ids': [top_product_id, bottom_product_id]}

    # 전문가 의견을 content로 사용 (있으면), 없으면 빈 문자열
    content = expert_opinions.get(current_expert, '')
    response = create_message(message_type='ai', content=content, metadata=metadata)

    return {
        StateName.MESSAGES: [response],
        StateName.SHOWN_IN_PRODUCT_IDS: shown_ids,
    }


def send_refinement_prompt_node(state: State) -> dict:
    """더 이상 보여줄 캐시 아이템이 없을 때 사용자에게 안내 메시지를 보내는 노드"""
    logger.debug('\n--- 노드 실행: send_refinement_prompt_node ---')
    message = create_message(
        message_type='ai',
        content='추천해 드릴 만한 다른 상품을 모두 보여드렸어요. 원하시는 스타일이 있다면 더 자세히 알려주시겠어요? 새로운 조건으로 다시 찾아볼게요!',
    )
    return {StateName.MESSAGES: [message]}


def handle_inappropriate_node(state: State):
    """부적절한 질문 처리 노드"""
    logger.info('\n--- 노드 실행: handle_inappropriate_node ---')
    response = '죄송합니다. 해당 질문에는 답변해 드릴 수 없습니다. 의류 추천과 관련하여 도움이 필요하시면 말씀해주세요.'
    response = create_message(message_type='ai', content=response)
    return {StateName.MESSAGES: [response]}


async def info_qa_node(state: State):
    """정보 질문 처리 노드 (플레이스홀더)"""
    logger.info('\n--- 노드 실행: info_qa_node ---')
    # 실제 구현 시에는 웹 검색 등의 도구를 사용하여 전문적인 답변 제공
    chain = info_qa_prompt | llm
    response = await chain.ainvoke({StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE)})
    response = create_message(message_type='ai', content=response.content)
    return {StateName.MESSAGES: [response]}


async def chatbot(state: State, config: RunnableConfig) -> dict:
    chain = chatbot_prompt | llm
    response = await chain.ainvoke({StateName.USER_MESSAGE: state.get(StateName.USER_MESSAGE)})
    response = create_message(message_type='ai', content=response.content)
    return {StateName.MESSAGES: [response]}


def test_search_node(state: State):
    """최종 검색 실행 노드"""
    logger.info('\n--- 노드 실행: search_node ---')
    search_info = state['cloth_search']
    search_result_message = f'검색을 시작합니다: {search_info.model_dump_json(indent=2)}'
    logger.info(search_result_message)
    return {StateName.MESSAGES: [AIMessage(content=search_result_message)]}


def prepare_cache_cycle_node(state: State) -> dict:
    """캐시 순환 준비 - 순환 가능 여부 확인 및 State 업데이트

    캐시 구조: {'expert_name': {'TOP': [product_id1, ...], 'BOTTOM': [product_id2, ...]}}
    각 전문가가 TOP과 BOTTOM 둘 다 보여줄 수 있어야 순환 가능 (전체 중단 구조)
    """
    logger.info('\n--- 노드: prepare_cache_cycle ---')

    expert_cache = state.get(StateName.EXPERT_SEARCH_CACHE.value, {})
    expert_offsets = state.get(StateName.EXPERT_OFFSETS.value, {})
    shown_ids = state.get(StateName.SHOWN_IN_PRODUCT_IDS.value, set())

    expert_names_with_cache = list(expert_cache.keys())
    planned_items = set()
    updated_offsets = expert_offsets.copy()
    can_cycle = True

    # 순환 가능 여부 확인 및 offset 업데이트
    for expert_name in expert_names_with_cache:
        cached_by_category = expert_cache.get(expert_name, {})
        top_list = cached_by_category.get('TOP', [])
        bottom_list = cached_by_category.get('BOTTOM', [])

        current_offset = updated_offsets.get(expert_name, 0)
        found_pair = False

        # 현재 offset부터 시작하여 TOP과 BOTTOM 둘 다 보여줄 수 있는 쌍 찾기
        while current_offset < min(len(top_list), len(bottom_list)):
            top_product_id = top_list[current_offset]
            bottom_product_id = bottom_list[current_offset]

            # 둘 다 중복이 아닌지 확인
            top_ok = top_product_id not in shown_ids and top_product_id not in planned_items
            bottom_ok = bottom_product_id not in shown_ids and bottom_product_id not in planned_items

            if top_ok and bottom_ok:
                # 둘 다 보여줄 수 있음
                found_pair = True
                planned_items.add(top_product_id)
                planned_items.add(bottom_product_id)
                updated_offsets[expert_name] = current_offset
                logger.info(f'  - {expert_name}: offset={current_offset}에서 쌍 발견')
                break

            # 중복이 있으면 다음 인덱스로
            current_offset += 1

        if not found_pair:
            logger.info(f'- {expert_name}: 보여줄 수 있는 TOP-BOTTOM 쌍 없음 → 순환 불가')
            can_cycle = False
            break

    logger.info(f'- 캐시 순환 가능 여부: {can_cycle}')

    # State 업데이트 반환
    return {
        StateName.EXPERT_OFFSETS: updated_offsets,
        StateName.EXPERTS_TO_RUN: expert_names_with_cache if can_cycle else [],
        StateName.CACHE_CYCLABLE: can_cycle,  # 라우터에서 사용할 플래그
    }


def prepare_search_cycle_node(state: State) -> dict:
    """최초 검색 준비 - 3개 전문가 설정"""
    logger.info('\n--- 노드: prepare_search_cycle ---')
    changed_fields = state.get(StateName.LAST_UPDATED_FIELDS, [])

    if not changed_fields:
        logger.info('- 최초 검색 -> 전문가 전체 호출')
        experts_to_run = [COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATER]
        return {
            StateName.EXPERTS_TO_RUN: experts_to_run,
        }
    else:
        experts_set = set()
        # 색상만 변경
        if 'color' in changed_fields and len(changed_fields) == 1:
            experts_set.add(COLOR_EXPERT)
            logger.info('  → color_expert만 실행')

        # 스타일만 변경
        elif 'style' in changed_fields and len(changed_fields) == 1:
            experts_set.add(STYLE_ANALYST)
            logger.info('  → style_analyst만 실행')

        # TPO 변경 또는 복합 변경 -> 전체 재평가
        elif 'tpo' in changed_fields or len(changed_fields) > 1:
            experts_set.update([COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATER])
            logger.info('  → 전체 전문가 재평가')
        else:
            experts_set.update([COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATER])
            logger.info('  → 기본: 전체 전문가 실행')

        experts_to_run = list(experts_set)
        logger.info(f'  (실행할 전문가 목록: {experts_to_run})')

        return {
            StateName.EXPERTS_TO_RUN: experts_to_run,
        }
