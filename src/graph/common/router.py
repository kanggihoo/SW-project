# ruff : noqa: E501

from langgraph.graph import END
from loguru import logger

from graph.common.state import State
from graph.constants import (
    SHOW_CACHED,
    IntentTypes,
    NodeName,
    RouterReturnNames,
    StateName,
)


def master_router(state: State):
    logger.debug('---\n--- 라우팅: master_router ---')
    if state.get(StateName.PRODUCT_ID):
        logger.debug('- 라우팅: product_info_agent_node로 이동')
        return RouterReturnNames.CUSTOM_PRE_MODEL_NODE
    elif state.get(StateName.IS_PREDEFINED_TEMPLATE):
        logger.debug('- 라우팅: prepare_template_search_node로 이동 (템플릿 처리 준비)')
        return RouterReturnNames.PREPARE_TEMPLATE_SEARCH
    else:
        logger.debug('- 라우팅: classify_intent_node로 이동')
        return RouterReturnNames.CLASSIFY_INTENT


def route_after_gathering(state: State):
    """정보 수집 후 다음 노드를 결정"""
    logger.debug('\n--- 라우팅: route_after_gathering ---')
    if state.get(StateName.IS_INFO_GATHERING_COMPLETE):
        logger.debug('- 라우팅: search_node로 이동')
        return NodeName.SEARCH_NODE
    else:
        logger.debug('- 라우팅: END (추가 사용자 입력 대기)')
        return END


def route_after_classification(state: State):
    """의도 분류 결과에 따라 다음 노드를 결정
    state에 담긴 intent 와 is_info_gathering_complete 를 사용하여 라우팅 결정
    1. is_info_gathering_complete 가 False 이고 intent 가 DIRECT_SEARCH 이면 INFORMATION_GATHERING 으로 이동하여 정보 수집 노드 동작
    2. is_info_gathering_complete 가 True 이고 intent 가 SEARCH_REFINEMENT 이면 INFORMATION_UPDATE 으로 이동하여 정보 업데이트 노드 동작

    3. 그외의 부적절한 의도, 챗봇, 정보 검색 인 경우 해당 노드로 이동
    4. unclear 또는 기타 의도의 경우 END 로 이동
    """
    intent = state[StateName.INTENT.value]
    is_info_gathering_complete = state.get(StateName.IS_INFO_GATHERING_COMPLETE, False)

    if not is_info_gathering_complete and intent in [IntentTypes.DIRECT_SEARCH, IntentTypes.SEARCH_REFINEMENT]:
        if intent == IntentTypes.SEARCH_REFINEMENT:
            logger.warning(f'- 로직 보정: Gathering 상태에서 {intent}가 감지되어 {RouterReturnNames.INFORMATION_GATHERING}(으)로 보정 라우팅합니다.')
        return RouterReturnNames.INFORMATION_GATHERING

    elif is_info_gathering_complete and intent in [IntentTypes.SEARCH_REFINEMENT, IntentTypes.DIRECT_SEARCH]:
        if intent == IntentTypes.DIRECT_SEARCH:
            logger.warning(
                f'- 로직 보정: Gathering 완료 상태에서 {intent}가 감지되어 {RouterReturnNames.INFORMATION_UPDATE}(으)로 보정 라우팅합니다.'
            )
        return RouterReturnNames.INFORMATION_UPDATE

    elif intent == IntentTypes.INAPPROPRIATE_QUERY:
        logger.debug('- 라우팅: handle_inappropriate_node로 이동')
        return RouterReturnNames.HANDLE_INAPPROPRIATE
    elif intent == IntentTypes.CHATBOT:
        logger.debug('- 라우팅: chatbot_node로 이동')
        return RouterReturnNames.CHATBOT
    elif intent == IntentTypes.INFO_QA:
        logger.debug('- 라우팅: info_qa_node로 이동')
        return RouterReturnNames.INFO_QA
    else:  # unclear 또는 기타
        logger.info('- 라우팅: END (분류 실패 또는 추가 처리 불필요)')
        return END


# ==================================================================================================================
# search_subgraph 에서 사용하는 라우터
# ==================================================================================================================
def route_search_entry(state: State) -> str:
    """Search Sub-Graph 진입 시 초기 라우팅

    Returns:
        - "prepare_cache_cycle": 캐시에서 다음 결과 표시
        - "prepare_initial_search": 최초 검색 (3개 전문가)
        - "prepare_field_update_search": 필드 변경에 따른 검색
    """
    logger.info('\n--- 라우터(진입): route_search_entry ---')
    changed_fields = state.get(StateName.LAST_UPDATED_FIELDS.value, [])

    # Case 1: 다음 유사 아이템 표시 요청
    if SHOW_CACHED in changed_fields:
        logger.info('- 경로 결정: 캐시 순환 체크 필요')
        return RouterReturnNames.PREPARE_CACHE_CYCLE

    return RouterReturnNames.PREPARE_SEARCH_CYCLE


def decide_work_after_pop(state: State) -> str:
    """전문가를 뽑은 직후, 새로운 검색을 할지 캐시를 보여줄지 결정"""
    # last_updated_fields 상태를 보고 간단히 다음 경로를 결정합니다.
    if SHOW_CACHED in state.get(StateName.LAST_UPDATED_FIELDS.value, []):
        return RouterReturnNames.GET_CACHED_ITEM  # 캐시 순환 플래그가 있으면 캐시 노드로
    else:
        return RouterReturnNames.RUN_EXPERT_EVALUATION  # 없으면 일반 검색 노드로


def route_after_cache_preparation(state: State) -> str:
    """캐시 준비 노드 이후 라우팅

    Returns:
        - "continue_cached_loop": 캐시 순환 계속
        - "no_more_items": 캐시 소진
    """
    logger.info('\n--- 라우터: route_after_cache_preparation ---')

    if state.get('cache_cyclable', False):
        logger.info('- 경로 결정: 캐시 순환 계속')
        return RouterReturnNames.GO_CACHED_LOOP
    else:
        logger.info('- 경로 결정: 캐시 소진, 사용자에게 안내')
        return RouterReturnNames.NO_MORE_ITEMS


# --- ▼ 캐시 순환 로직을 위한 라우터 ---
# def route_cached_results(state: State):
#     """캐시 순환 시작 전, 보여줄 상품이 남아있는지 전체적으로 검사하는 라우터"""
#     logger.debug('\n--- 라우팅(캐시 제어): route_cached_results ---')
#     expert_cache = state.get(StateName.EXPERT_SEARCH_CACHE.value, {})
#     expert_offsets = state.get(StateName.EXPERT_OFFSETS.value, {})
#     shown_ids = state.get(StateName.SHOWN_IN_PRODUCT_IDS.value, [])

#     # 실행할 전문가 목록 (이 시점에는 캐시가 있는 모든 전문가)
#     experts_to_run = state.get(StateName.EXPERTS_TO_RUN.value, [])

#     for expert in experts_to_run:
#         cached_results = expert_cache.get(expert, [])
#         current_offset = expert_offsets.get(expert, 0)

#         # 해당 전문가의 남은 캐시 목록 확인
#         if current_offset < len(cached_results):
#             # 남은 상품 중 하나라도 아직 안 보여준 것이 있는지 확인
#             remaining_ids = {item['product_id'] for item in cached_results[current_offset:]}
#             if not remaining_ids.issubset(set(shown_ids)):
#                 logger.debug('- 경로 결정: 캐시 순환 계속 (보여줄 상품 남음)')
#                 return RouterReturnNames.CONTINUE_CACHED_LOOP

#     logger.debug('- 경로 결정: 캐시 순환 종료 (보여줄 상품 없음)')
#     return RouterReturnNames.NO_MORE_ITEMS


def route_expert_loop(state: State):
    """전문가 1명의 작업 사이클 후, 루프를 계속할지 종료할지 결정"""
    experts_left = state.get(StateName.EXPERTS_TO_RUN.value, [])
    # 순환 할 수 있는 전문가 남아 있는 경우 계속 순환
    if len(experts_left) > 0:
        logger.info(f'- 경로 결정: 루프 계속 (남은 전문가: {experts_left})')
        return RouterReturnNames.CONTINUE_LOOP
    else:
        logger.info('- 경로 결정: 루프 종료 (모든 전문가 순환 완료)')
        return END
