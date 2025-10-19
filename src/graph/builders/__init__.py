import inspect

from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from graph.constants import GraphName

from .chatbot_builder import build_chatbot_graph
from .fashion_search_builder import build_fashion_search_graph
from .llm_search_builder import build_llm_search_graph
from .llm_search_once_builder import build_llm_search_once_graph
from .search_subgraph_builder import build_search_subgraph

DEFAULT_AGENT_NAME = GraphName.FASHION_SEARCH

agents = {
    GraphName.CHATBOT: build_chatbot_graph,
    # 'product' : build_product_graph,
    GraphName.SEARCH_SUBGRAPH: build_search_subgraph,
    GraphName.LLM_SEARCH: build_llm_search_graph,
    GraphName.LLM_SEARCH_ONCE: build_llm_search_once_graph,
    GraphName.FASHION_SEARCH: build_fashion_search_graph,
}

# def get_graph_builder(agent_name:str)->Callable[[httpx.AsyncClient | None],CompiledStateGraph]:
#     "에이전트 이름으로 그래프 빌더 factory function 반환"
#     if agent_name not in agents:
#         raise ValueError(f"Agent {agent_name} not found")
#     return agents[agent_name]


def get_agent(agent_name: str, **kwargs) -> CompiledStateGraph:
    """Get an agent by name"""
    if agent_name not in agents:
        raise ValueError(f'Agent {agent_name} not found')
    if 'client' not in kwargs:
        raise ValueError('AsnycClient is not given as a keyword argument')

    builder_func = agents[agent_name]
    client = kwargs['client']
    sig = inspect.signature(builder_func)
    if 'client' in sig.parameters:
        logger.info(f"Building agent '{agent_name}' with HTTP client...")
        return builder_func(client=client)
    return builder_func()


def get_all_agent_info() -> list[str]:
    "이용 가능한 에이전트 이름 목록 반환"
    return [k for k, v in agents.items()]


__all__ = [
    'get_all_agent_info',
    'DEFAULT_AGENT_NAME',
    'build_search_subgraph',
]
