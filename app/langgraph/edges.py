# langgraph
from langgraph.graph import StateGraph , START , END

# State
from .states import ClothingRAGState

# Nodes
from .nodes import embed_query_node , select_candidates_node , gather_information_node , rerank_candidates_node , select_final_item_node , wait_for_user_feedback_node



def router_function(state: ClothingRAGState) -> str:
    '''
    client 측에서 종료 버튼을 누른경우에는 바로 end로 이동
    
    '''
    user_feedback = state.get("user_feedback")
    if user_feedback == "accept":
        return END
    else:
        return user_feedback 
    
def build_graph():
    builder = StateGraph(ClothingRAGState)
    builder.add_node("embed_query_node", embed_query_node)
    builder.add_node("select_candidates_node", select_candidates_node)
    builder.add_node("gather_information_node", gather_information_node)
    builder.add_node("rerank_candidates_node", rerank_candidates_node)
    builder.add_node("select_final_item_node", select_final_item_node)
    builder.add_node("wait_for_user_feedback_node", wait_for_user_feedback_node)


    builder.add_edge(START, "embed_query_node")
    builder.add_edge("embed_query_node", "select_candidates_node")
    builder.add_edge("select_candidates_node", "gather_information_node")
    builder.add_edge("gather_information_node", "rerank_candidates_node")
    builder.add_edge("rerank_candidates_node", "select_final_item_node")
    builder.add_edge("select_final_item_node", "wait_for_user_feedback_node")
    builder.add_edge("wait_for_user_feedback_node", END)

    builder.add_conditional_edges(
        "wait_for_user_feedback_node",
        
        router_function,
        {
            END: END,
            "embed_query_node": "embed_query_node",
            
        }
    )
    return builder








