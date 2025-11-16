from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio
from langchain.tools import StructuredTool

from app.services.musinsa import MusinsaAPIWrapper
from graph.tools.definition import PRODUCT_TOOL_DEFINITION
from graph.tools.handlers.product_handlers import ProductToolHandlers


@pytest_asyncio.fixture
async def httpx_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient() as client:
        yield client


def test_build_product_info_agent_subgraph(httpx_client: httpx.AsyncClient):
    # Bind tools from handler based on TOOL_DEFINITION
    service = MusinsaAPIWrapper(client=httpx_client)
    handlers = ProductToolHandlers(service, cache_client=None, task_queue_client=None, db_repository=None)

    bound_tools: list[StructuredTool] = []
    for spec in PRODUCT_TOOL_DEFINITION:
        name = spec['name']
        args_schema = spec['args_schema']
        handler_func = getattr(handlers, f'handle_{name}')
        tool = StructuredTool.from_function(
            func=None,
            name=name,
            description=(handler_func.__doc__ or name),
            args_schema=args_schema,
            coroutine=handler_func,
        )
        bound_tools.append(tool)

    for tool in bound_tools:
        print(tool)
    print(bound_tools)
