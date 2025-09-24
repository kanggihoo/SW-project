# Combined External LLM and Search Agent
from langgraph.config import get_stream_writer 
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import BaseMessage
from typing import Annotated, TypedDict
from functools import partial

import json
import httpx
import logging

from model.type import SSETypes
from model.schema import StatusUpdate
from utils.messages import create_message
from agents.external_llm.utils import external_streaming_llm
from wrapper.search_wrapper import VectorSearchAPIWrapper

from graph.schemas import State
from graph.router import route_expert_loop

logger = logging.getLogger(__name__)

# class State(TypedDict):
#     """Combined LLM Search state that includes both external LLM and search functionality"""
#     messages: Annotated[list[BaseMessage], add_messages] = []
#     metadata: str = ""
#     search_image_context: str = ""


async def pop_next_expert_node(state: State):
    """전문가 리스트에서 다음 전문가를 꺼내 'current_expert'로 설정"""
    print("\n--- 노드 실행: pop_next_expert_node ---")
    experts_to_run = state["experts_to_run"]
    print(f"experts_to_run: {experts_to_run}")
    current_expert = experts_to_run.pop(0)
    print(f"  (이번 전문가: {current_expert})")
    return {
        "current_expert": current_expert,
        "experts_to_run": experts_to_run
    }


async def external_llm_node(state: State, http_session: httpx.AsyncClient, api_endpoint: str) -> State:
    """외부 LLM 스트리밍 결과를 반환하는 노드 - 사용자 입력을 분석하여 검색 쿼리 생성"""
    text = state["user_message"]
    current_expert = state.get("current_expert")
    writer = get_stream_writer()
    response_text = ""
    
    
    content = StatusUpdate(
        state="start", 
        content=f"{current_expert} 의류 조합 분석 시작", 
        task_id=current_expert
    ).model_dump()
    writer({"type": SSETypes.STATUS.value, "content": content})
    
    try:
        async for chunk in external_streaming_llm(text, api_endpoint, http_session , expert_type=current_expert):
            chunk = chunk.strip()
            if chunk.startswith("data: "):
                data = chunk[6:]
                parsed = json.loads(data)
                match parsed["type"]:
                    case SSETypes.TOKEN.value:
                        response_text += parsed["content"]
                        writer({"type": SSETypes.TOKEN.value, "content": parsed["content"]})
                    case SSETypes.STATUS.value:
                        writer({"type": SSETypes.STATUS.value, "content": parsed["content"]})
                    case SSETypes.END.value:
                        content = StatusUpdate(
                            state="end", 
                            content=f"{current_expert} 분석 완료", 
                            task_id=current_expert
                        ).model_dump()
                        writer({"type": SSETypes.STATUS.value, "content": content})
                        break
    except Exception as e:
        logger.error(f"Error in external LLM node: {e}")
        response_text = "의류 분석 중 오류가 발생했습니다."
        content = StatusUpdate(
            state="error", 
            content=f"{current_expert} 분석 오류", 
            task_id=current_expert,
            error_details=str(e)
        ).model_dump()
        writer({"type": SSETypes.STATUS.value, "content": content})

    return State(
        expert_opinions=response_text,
    )

#TODO : 여기서 쿼리 분석과 벡터 검색을 분리해서 노드 작성
async def search_node(state: State, search_api_wrapper: VectorSearchAPIWrapper) -> State:
    """외부 LLM 결과를 기반으로 벡터 검색을 수행하는 노드"""
    writer = get_stream_writer()
    writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="start", content="이미지 검색 시작", task_id="search").model_dump()})
    
    # 마지막 메시지(외부 LLM 결과)를 검색 쿼리로 사용
    expert_opinions = state["expert_opinions"]
    current_expert = state["current_expert"]
    
    try:
        response = await search_api_wrapper.search(expert_opinions)
        
        writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="end", content="이미지 검색 완료!", task_id="search").model_dump()})
        
        metadata = {"expert_type": current_expert}
        image_urls = [data["image_url"] for data in response.get("data", [])]
        response["metadata"] = metadata
        # 검색 결과와 함께 메시지 생성
        search_result_message = create_message(
            message_type="ai", 
            content=expert_opinions, 
            metadata_type="image", 
            image_urls=image_urls, 
            metadata=response
        )
        return {"messages":[search_result_message]}
        
    except Exception as e:
        logger.error(f"Error in search node: {e}")
        writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="error", content="이미지 검색 오류", task_id="search", error_details=str(e)).model_dump()})
        
        error_message = create_message(
            message_type="ai", 
            content="이미지 검색 중 오류가 발생했습니다."
        )
        
        return {"messages":[error_message]}

def build_graph(http_session: httpx.AsyncClient, api_endpoint: str = None) -> StateGraph:
    """Combined external LLM and search graph builder
    
    Flow: 사용자 입력 -> external_llm_node -> search_node
    - external_llm_node: 사용자 입력을 분석하여 의류 조합 추천
    - search_node: 외부 LLM 결과를 기반으로 이미지 검색 수행
    """
    if api_endpoint is None:
        host = "http://3.35.85.182"
        port = "6020"
        path = "/llm/api/expert/single/stream"
        api_endpoint = f"{host}:{port}{path}"
    
    # Create node functions with bound parameters
    external_llm_partial = partial(
        external_llm_node, 
        http_session=http_session, 
        api_endpoint=api_endpoint
    )
    
    search_partial = partial(
        search_node, 
        search_api_wrapper=VectorSearchAPIWrapper(http_session)
    )
    
    # Build the graph
    graph_builder = StateGraph(State)
    
    # Add nodes
    graph_builder.add_node("pop_next_expert", pop_next_expert_node)
    graph_builder.add_node("external_llm", external_llm_partial)
    graph_builder.add_node("search", search_partial)
    
    # Define edges: START -> external_llm -> search -> END
    graph_builder.add_edge(START, "pop_next_expert")
    graph_builder.add_edge("pop_next_expert", "external_llm")
    graph_builder.add_edge("external_llm", "search")
    
    graph_builder.add_conditional_edges(
        "search",
        route_expert_loop,
        {
            "continue_loop": "pop_next_expert",
            "end_loop": END
        }
    )
    
    compiled_graph = graph_builder.compile()
    compiled_graph.name = "llm_search"
    
    return compiled_graph
