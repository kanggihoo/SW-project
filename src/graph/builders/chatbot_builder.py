from langgraph.graph import END, START, StateGraph

from graph.common.node import chatbot
from graph.common.state import State
from graph.constants import GraphName


def build_chatbot_graph():
    graph_builder = StateGraph(State)
    graph_builder.add_node('chatbot', chatbot)
    graph_builder.add_edge(START, 'chatbot')
    graph_builder.add_edge('chatbot', END)
    chatbot_graph = graph_builder.compile()
    chatbot_graph.name = GraphName.CHATBOT
    return chatbot_graph
