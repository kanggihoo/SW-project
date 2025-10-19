# Combined External LLM and Search graph builder

import httpx
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.builders.search_subgraph_builder import search_subgraph
from graph.common.node import (
    chatbot,
    handle_inappropriate_node,
    info_qa_node,
    information_gathering_node,
    information_update_node,
    intent_classify_node,
)
from graph.common.router import (
    master_router,
    route_after_classification,
    route_after_gathering,
)
from graph.common.state import State
from graph.constants import GraphName, NodeName, RouterReturnNames


# TODO : chatbot , info_qa에서의 create_react_agent, product_info_qgent 에서 client 전달해서 tool에서 사용하도록 하기
def build_fashion_search_graph(client: httpx.AsyncClient) -> CompiledStateGraph:
    graph_builder = StateGraph(State)

    graph_builder.add_node(NodeName.CLASSIFY_INTENT, intent_classify_node)
    graph_builder.add_node(NodeName.HANDLE_INAPPROPRIATE, handle_inappropriate_node)
    graph_builder.add_node(NodeName.CHATBOT, chatbot)
    graph_builder.add_node(NodeName.INFO_QA, info_qa_node)
    graph_builder.add_node(NodeName.INFORMATION_GATHERING, information_gathering_node)
    graph_builder.add_node(NodeName.INFORMATION_UPDATE, information_update_node)
    # graph_builder.add_node(NodeName.SEARCH_NODE, test_search_node)

    graph_builder.add_node(NodeName.SEARCH_NODE, search_subgraph)
    # graph_builder.add_node(NodeName.PRODUCT_INFO_AGENT, product_info_agent)

    graph_builder.add_conditional_edges(
        START,
        master_router,
        {
            # NodeName.PRODUCT_INFO_AGENT: NodeName.PRODUCT_INFO_AGENT,
            NodeName.CLASSIFY_INTENT: NodeName.CLASSIFY_INTENT,
        },
    )

    # 2. 의도 분류 후 라우팅
    graph_builder.add_conditional_edges(
        NodeName.CLASSIFY_INTENT,
        route_after_classification,
        {
            RouterReturnNames.INFORMATION_GATHERING: NodeName.INFORMATION_GATHERING,
            RouterReturnNames.HANDLE_INAPPROPRIATE: NodeName.HANDLE_INAPPROPRIATE,
            RouterReturnNames.INFORMATION_UPDATE: NodeName.INFORMATION_UPDATE,
            RouterReturnNames.CHATBOT: NodeName.CHATBOT,
            RouterReturnNames.INFO_QA: NodeName.INFO_QA,
            END: END,
        },
    )

    # 3. 정보 수집 후 라우팅
    graph_builder.add_conditional_edges(
        NodeName.INFORMATION_GATHERING,
        route_after_gathering,
        {
            NodeName.SEARCH_NODE: NodeName.SEARCH_NODE,
            END: END,
        },
    )
    # 3. 정보 '업데이트' 후에는 다시 '검색' 노드로 이동
    graph_builder.add_edge(NodeName.INFORMATION_UPDATE, NodeName.SEARCH_NODE)

    # 4. 최종 노드 -> END
    graph_builder.add_edge(NodeName.SEARCH_NODE, END)
    # graph_builder.add_edge(NodeName.PRODUCT_INFO_AGENT, END)
    graph_builder.add_edge(NodeName.HANDLE_INAPPROPRIATE, END)
    graph_builder.add_edge(NodeName.CHATBOT, END)
    graph_builder.add_edge(NodeName.INFO_QA, END)

    compiled_graph = graph_builder.compile()
    compiled_graph.name = GraphName.FASHION_SEARCH

    return compiled_graph
