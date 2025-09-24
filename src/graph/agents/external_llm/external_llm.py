# External LLM streaming agent
from langgraph.config import get_stream_writer 
from langgraph.graph import StateGraph, START, add_messages
from langchain_core.messages import BaseMessage
from typing import Annotated, TypedDict, AsyncGenerator

import json
import httpx
from functools import partial
import logging

from model.type import SSETypes
from model.schema import StatusUpdate
from utils.messages import create_message
from .utils import external_streaming_llm

logger = logging.getLogger(__name__)

class ExternalLLMState(TypedDict):
    """External LLM state"""
    messages: Annotated[list[BaseMessage], add_messages] = []
    metadata: str = ""





async def _call_external_streaming_llm(state: ExternalLLMState, http_session: httpx.AsyncClient, api_endpoint: str):
    """외부 LLM 스트리밍 결과를 반환하는 노드"""
    text = state["messages"][-1].content
    writer = get_stream_writer()
    response_text = ""
    #TODO : 각 전문가 연결
    # color_expert, fitting_coordinater, style_anal
    external_agent_name = "style_analyst"
    
    content = StatusUpdate(
        state="start", 
        content=f"{external_agent_name} 의류 조합 분석 시작", 
        task_id=external_agent_name
    ).model_dump()
    writer({"type": SSETypes.STATUS.value, "content": content})
    
    async for chunk in external_streaming_llm(text, api_endpoint, http_session):
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
                        content=f"{external_agent_name} 분석 완료", 
                        task_id=external_agent_name
                    ).model_dump()
                    writer({"type": SSETypes.STATUS.value, "content": content})

    return ExternalLLMState(messages=[create_message(message_type="ai", content=response_text)], metadata="external_llm_response")


def build_graph(http_session: httpx.AsyncClient, api_endpoint: str = None):
    """Build external LLM streaming graph"""
    if api_endpoint is None:
        host = "http://3.35.85.182"
        port = "6020"
        path = "/llm/api/expert/single/stream"
        api_endpoint = f"{host}:{port}{path}"
    
    # Create the node function with bound parameters
    streaming_node = partial(_call_external_streaming_llm, 
                           http_session=http_session, 
                           api_endpoint=api_endpoint)
    
    # Build the graph
    graph_builder = StateGraph(ExternalLLMState)
    graph_builder.add_node("external_streaming_llm", streaming_node)
    graph_builder.add_edge(START, "external_streaming_llm")
    
    return graph_builder.compile()
