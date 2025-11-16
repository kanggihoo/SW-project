import json

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from loguru import logger

from db.services.search import SearchService
from graph.common.state import State
from graph.common.utils import external_streaming_llm
from graph.constants import (
    COLOR_EXPERT,
    CONFIG,
    FITTING_COORDINATOR,
    HTTP_SESSION,
    SEARCH_SERVICE,
    STYLE_ANALYST,
    SSETypes,
    StateName,
    StatusUpdateTypes,
)
from graph.model.api_schema import StatusUpdate
from graph.utils.messages import create_message


def _build_cache_from_search_results(search_data: list, shown_ids: set) -> dict:
    """검색 결과를 캐시로 구성 (중복 제거)"""
    cached_results = {'TOP': [], 'BOTTOM': []}
    for item in search_data:
        product_id = item.get('product_id', '').strip()
        main_category = item.get('main_category')
        if product_id and product_id not in shown_ids:
            cached_results[main_category].append(product_id)
    return cached_results


def _update_cache_and_offsets(state: State, current_expert: str, cached_results: dict) -> tuple:
    """캐시와 오프셋을 업데이트하고 반환"""
    updated_cache = state.get(StateName.EXPERT_SEARCH_CACHE.value, {})
    updated_cache[current_expert] = cached_results

    updated_offsets = state.get(StateName.EXPERT_OFFSETS.value, {})
    updated_offsets[current_expert] = 0

    return updated_cache, updated_offsets


def _create_outfit_message(
    current_expert: str,
    current_expert_opinion: str,
    first_top: str,
    first_bottom: str,
):
    """코디 메시지를 생성"""
    metadata = {'type': 'refer', 'expert_type': current_expert, 'product_ids': [first_top, first_bottom]}
    return create_message(message_type='ai', content=current_expert_opinion, metadata=metadata)


async def run_expert_evaluation_node(state: State, config: RunnableConfig) -> dict:
    """외부 LLM 스트리밍 결과를 반환하는 노드 - 사용자 입력을 분석하여 검색 쿼리 생성"""
    host = 'https://the-first-take.com'
    path = 'llm/api/expert/single/stream'
    api_endpoint = f'{host}/{path}'

    # text = state[StateName.USER_MESSAGE.value]
    text = state.get(StateName.CLOTH_SEARCH.value).tpo
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
                        writer(
                            {
                                'type': SSETypes.STATUS,
                                'content': content,
                            }
                        )
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
        writer(
            {
                'type': SSETypes.STATUS.value,
                'content': content,
            },
        )

    # dict로 반환하여 전문가별 의견 누적 저장
    current_opinions = state.get(StateName.EXPERT_OPINIONS.value, {})
    current_opinions[current_expert] = response_text
    return {
        StateName.EXPERT_OPINIONS: current_opinions,
    }


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
        search_limit = config.get(CONFIG, {}).get('search_limit', 5)
        fallback_delta = config.get(CONFIG, {}).get('search_limit_fallback_delta', 3)

        search_result = await search_service.search_by_query(current_expert_opinion, limit=search_limit)

        writer(
            {
                'type': SSETypes.STATUS.value,
                'content': StatusUpdate(state=StatusUpdateTypes.END, content='이미지 검색 완료!', task_id='search').model_dump(),
            }
        )

        # 중복 제거하며 캐시 구성
        shown_ids = state.get(StateName.SHOWN_IN_PRODUCT_IDS.value, set())
        cached_results = _build_cache_from_search_results(search_result['data'], shown_ids)
        total_results = len(search_result['data'])

        # 캐시 상태 로깅
        logger.info(
            f'{current_expert} 검색 결과: '
            f'전체 {total_results}개, '
            f'중복 제거 후 TOP {len(cached_results["TOP"])}개, '
            f'BOTTOM {len(cached_results["BOTTOM"])}개'
        )

        # 캐시 업데이트
        updated_cache, updated_offsets = _update_cache_and_offsets(state, current_expert, cached_results)

        # 케이스 1: 빈 캐시 (보여줄 것이 없음) → 재검색 수행 (임베딩/필터 재사용)
        if not cached_results['TOP'] or not cached_results['BOTTOM']:
            writer(
                {
                    'type': SSETypes.STATUS.value,
                    'content': StatusUpdate(state=StatusUpdateTypes.START, content=f'{current_expert} 재검색 시작', task_id='search').model_dump(),
                }
            )
            logger.warning(f'{current_expert}: 중복 제거 후 표시 가능한 코디 세트 없음. shown_ids={len(shown_ids)}개')

            last_embeddings = search_result.get('embeddings', None)
            last_pre_filters = search_result.get('pre_filter_list', None)

            retry_limit = search_limit + fallback_delta
            retry_result = await search_service.search_by_previous_embeddings_with_relaxed_filters(
                embeddings=last_embeddings,
                pre_filters=last_pre_filters,
                limit=retry_limit,
            )
            writer(
                {
                    'type': SSETypes.STATUS.value,
                    'content': StatusUpdate(state=StatusUpdateTypes.END, content='재검색 완료!', task_id='search').model_dump(),
                }
            )

            # 재검색 결과를 동일 로직으로 캐시 구성
            cached_results_retry = _build_cache_from_search_results(retry_result['data'], shown_ids)
            total_results_retry = len(retry_result['data'])

            logger.info(
                f'[재검색] {current_expert} 결과: 전체 {total_results_retry}개, '
                f'TOP {len(cached_results_retry["TOP"])}개, BOTTOM {len(cached_results_retry["BOTTOM"])}개'
            )

            updated_cache[current_expert] = cached_results_retry
            updated_offsets[current_expert] = 0

            if cached_results_retry['TOP'] and cached_results_retry['BOTTOM']:
                first_top = cached_results_retry['TOP'][0]
                first_bottom = cached_results_retry['BOTTOM'][0]

                updated_shown_ids = shown_ids.copy()
                updated_shown_ids.add(first_top)
                updated_shown_ids.add(first_bottom)

                retry_message = _create_outfit_message(current_expert, current_expert_opinion, first_top, first_bottom)

                return {
                    StateName.MESSAGES: [retry_message],
                    StateName.EXPERT_SEARCH_CACHE: updated_cache,
                    StateName.EXPERT_OFFSETS: updated_offsets,
                    StateName.SHOWN_IN_PRODUCT_IDS: updated_shown_ids,
                }

            # 재검색을 수행할 데이터가 없거나, 재검색도 실패한 경우 → 의견만 반환
            empty_cache_message = create_message(message_type='ai', content=current_expert_opinion)
            return {
                StateName.MESSAGES: [empty_cache_message],
                StateName.EXPERT_SEARCH_CACHE: updated_cache,
                StateName.EXPERT_OFFSETS: updated_offsets,
            }

        # 케이스 2: 정상 캐시 (첫 번째 코디 표시)
        first_top = cached_results['TOP'][0]
        first_bottom = cached_results['BOTTOM'][0]

        updated_shown_ids = shown_ids.copy()
        updated_shown_ids.add(first_top)
        updated_shown_ids.add(first_bottom)

        search_result_message = _create_outfit_message(current_expert, current_expert_opinion, first_top, first_bottom)

        return {
            StateName.MESSAGES: [search_result_message],
            StateName.EXPERT_SEARCH_CACHE: updated_cache,
            StateName.EXPERT_OFFSETS: updated_offsets,
            StateName.SHOWN_IN_PRODUCT_IDS: updated_shown_ids,
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
    """캐시에서 다음으로 보여줄 상품을 찾는 노드 (부분 순환 지원)

    prepare_cache_cycle_node에서 설정한 offset을 사용
    - 범위 내: 유효한 쌍 존재 → 이미지 표시
    - 범위 밖: 캐시 소진 → 텍스트만 표시
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

    # 범위 체크로 순환 가능 여부 판단
    if current_offset < min(len(top_list), len(bottom_list)):
        # 케이스 1: 순환 가능 (이미지 + 의견)
        logger.info(f'  🖼️  {current_expert}: 캐시에서 이미지 가져오기 (offset={current_offset})')

        top_product_id = top_list[current_offset]
        bottom_product_id = bottom_list[current_offset]

        # shown_ids에 추가
        updated_shown_ids = shown_ids.copy()
        updated_shown_ids.add(top_product_id)
        updated_shown_ids.add(bottom_product_id)

        # offset 증가 (다음번을 위해)
        updated_offsets = expert_offsets.copy()
        updated_offsets[current_expert] = current_offset + 1
        logger.info(f'  📍 {current_expert}: offset {current_offset} → {current_offset + 1}')

        metadata = {'type': 'refer', 'expert_type': current_expert, 'product_ids': [top_product_id, bottom_product_id]}

        content = expert_opinions.get(current_expert, '')
        response = create_message(message_type='ai', content=content, metadata=metadata)

        return {
            StateName.MESSAGES: [response],
            StateName.SHOWN_IN_PRODUCT_IDS: updated_shown_ids,
            StateName.EXPERT_OFFSETS: updated_offsets,
        }

    else:
        # 케이스 2: 순환 불가능 (텍스트만)
        logger.info(
            f'  💬 {current_expert}: 캐시 소진 '
            f'(offset={current_offset}, len={min(len(top_list), len(bottom_list)) if top_list or bottom_list else 0}) → 텍스트만 표시'
        )

        # 전문가 의견 + 안내 메시지 (metadata 없이)
        # content = expert_opinions.get(current_expert, '')
        # TODO : 여기에 보여줄 message의 content를 어떻게 정할지??
        content = f'{current_expert} 전문가 조건에 맞는 추가 상품을 모두 확인하셨어요.'

        response = create_message(message_type='ai', content=content, metadata={'expert_type': current_expert})

        return {
            StateName.MESSAGES: [response],
        }


def send_refinement_prompt_node(state: State) -> dict:
    """더 이상 보여줄 캐시 아이템이 없을 때 사용자에게 안내 메시지를 보내는 노드"""
    logger.debug('\n--- 노드 실행: send_refinement_prompt_node ---')
    message = create_message(
        message_type='ai',
        content='추천해 드릴 만한 다른 상품을 모두 보여드렸어요. 원하시는 스타일이 있다면 더 자세히 알려주시겠어요? 새로운 조건으로 다시 찾아볼게요!',
    )
    return {StateName.MESSAGES: [message]}


def test_search_node(state: State):
    """최종 검색 실행 노드"""
    logger.info('\n--- 노드 실행: search_node ---')
    search_info = state['cloth_search']
    search_result_message = f'검색을 시작합니다: {search_info.model_dump_json(indent=2)}'
    logger.info(search_result_message)
    return {StateName.MESSAGES: [create_message(message_type='ai', content=search_result_message)]}


def prepare_cache_cycle_node(state: State) -> dict:
    """캐시 순환 준비 - 부분 순환 지원

    v3 개선: 전체 중단 → 부분 순환
    - 순환 가능한 전문가: offset 업데이트 (이미지 표시)
    - 순환 불가능한 전문가: offset은 범위 밖 상태 유지 (텍스트만 표시)
    - 1명이라도 순환 가능: can_cycle = True
    - 모두 불가능: can_cycle = False (안내 메시지)
    """
    logger.info('\n--- 노드: prepare_cache_cycle (부분 순환 지원) ---')

    expert_cache = state.get(StateName.EXPERT_SEARCH_CACHE.value, {})
    expert_offsets = state.get(StateName.EXPERT_OFFSETS.value, {})
    shown_ids = state.get(StateName.SHOWN_IN_PRODUCT_IDS.value, set())

    expert_names_with_cache = list(expert_cache.keys())
    planned_items = set()
    updated_offsets = expert_offsets.copy()

    experts_with_items = []  # 순환 가능한 전문가 (로깅용)

    # 각 전문가별로 순환 가능 여부 확인 및 offset 업데이트
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
                logger.info(f'  ✅ {expert_name}: offset={current_offset}에서 쌍 발견')
                break

            # 중복이 있으면 다음 인덱스로
            current_offset += 1

        # 쌍을 못 찾은 경우에도 offset 업데이트 (범위 밖으로 설정)
        if not found_pair:
            updated_offsets[expert_name] = current_offset
            logger.info(f'  ⚠️  {expert_name}: 보여줄 쌍 없음 (offset={current_offset}) → 텍스트만 표시')

        if found_pair:
            experts_with_items.append(expert_name)

    # 부분 순환 판단: 1명이라도 순환 가능하면 True
    can_cycle = len(experts_with_items) > 0

    logger.info(f'- 순환 가능 전문가: {experts_with_items}')
    logger.info(f'- 전체 실행 전문가: {expert_names_with_cache}')
    logger.info(f'- 캐시 순환 가능 여부: {can_cycle}')

    # State 업데이트 반환 - 순환 가능 여부와 상관없이 모든 전문가 실행
    return {
        StateName.EXPERT_OFFSETS: updated_offsets,
        StateName.EXPERTS_TO_RUN: expert_names_with_cache,  # 모든 전문가 실행
        StateName.CACHE_CYCLABLE: can_cycle,  # 라우터에서 사용할 플래그
    }


def prepare_search_cycle_node(state: State) -> dict:
    """
    information gathering node / information_update_node 에서 변경된 cloth_search에 대한 값에 따라서 실행할(순환할) 전문가 설정
    최초 검색 준비 - 3개 전문가 설정
    """
    logger.info('\n--- 노드: prepare_search_cycle ---')
    # changed_fields = state.get(StateName.LAST_UPDATED_FIELDS, [])

    # if not changed_fields:
    logger.info('- 저ㄴ체 전문가 호출')
    experts_to_run = [COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATOR]
    return {
        StateName.EXPERTS_TO_RUN: experts_to_run,
    }
    # # TODO : 조건 변경시 전문가 실행할 전문가 설정하는 로직 수정 필요
    # else:
    #     experts_set = set()
    #     # 색상만 변경
    #     if 'color' in changed_fields and len(changed_fields) == 1:
    #         experts_set.add(COLOR_EXPERT)
    #         logger.info('  → color_expert만 실행')

    #     # 스타일만 변경
    #     elif 'style' in changed_fields and len(changed_fields) == 1:
    #         experts_set.add(STYLE_ANALYST)
    #         logger.info('  → style_analyst만 실행')

    #     # TPO 변경 또는 복합 변경 -> 전체 재평가
    #     elif 'tpo' in changed_fields or len(changed_fields) > 1:
    #         experts_set.update([COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATOR])
    #         logger.info('  → 전체 전문가 재평가')
    #     else:
    #         experts_set.update([COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATOR])
    #         logger.info('  → 기본: 전체 전문가 실행')

    #     experts_to_run = list(experts_set)
    #     logger.info(f'  (실행할 전문가 목록: {experts_to_run})')

    #     return {
    #         StateName.EXPERTS_TO_RUN: experts_to_run,
    #     }
