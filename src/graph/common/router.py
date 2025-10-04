from langgraph.graph import END
from loguru import logger

from graph.common.schemas import NodeName
from graph.common.state import State


def route_expert_loop(state: State):
    """전문가 1명의 작업 사이클 후, 루프를 계속할지 종료할지 결정"""
    logger.debug('\n--- 라우팅(루프 제어): route_expert_loop ---')
    experts_left = state.get('experts_to_run', [])

    if len(experts_left) > 0:
        logger.debug(f'- 경로 결정: 루프 계속 (남은 전문가: {experts_left})')
        return 'continue_loop'
    else:
        logger.debug('- 경로 결정: 루프 종료 (모든 전문가 완료)')
        return 'end_loop'


def master_router(state: State):
    print('---\n--- 라우팅: master_router ---')
    if state.get('product_id'):
        print('- 라우팅: product_info_agent_node로 이동')
        return NodeName.PRODUCT_INFO_AGENT
    else:
        print('- 라우팅: classify_intent_node로 이동')
        return NodeName.CLASSIFY_INTENT


def route_after_gathering(state: State):
    """정보 수집 후 다음 노드를 결정"""
    print('\n--- 라우팅: route_after_gathering ---')
    if state.get('is_info_gathering_complete'):
        print('- 라우팅: search_node로 이동')
        return NodeName.SEARCH_NODE
    else:
        print('- 라우팅: END (추가 사용자 입력 대기)')
        return END


def route_after_classification(state: State):
    """의도 분류 결과에 따라 다음 노드를 결정"""
    print(f'\n--- 라우팅: route_after_classification (분류된 의도: {state["intent"]}) ---')
    intent = state['intent']
    is_info_gathering_complete = state.get('is_info_gathering_complete', False)
    if not is_info_gathering_complete and intent == NodeName.DIRECT_SEARCH:
        print('- 라우팅: information_gathering_node로 이동 (초기 수집)')
        return NodeName.INFORMATION_GATHERING
    elif is_info_gathering_complete and intent == NodeName.SEARCH_REFINEMENT:
        print('- 라우팅: information_update_node로 이동 (피드백 수정)')
        return NodeName.INFORMATION_UPDATE
    elif intent == NodeName.INAPPROPRIATE_QUERY:
        print('- 라우팅: handle_inappropriate_node로 이동')
        return NodeName.HANDLE_INAPPROPRIATE
    elif intent == NodeName.CHATBOT:
        print('- 라우팅: chatbot_node로 이동')
        return NodeName.CHATBOT
    elif intent == NodeName.INFO_QA:
        print('- 라우팅: info_qa_node로 이동')
        return NodeName.INFO_QA
    else:  # unclear 또는 기타
        print('- 라우팅: END (분류 실패 또는 추가 처리 불필요)')
        return END
