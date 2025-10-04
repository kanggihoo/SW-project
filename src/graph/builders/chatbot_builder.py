from langgraph.graph import END, START, StateGraph

from graph.common.node import chatbot
from graph.common.state import State


def build_chatbot_graph():
    graph_builder = StateGraph(State)
    graph_builder.add_node('chatbot', chatbot)
    graph_builder.add_edge(START, 'chatbot')
    graph_builder.add_edge('chatbot', END)
    chatbot_graph = graph_builder.compile()
    chatbot_graph.name = 'chatbot'
    return chatbot_graph
