import inspect

from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from graph.constants import GraphName

from .fashion_search_builder import build_fashion_search_graph
from .llm_search_builder import build_llm_search_graph
from .llm_search_once_builder import build_llm_search_once_graph
from .search_subgraph_builder import build_search_subgraph

DEFAULT_AGENT_NAME = GraphName.FASHION_SEARCH

agents = {
    # 'product' : build_product_graph,
    GraphName.SEARCH_SUBGRAPH: build_search_subgraph,
    GraphName.LLM_SEARCH: build_llm_search_graph,
    GraphName.LLM_SEARCH_ONCE: build_llm_search_once_graph,
    GraphName.FASHION_SEARCH: build_fashion_search_graph,
    # GraphName.BEFORE_SEARCH: build_before_search_graph,
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

    builder_func = agents[agent_name]
    sig = inspect.signature(builder_func)

    # kwargs에서 필요한 파라미터들만 필터링
    filtered_kwargs = {}
    for param_name in sig.parameters:
        if param_name in kwargs:
            filtered_kwargs[param_name] = kwargs[param_name]
        else:
            raise ValueError(f"Required parameter '{param_name}' not found in kwargs for agent '{agent_name}'")

    # 필터링된 파라미터들로 함수 호출
    logger.info(f"Building agent '{agent_name}' with parameters: {list(filtered_kwargs.keys())}")
    return builder_func(**filtered_kwargs)


def get_all_agent_info() -> list[str]:
    "이용 가능한 에이전트 이름 목록 반환"
    return [k for k, v in agents.items()]


__all__ = [
    'get_all_agent_info',
    'DEFAULT_AGENT_NAME',
    'build_search_subgraph',
]
