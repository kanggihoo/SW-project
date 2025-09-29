# from langchain_core.messages import HumanMessage, AIMessage , BaseMessage , SystemMessage
# from langgraph.graph import StateGraph, START, END , add_messages
# from langchain_core.runnables import RunnableConfig
# from langchain_core.language_models import BaseChatModel

# from typing import Annotated , TypedDict
# import logging
# import httpx

# from graph.llm import get_llm_model
# from graph.settings import settings
# from graph.agents.prompt import chatbot_prompt
# from graph.utils.messages import create_message

# logger = logging.getLogger(__name__)

# from graph.common.state import State


# async def chatbot(state:State , config:RunnableConfig)->State:

#     print("chatbot 노드 시작")
#     model : BaseChatModel = get_llm_model(config["configurable"].get("model" , settings.DEFAULT_LLM_MODEL))
#     print("model: " , model , settings.DEFAULT_LLM_MODEL)
#     chain = chatbot_prompt | model
#     response = await chain.ainvoke({"messages":state["messages"]})
#     response = create_message(message_type="ai", content=response.content)
#     return State(messages=[response])

# def build_graph(http_session:httpx.AsyncClient | None = None):
#     graph_builder = StateGraph(State)
#     graph_builder.add_node("chatbot", chatbot)
#     graph_builder.add_edge(START, "chatbot")
#     graph_builder.add_edge("chatbot", END)
#     chatbot_graph = graph_builder.compile()
#     chatbot_graph.name = "chatbot"
#     return chatbot_graph


