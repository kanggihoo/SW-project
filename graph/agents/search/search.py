from langchain_core.messages import HumanMessage, AIMessage , BaseMessage , SystemMessage 
from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END , add_messages 
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langgraph.config import get_stream_writer

from typing import Annotated , TypedDict 
import logging
import httpx
import asyncio
from functools import partial

# from app.config.dependencies import get_s3_manager
# from wrapper.search_wrapper import VectorSearchAPIWrapper

from graph.settings import settings 
from graph.llm import get_llm_model 
from graph.model.type import SSETypes
from graph.model.schema import StatusUpdate
from graph.agents.prompt import search_prompt
from graph.utils.messages import create_message
'''
단순히 그래프 호출시 => llm => stat에 llm 결과 넣고, => 해당 llm 쿼리문을 그래도 벡터 검색 => 
반환된 검색 결과를 state혹은 AIMessage 형태로 반환(이때 지금은 검색된 url을 s3key 형태로 parsing 해서 넣기)

이전 state를 기반으로 벡터 검색시 후보를 선정하는데 있어서 reranking 작업이 필요 보이긴 해 (이전에 반환된 데이터에 대해서는 제외하거나 하는 작업)

#CHECK :  벡터 서치의 모든 결과를 그대로 다 AIMessage의 additional_kwargs에 넣어 주어야 하나? 


'''


logger = logging.getLogger(__name__)

class ChatbotState(TypedDict):
    """Chatbot state"""
    messages : Annotated[list[BaseMessage], add_messages] = []
    search_image_context : str = ""


async def chatbot(state:ChatbotState , config:RunnableConfig)->ChatbotState:
    
   
    model : BaseChatModel = get_llm_model(config["configurable"].get("model" , settings.DEFAULT_LLM_MODEL))
    chain = search_prompt | model 
    response = await chain.ainvoke({"messages":state["messages"]})
    response = create_message(message_type="ai", content=response.content)
    return ChatbotState(messages=[response])

async def search(state:ChatbotState , config:RunnableConfig , search_api_wrapper:VectorSearchAPIWrapper)->ChatbotState:
    writer = get_stream_writer()
    writer({"type": SSETypes.STATUS.value, "content":StatusUpdate(state="start", content="이미지 검색 시작" , task_id="search").model_dump()})
    response = await search_api_wrapper.search(state["messages"][-1].content)
    
    writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="end", content="이미지 검색 완료!" , task_id="search").model_dump()})
    
    metadata = {"search_response": response}
    image_urls = [data["image_url"] for data in response.get("data")]
    response = create_message(message_type="ai", content="이미지 검색을 진행했습니다. 관련 이미지 반환!", metadata_type="image", image_urls=image_urls , metadata=metadata)
    return ChatbotState(messages=[response])

async def mock_search(state:ChatbotState , config:RunnableConfig , search_api_wrapper:VectorSearchAPIWrapper)->ChatbotState:
    writer = get_stream_writer()
    sample_image_url_1 = "https://images.unsplash.com/photo-1548407260-da850faa41e3?q=80&w=2070&auto=format&fit=crop"
    sample_image_url_2 = "https://images.unsplash.com/photo-1552733407-5d5c46c3bb3b?q=80&w=1974&auto=format&fit=crop"
    sample_image_url_3 = "https://images.unsplash.com/photo-1501854140801-50d01698950b?q=80&w=2175&auto=format&fit=crop"
        
    writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="start", content="이미지 검색 시작" , task_id="search").model_dump()})
    await asyncio.sleep(15)
    response = create_message(message_type="ai", content="이미지 검색을 진행했습니다. 관련 이미지 반환!", metadata_type="image", image_urls=[sample_image_url_1, sample_image_url_2, sample_image_url_3])
    writer({"type": SSETypes.STATUS.value, "content": StatusUpdate(state="end", content="이미지 검색 완료!" , task_id="search").model_dump()})
    return ChatbotState(messages=[response])


def build_graph(http_session:httpx.AsyncClient):
    graph_builder = StateGraph(ChatbotState)


    search_partial = partial(search, search_api_wrapper=VectorSearchAPIWrapper(http_session))
    # search_partial = mock_search

    
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("search", search_partial)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", "search")
    graph_builder.add_edge("search", END)

    search_graph = graph_builder.compile()
    search_graph.name = "search"
    return search_graph






