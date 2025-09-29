import sys

import httpx
import pytest
import pytest_asyncio
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger

from graph.model.graph_schemas import ClothSearch


@pytest_asyncio.fixture(scope='session')
async def http_client():
    """Real httpx AsyncClient fixture with proper resource management."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture(scope='session')
def capture_log():
    """Real logger fixture with proper resource management."""
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level='INFO',
        format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> \n \
             <level>{message}</level>',
        colorize=True,
    )
    yield logger
    logger.remove()


# 사용가능한 전문가 : color_expert , fitting_coordinator , style_analyst
@pytest.fixture
def test_state():
    """Provides a test state for the external_llm_node."""
    default_state = {
        'messages': [HumanMessage(content='데이트')],
        'user_message': '데이트',
        'current_expert': 'style_analyst',
        'experts_to_run': ['style_analyst'],
        'expert_opinions': '',
        'cloth_search': ClothSearch(tpo='데일리', color='검은색', style='캐주얼'),
        'is_info_gathering_complete': False,
        'product_id': None,
        'intent': None,
        'last_updated_fields': None,
    }

    def generate_state(**kwargs) -> dict:
        if kwargs:
            for key, value in kwargs.items():
                if key in default_state:
                    default_state[key] = value
        return default_state

    return generate_state


@pytest.fixture
def test_config(http_client) -> RunnableConfig:
    """Provides a test config with real httpx client."""
    return {
        'configurable': {
            'http_session': http_client,
            'api_endpoint': 'https://the-first-take.com/llm/api/expert/single/stream',
        }
    }
