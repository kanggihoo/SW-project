from langchain_core.runnables import RunnableConfig
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# State
from .states import ClothingRAGState

# Utils
from .utils import embedding_query , search_vector_db , get_product_details, rerank_items  , modify_query

# Annotations
from typing import Any

# langgraph
from langgraph.graph import END





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

async def select_final_item_node(state: ClothingRAGState , config: RunnableConfig) -> dict[str, Any]:
    print("--- Node: select_final_item_node ---")
    ranked_candidates = state.get("ranked_candidates")[0]
    user_query = state.get("user_query")
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
    
    final_response = ""
    async for chunk in chain.astream({"user_query": user_query}):
        # print(chunk, end="", flush=True)
        # Yield each chunk as a partial update
        yield {"llm_stream_chunk": chunk}
        final_response += chunk

    print("\n--- End of LLM Stream ---")
    # Yield the final complete message to update the state
    yield {"final_recommendation": final_response}

# 사용자 피드백 수집 노드 
def wait_for_user_feedback_node(state: ClothingRAGState) -> dict[str, Any]:
    print("--- Node: wait_for_user_feedback_node (after interrupt, expecting feedback in state) ---")
    print("user_feedback : ", state.get("user_feedback"))
    return {}

