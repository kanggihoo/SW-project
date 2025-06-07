from langgraph.graph.message import MessagesState
from typing import Annotated , Any
from langgraph.graph import StateGraph , END , START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from .utils import embedding_query , search_vector_db , get_product_details, rerank_items  , modify_query
from dotenv import load_dotenv
import os
import uuid

class ClothingRAGState(MessagesState):
    user_query: str
    embedded_query: list[float] | None
    candidate_items: list[dict[str, Any]] | None
    candidate_items_with_metadata: list[dict[str, Any]] | None
    external_info: dict[str, Any] | None   
    ranked_candidates: list[dict[str, Any]] | None
    # final_recommendation: Anno[dict[str, Any]]
    user_feedback: str | None # e.g., "rerank_cheaper", "rerank_review", "restart", "accept"
    # error_message: Annotated[str, ""]
    
#TODO : user_feedback이 있는 경우에는 llm을 이용해서 쿼리 수정 해야함.
# 임베딩 노드
def embed_query_node(state: ClothingRAGState) -> dict[str, Any]:
    print("--- Node: embed_query_node ---")
    user_query = state["user_query"]
    user_feedback = state.get("user_feedback", None)
    if user_feedback:
        # llm을 이용해서 쿼리 수정
        user_new_query = modify_query(user_query, user_feedback)
        print("user_feedback 존재하여 새로운 쿼리 생성! : ", user_new_query)
        return {"embedded_query": embedding_query(user_new_query)}
    else:
        return {"embedded_query": embedding_query(user_query) }

def select_candidates_node(state: ClothingRAGState , config:RunnableConfig) -> dict[str, Any]:
    print("--- Node: select_candidates_node ---")
    embedded_query = state["embedded_query"]
    # if not embedded_query:
    #     print("Error: No embedded query found.")
    #     return {"error_message": "Embedding failed or not provided."}
    k = config.get("configurable", {}).get("k", 3)
    candidates = search_vector_db(embedded_query , k = k)
    # Simulate some relevance based on the mock embedding and query
    print(f"Selected {len(candidates)} candidates (mock): {[c['name'] for c in candidates]}")
    return {"candidate_items": candidates}

def gather_information_node(state: ClothingRAGState) -> dict[str, Any]:
    print("--- Node: gather_information_node ---")
    candidate_items = state.get("candidate_items")
    # if not candidate_items:
    #     print("Error: No candidate items to gather information for.")
    #     return {"error_message": "No candidates found to gather info."}
    product_ids = [item["product_id"] for item in candidate_items]
    product_details = get_product_details(product_ids) 
    
    return {"candidate_items_with_metadata": product_details, "external_info": []}

def rerank_candidates_node(state: ClothingRAGState) -> dict[str, Any]:
    print("--- Node: rerank_candidates_node ---")
    items_with_metadata = state.get("candidate_items_with_metadata")
    external_info = state.get("external_info", {})
    

    # if not items_with_metadata:
    #     print("Error: No items with metadata to rerank.")
    #     return {"error_message": "Cannot rerank without item metadata."}
    reranked_items = rerank_items(items_with_metadata, external_info)    
    return {"ranked_candidates": reranked_items}

def select_final_item_node(state: ClothingRAGState , config: RunnableConfig) -> dict[str, Any]:
    print("--- Node: select_final_item_node ---")
    ranked_candidates = state.get("ranked_candidates")[0]
    # if not ranked_candidates:
    #     print("No candidates to select from after ranking.")
    #     return {"final_recommendation": None, "error_message": "No candidates available post-ranking."}
    
    llm_config = config.get("configurable", {}).get("llm_model", {})
    system_prompt = llm_config.get("prompt_template" , "")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{user_query}")
        ]
    )
    model = llm_config["model"]
    if model.startswith("gpt"):
        llm = ChatOpenAI(model=model , temperature=0)
    elif model.startswith("gemini"):
        llm = ChatGoogleGenerativeAI(model=model , temperature=0)
    chain = prompt | llm | StrOutputParser()
    for chunk in chain.stream({"user_query": "i wnat to buy a shirt"}):
        print(chunk , end = "|" , flush = True)

    # return {"final_recommendation": final_recommendation}

# 사용자 피드백 수집 노드 
def wait_for_user_feedback_node(state: ClothingRAGState) -> dict[str, Any]:
    print("--- Node: wait_for_user_feedback_node (after interrupt, expecting feedback in state) ---")
    print("user_feedback : ", state.get("user_feedback"))
    return {}

# human feedback을 바탕으로 다음으로 이동할 노드 결정
def router_function(state: ClothingRAGState) -> str:
    '''
    client 측에서 종료 버튼을 누른경우에는 바로 end로 이동
    
    '''
    user_feedback = state.get("user_feedback")
    if user_feedback == "accept":
        return END
    else:
        return "embed_query_node"

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


if __name__ == "__main__":
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    load_dotenv()
    # os.environ["LANGSMITH_TRACING"] = "true"
    # os.environ["LANGSMITH_PROJECT"] = "langgraph-test"
    
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "llm_model" : {
                "model": "gemini-1.5-flash",
                "prompt_template": "You are a helpful assistant that recommends clothing items based on the user's query. ",
            },
            "k": 3
        },
        "tags" : ["tmp" , "test"],
        "run_name" : "test_run"
        
    }
    # 인터럽트 걸리기 전까지 실행
    for chunk in graph.stream({"user_query": "I want to buy a shirt"} , stream_mode="updates" , config=config , interrupt_before=["wait_for_user_feedback_node"]):
        print(chunk)

    print("인터럽트 걸림")    
    while 1:
        current_graph_state = graph.get_state(config)
        
        if not current_graph_state.next:
            print("반복 종료 ")
            break
        
        user_feedback = input("Press Enter to continue...")
        
        graph.update_state(config , {"user_feedback": user_feedback})
        for chunk in graph.stream(None , stream_mode="updates" , config=config , interrupt_before=["wait_for_user_feedback_node"]):
            for node_name , updated_state in chunk.items():
                if updated_state is not None:
                    print(f"Node: {node_name} , State: {updated_state}")
            
    
    print("그래프 종료!! ")
        
        
            
    
    



