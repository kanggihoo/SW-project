# Combined External LLM and Search graph builder

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.common.nodes.before_search_node import (
    chatbot,
    handle_inappropriate_node,
    info_qa_node,
    information_gathering_node,
    information_update_node,
    intent_classify_node,
    prepare_search_message_node,
    prepare_template_search_node,
)
from graph.common.nodes.product_info_node import custom_pre_model_node
from graph.common.router import master_router, route_after_classification, route_after_gathering
from graph.common.state import State
from graph.constants import GraphName, NodeName, RouterReturnNames
from graph.subgraph.build_product_info_agent import build_product_info_agent_subgraph
from graph.subgraph.search import search_subgraph


# TODO : chatbot , info_qa에서의 create_react_agent, product_info_qgent 에서 client 전달해서 tool에서 사용하도록 하기
def build_fashion_search_graph(musinsa_api_wrapper, cache_client, task_queue_client, db_repository) -> CompiledStateGraph:
    graph_builder = StateGraph(State)

    graph_builder.add_node(NodeName.CLASSIFY_INTENT, intent_classify_node)
    graph_builder.add_node(NodeName.HANDLE_INAPPROPRIATE, handle_inappropriate_node)
    graph_builder.add_node(NodeName.CHATBOT, chatbot)
    graph_builder.add_node(NodeName.INFO_QA, info_qa_node)
    graph_builder.add_node(NodeName.INFORMATION_GATHERING, information_gathering_node)
    graph_builder.add_node(NodeName.INFORMATION_UPDATE, information_update_node)
    graph_builder.add_node(NodeName.PREPARE_TEMPLATE_SEARCH, prepare_template_search_node)
    graph_builder.add_node(NodeName.PREPARE_SEARCH_MESSAGE, prepare_search_message_node)
    # graph_builder.add_node(NodeName.SEARCH_NODE, test_search_node)

    graph_builder.add_node(NodeName.SEARCH_NODE, search_subgraph)
    graph_builder.add_node(NodeName.CUSTOM_PRE_MODEL_NODE, custom_pre_model_node)
    graph_builder.add_node(
        NodeName.PRODUCT_INFO_AGENT, build_product_info_agent_subgraph(musinsa_api_wrapper, cache_client, task_queue_client, db_repository)
    )

    graph_builder.add_conditional_edges(
        START,
        master_router,
        {
            RouterReturnNames.CUSTOM_PRE_MODEL_NODE: NodeName.CUSTOM_PRE_MODEL_NODE,
            RouterReturnNames.CLASSIFY_INTENT: NodeName.CLASSIFY_INTENT,
            RouterReturnNames.PREPARE_TEMPLATE_SEARCH: NodeName.PREPARE_TEMPLATE_SEARCH,
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
            RouterReturnNames.PREPARE_SEARCH_MESSAGE: NodeName.PREPARE_SEARCH_MESSAGE,
            END: END,
        },
    )
    # 템플릿 준비 노드 -> 정보 업데이트 노드로 연결
    graph_builder.add_edge(NodeName.PREPARE_TEMPLATE_SEARCH, NodeName.INFORMATION_UPDATE)

    # product_id가 주어진 경우 무신사 api 서브 그래프 실행전 message 수정 노드
    graph_builder.add_edge(NodeName.CUSTOM_PRE_MODEL_NODE, NodeName.PRODUCT_INFO_AGENT)

    # 검색 메시지 준비 노드 -> 검색 서브그래프로 이동
    graph_builder.add_edge(NodeName.PREPARE_SEARCH_MESSAGE, NodeName.SEARCH_NODE)

    # 정보 '업데이트' 후에는 메시지 준비 노드로 이동
    graph_builder.add_edge(NodeName.INFORMATION_UPDATE, NodeName.PREPARE_SEARCH_MESSAGE)

    # 4. 최종 노드 -> END
    graph_builder.add_edge(NodeName.SEARCH_NODE, END)
    graph_builder.add_edge(NodeName.PRODUCT_INFO_AGENT, END)
    graph_builder.add_edge(NodeName.HANDLE_INAPPROPRIATE, END)
    graph_builder.add_edge(NodeName.CHATBOT, END)
    graph_builder.add_edge(NodeName.INFO_QA, END)

    compiled_graph = graph_builder.compile()
    compiled_graph.name = GraphName.FASHION_SEARCH

    return compiled_graph
