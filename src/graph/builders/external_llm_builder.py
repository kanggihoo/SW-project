# External LLM streaming graph builder
import logging

from langgraph.graph import START, StateGraph

from graph.common.node import external_llm_node
from graph.common.state import State

logger = logging.getLogger(__name__)


def build_external_llm_graph():
    """Build external LLM streaming graph

    Args:
        http_session: HTTP client session for external API calls
        api_endpoint: External LLM API endpoint URL

    Returns:
        Compiled graph for external LLM streaming
    """

    # Create the node function with bound parameters
    # Build the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node('external_streaming_llm', external_llm_node)
    graph_builder.add_edge(START, 'external_streaming_llm')

    return graph_builder.compile()
