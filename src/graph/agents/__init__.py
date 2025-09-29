from collections.abc import Callable

import httpx
from langgraph.graph.state import CompiledStateGraph

from graph.builders.external_llm_builder import build_external_llm_graph
from graph.builders.llm_search_builder import build_llm_search_graph

# from .gather_info import build_graph as build_gather_info_graph
DEFAULT_AGENT_NAME = 'gather_info'

agents = {
    # 'chatbot': build_chatbot_graph(),
    # 'product' : build_product_graph,
    # 'search' : build_search_graph,
    'external_llm': build_external_llm_graph(),
    'llm_search': build_llm_search_graph(),
    # "gather_info" : build_gather_info_graph,
}

# def get_graph_builder(agent_name:str)->Callable[[httpx.AsyncClient | None],CompiledStateGraph]:
#     "에이전트 이름으로 그래프 빌더 factory function 반환"
#     if agent_name not in agents:
#         raise ValueError(f"Agent {agent_name} not found")
#     return agents[agent_name]


def get_agent(agent_name: str) -> CompiledStateGraph:
    """Get an agent by name"""
    if agent_name not in agents:
        raise ValueError(f'Agent {agent_name} not found')
    return agents[agent_name]


def get_all_agent_info() -> list[str]:
    "이용 가능한 에이전트 이름 목록 반환"
    return [k for k, v in agents.items()]


__all__ = [
    'get_all_agent_info',
    'DEFAULT_AGENT_NAME',
]
