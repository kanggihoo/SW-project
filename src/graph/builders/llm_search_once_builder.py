# 특정 전문가를 호출하고 그 결과로 바탕으로 이미지 검색 한 뒤에 정보 담아서 검색

# Combined External LLM and Search graph builder

from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.common.mock_node import mock_external_llm_node
from graph.common.node import external_llm_node, search_node
from graph.common.state import State
from graph.constants import GraphName
from graph.settings import Environment, settings


def build_llm_search_once_graph() -> CompiledStateGraph:
    """Combined external LLM and search graph builder

    Flow: 사용자 입력 -> pop_next_expert -> external_llm_node -> search_node -> (loop or end)
    - pop_next_expert: 전문가 리스트에서 다음 전문가 선택
    - external_llm_node: 사용자 입력을 분석하여 의류 조합 추천
    - search_node: 외부 LLM 결과를 기반으로 이미지 검색 수행
    - route_expert_loop: 모든 전문가 완료 여부에 따른 루프 제어

    Args:
        api_endpoint: External LLM API endpoint URL (optional)

    Returns:
        Compiled graph for LLM search workflow
    """
    graph_builder = StateGraph(State)

    # Add nodes
    if settings.ENV == Environment.TESTING:
        graph_builder.add_node('external_llm', mock_external_llm_node)
    else:
        graph_builder.add_node('external_llm', external_llm_node)
    graph_builder.add_node('search', search_node)

    # Add edges
    graph_builder.add_edge(START, 'external_llm')
    graph_builder.add_edge('external_llm', 'search')

    compiled_graph = graph_builder.compile()
    compiled_graph.name = GraphName.LLM_SEARCH_ONCE

    return compiled_graph
