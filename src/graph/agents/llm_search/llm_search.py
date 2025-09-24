# Combined External LLM and Search Agent
from langgraph.config import get_stream_writer , RunnableConfig
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import BaseMessage
from typing import Annotated, TypedDict
from functools import partial

import json
import httpx
import logging

from db.services.search import SearchService
from graph.model.constants import SSETypes
from graph.model.api_schema import StatusUpdate
from graph.utils.messages import create_message
from agents.external_llm.utils import external_streaming_llm
from graph.common.state import State
from graph.common.router import route_expert_loop


logger = logging.getLogger(__name__)


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


async def external_llm_node(state: State,  api_endpoint: str , config:dict) -> State:
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
        async for chunk in external_streaming_llm(text, api_endpoint, http_session=config["configurable"]["http_session"], expert_type=current_expert):
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

async def search_node(state: State, config:dict) -> State:
    """외부 LLM 결과를 기반으로 벡터 검색을 수행하는 노드"""
    writer = get_stream_writer()
    writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="start", content="이미지 검색 시작", task_id="search").model_dump()})
    
    expert_opinions = state["expert_opinions"]
    current_expert = state["current_expert"]
    search_service: SearchService = config["configurable"]["search_service"]
    try:
        # TODO : 반환된 값에 대한 리랭킹 필요 
        search_result = await search_service.search_by_query(expert_opinions, limit=1)
        
        writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="end", content="이미지 검색 완료!", task_id="search").model_dump()})
        
        image_urls = []
        if search_result and "data" in search_result:
            for item in search_result["data"]:
                url = search_service._generate_representative_image_url(item)
                if url:
                    image_urls.append(url)

        metadata = {"expert_type": current_expert, "search_response": search_result}
        
        search_result_message = create_message(
            message_type="ai", 
            content=expert_opinions, 
            metadata_type="image", 
            image_urls=image_urls, 
            metadata=metadata
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

def build_graph(api_endpoint: str = None) -> StateGraph:
    """Combined external LLM and search graph builder
    
    Flow: 사용자 입력 -> external_llm_node -> search_node
    - external_llm_node: 사용자 입력을 분석하여 의류 조합 추천
    - search_node: 외부 LLM 결과를 기반으로 이미지 검색 수행
    """
    if api_endpoint is None:
        host = "https://the-first-take.com"
        path = "llm/api/expert/single/stream"
        api_endpoint = f"{host}/{path}"
    
    external_llm_partial = partial(
        external_llm_node, 
        api_endpoint=api_endpoint
    )
    
    # search_partial = partial(
    #     search_node, 
    #     search_service=search_service
    # )
    
    graph_builder = StateGraph(State)
    
    graph_builder.add_node("pop_next_expert", pop_next_expert_node)
    graph_builder.add_node("external_llm", external_llm_partial)
    graph_builder.add_node("search", search_node)
    
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
'''
│ > @src/graph/agents/llm_search/llm_search.py  여기서 이전에는 vector 검색을 하기 위해 별도의 api로 감싸서 진행을 했지만 지금은 db관련한 vector db 모듈이 현재 프로젝트에 존재하기 때문에 특정 노드에서 partial 함수에서 전달받은 RepositoryDep를 이용해서      │
│   벡터 검색을 진행하도록 코드를 변경해주세요 . RepositoryDep에 대한 내용은 다음 코드를 참고해주세요 @src/graph/services/search.py   
'''