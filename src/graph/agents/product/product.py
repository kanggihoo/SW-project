# react 구조 이용한 musinsa 상품 조회 도구 연결 
from langgraph.graph import StateGraph , START , END
from langgraph.graph.message import add_messages 
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage , BaseMessage , SystemMessage 
from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder
from langchain_core.tools import StructuredTool


from typing import Annotated , TypedDict 
import logging
import httpx

from settings import settings 
from llm import get_llm_model 
from wrapper.musinsa_wrapper import MusinsaAPIWrapper
from agents.tools.definition import TOOL_DEFINITION




logger = logging.getLogger(__name__)
class ProductState(TypedDict):
    """Chatbot state"""
    messages : Annotated[list[BaseMessage], add_messages] = []


def build_graph(http_session:httpx.AsyncClient):
    musinsa_api_wrapper = MusinsaAPIWrapper(http_session)
    bound_tools = []
    for tool_info in TOOL_DEFINITION:
        func_name = tool_info["name"]
        func = getattr(musinsa_api_wrapper, func_name)
        doc = func.__doc__
        bound_tool = StructuredTool.from_function(
            func=None,
            name=func_name,
            description=doc,
            args_schema=tool_info["args_schema"],
            coroutine=func
            )
        bound_tools.append(bound_tool)
        
    product_agent = create_react_agent(
        model = get_llm_model(settings.DEFAULT_LLM_MODEL),
        tools = bound_tools,
        prompt = "You are a helpful assistant."
    )
    return product_agent



    