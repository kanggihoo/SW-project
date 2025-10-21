# Combined External LLM and Search graph builder

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.common.nodes.mock_node import mock_external_llm_node
from graph.common.nodes.search_node import pop_next_expert_node, run_expert_evaluation_node, search_node
from graph.common.router import route_expert_loop
from graph.common.state import State
from graph.constants import GraphName, NodeName, RouterReturnNames
from graph.settings import Environment, settings


def build_llm_search_graph() -> CompiledStateGraph:
    """Combined external LLM and search graph builder

    Flow: 사용자 입력 -> pop_next_expert -> external_llm_node -> search_node -> (loop or end)
    - pop_next_expert: 전문가 리스트에서 다음 전문가 선택
    - external_llm_node: 사용자 입력을 분석하여 의류 조합 추천
    - search_node: 외부 LLM 결과를 기반으로 이미지 검색 수행
    - route_expert_loop: 모든 전문가 완료 여부에 따른 루프 제어

    Returns:
        Compiled graph for LLM search workflow
    """
    graph_builder = StateGraph(State)

    # Add nodes
    graph_builder.add_node(NodeName.POP_NEXT_EXPERT, pop_next_expert_node)
    if settings.ENV == Environment.TESTING:
        graph_builder.add_node(NodeName.RUN_EXPERT_EVALUATION, mock_external_llm_node)
    else:
        graph_builder.add_node(NodeName.RUN_EXPERT_EVALUATION, run_expert_evaluation_node)
    graph_builder.add_node(NodeName.VECTOR_SEARCH, search_node)

    # Add edges
    graph_builder.add_edge(START, NodeName.POP_NEXT_EXPERT)
    graph_builder.add_edge(NodeName.POP_NEXT_EXPERT, NodeName.RUN_EXPERT_EVALUATION)
    graph_builder.add_edge(NodeName.RUN_EXPERT_EVALUATION, NodeName.VECTOR_SEARCH)

    # Add conditional edges for expert loop control
    graph_builder.add_conditional_edges(
        NodeName.VECTOR_SEARCH,
        route_expert_loop,
        {
            RouterReturnNames.CONTINUE_LOOP: NodeName.POP_NEXT_EXPERT,
            END: END,
        },
    )

    compiled_graph = graph_builder.compile()
    compiled_graph.name = GraphName.LLM_SEARCH

    return compiled_graph
