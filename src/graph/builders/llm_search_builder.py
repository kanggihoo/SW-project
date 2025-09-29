# Combined External LLM and Search graph builder
import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.common.node import external_llm_node, pop_next_expert_node, search_node
from graph.common.router import route_expert_loop
from graph.common.state import State

logger = logging.getLogger(__name__)


def build_llm_search_graph(api_endpoint: str = None) -> CompiledStateGraph:
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
    graph_builder.add_node('pop_next_expert', pop_next_expert_node)
    graph_builder.add_node('external_llm', external_llm_node)
    graph_builder.add_node('search', search_node)

    # Add edges
    graph_builder.add_edge(START, 'pop_next_expert')
    graph_builder.add_edge('pop_next_expert', 'external_llm')
    graph_builder.add_edge('external_llm', 'search')

    # Add conditional edges for expert loop control
    graph_builder.add_conditional_edges('search', route_expert_loop, {'continue_loop': 'pop_next_expert', 'end_loop': END})

    compiled_graph = graph_builder.compile()
    compiled_graph.name = 'llm_search_graph'

    return compiled_graph
