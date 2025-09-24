from langchain_core.messages import HumanMessage, AIMessage , BaseMessage , SystemMessage 
from langgraph.graph import StateGraph, START, END , add_messages 
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel

from typing import Annotated , TypedDict 
from llm import get_llm_model 
from settings import settings 
from agents.prompt import chatbot_prompt
import logging
import httpx
from utils.messages import create_message

logger = logging.getLogger(__name__)

class ChatbotState(TypedDict):
    """Chatbot state"""
    messages : Annotated[list[BaseMessage], add_messages] = []


async def chatbot(state:ChatbotState , config:RunnableConfig)->ChatbotState:
    
    print("chatbot 노드 시작")
    model : BaseChatModel = get_llm_model(config["configurable"].get("model" , settings.DEFAULT_LLM_MODEL))
    print("model: " , model , settings.DEFAULT_LLM_MODEL)
    chain = chatbot_prompt | model 
    response = await chain.ainvoke({"messages":state["messages"]})
    response = create_message(message_type="ai", content=response.content)
    print("chatbot 반환")
    return ChatbotState(messages=[response])

def build_graph(http_session:httpx.AsyncClient | None = None):
    graph_builder = StateGraph(ChatbotState)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    chatbot_graph = graph_builder.compile()
    chatbot_graph.name = "chatbot"
    return chatbot_graph








