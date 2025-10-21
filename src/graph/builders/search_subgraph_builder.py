# # graph/nodes.py

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.common.nodes.mock_node import mock_external_llm_node
from graph.common.nodes.search_node import (
    get_cached_item_node,
    pop_next_expert_node,
    prepare_cache_cycle_node,
    prepare_search_cycle_node,
    run_expert_evaluation_node,
    search_node,
    send_refinement_prompt_node,
)
from graph.common.router import decide_work_after_pop, route_after_cache_preparation, route_expert_loop, route_search_entry
from graph.common.state import State
from graph.constants import GraphName, NodeName, RouterReturnNames
from graph.settings import Environment, settings

# def information_update_node(state: State):


def build_search_subgraph() -> CompiledStateGraph:
    # --- Search Sub-Graph 정의 ---
    graph_builder = StateGraph(State)

    # ============================================================================
    # 노드 정의
    # ============================================================================
    # 초기 실행할 로직에 따른 실행할 전문가 결정 (벡터 검색인 경우 실행할 전문가 결정 / 캐쉬 순환인 경우 순환가능한지 판단 )
    graph_builder.add_node(NodeName.PREPARE_SEARCH_CYCLE, prepare_search_cycle_node)
    graph_builder.add_node(NodeName.PREPARE_CACHE_CYCLE, prepare_cache_cycle_node)

    # 결정된 전문가로 부터 하니씩 가져오기
    graph_builder.add_node(NodeName.POP_NEXT_EXPERT, pop_next_expert_node)

    # 실제 벡터 검색 관련 노드들
    if settings.ENV == Environment.TESTING:
        graph_builder.add_node(NodeName.RUN_EXPERT_EVALUATION, mock_external_llm_node)
    else:
        graph_builder.add_node(NodeName.RUN_EXPERT_EVALUATION, run_expert_evaluation_node)
    graph_builder.add_node(NodeName.VECTOR_SEARCH, search_node)

    # 캐시 순환 가능한 경우 캐쉬로 부터 데이터 가져오기 / 캐쉬 순환 불가능 경우 사용자에게 안내 메시지 전송
    graph_builder.add_node(NodeName.GET_CACHED_ITEM, get_cached_item_node)
    graph_builder.add_node(NodeName.SEND_REFINEMENT_PROMPT, send_refinement_prompt_node)

    # ============================================================================
    # 라우터 정의
    # ============================================================================
    #  초기 진입 라우터 설정(이전 노드 결과에 따라 초기 실행할 로직 결정)
    graph_builder.add_conditional_edges(
        START,
        route_search_entry,
        {
            RouterReturnNames.PREPARE_SEARCH_CYCLE: NodeName.PREPARE_SEARCH_CYCLE,
            RouterReturnNames.PREPARE_CACHE_CYCLE: NodeName.PREPARE_CACHE_CYCLE,
        },
    )

    # 캐시 순환 라우터 설정 (캐시 순환 가능 여부에 따라 분기)
    graph_builder.add_conditional_edges(
        NodeName.PREPARE_CACHE_CYCLE,
        route_after_cache_preparation,
        {
            RouterReturnNames.GO_CACHED_LOOP: NodeName.POP_NEXT_EXPERT,
            RouterReturnNames.NO_MORE_ITEMS: NodeName.SEND_REFINEMENT_PROMPT,
        },
    )

    # 캐쉬 순환 가능한 경우 캐쉬로 부터 데이터 가져오기 / 실제 벡터 검색 수행하는 경우 벡터 검색 노드로 이동
    graph_builder.add_conditional_edges(
        NodeName.POP_NEXT_EXPERT,
        decide_work_after_pop,
        {
            RouterReturnNames.RUN_EXPERT_EVALUATION: NodeName.RUN_EXPERT_EVALUATION,
            RouterReturnNames.GET_CACHED_ITEM: NodeName.GET_CACHED_ITEM,
        },
    )

    # 벡터 검색의 순환 루프 제어
    graph_builder.add_conditional_edges(
        NodeName.VECTOR_SEARCH,  # 한 전문가의 검색이 끝나면
        route_expert_loop,  # 루프 제어 라우터가 판단
        {
            RouterReturnNames.CONTINUE_LOOP: NodeName.POP_NEXT_EXPERT,  # 계속 -> 루프 처음으로
            END: END,  # 종료 -> Sub-Graph 끝
        },
    )
    # 캐시 순환 루프 제어
    graph_builder.add_conditional_edges(
        NodeName.GET_CACHED_ITEM,
        route_expert_loop,
        {
            RouterReturnNames.CONTINUE_LOOP: NodeName.POP_NEXT_EXPERT,
            END: END,
        },
    )

    # ============================================================================
    # 엣지 정의
    # ============================================================================
    # 벡터 검색을 위해 전문가 목록 준비 노드 => 전문가 목록으로 부터 하니씩 꺼내 오는 노드
    graph_builder.add_edge(NodeName.PREPARE_SEARCH_CYCLE, NodeName.POP_NEXT_EXPERT)

    # 엣지 연결 (전문가 실행 노드 => 벡터 검색)
    graph_builder.add_edge(NodeName.RUN_EXPERT_EVALUATION, NodeName.VECTOR_SEARCH)

    # 캐시 순환 불가능 처리 노드 => 종료 엣지 연결
    graph_builder.add_edge(NodeName.SEND_REFINEMENT_PROMPT, END)

    # Sub-Graph 컴파일
    search_subgraph = graph_builder.compile()
    search_subgraph.name = GraphName.SEARCH_SUBGRAPH
    return search_subgraph
