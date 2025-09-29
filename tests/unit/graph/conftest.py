# flake8: noqa
"""Graph test fixtures and shared utilities"""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
import httpx
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from graph.model.graph_schemas import ClothSearch


@pytest_asyncio.fixture(scope='session')
async def http_client():
    """Real httpx AsyncClient fixture with proper resource management."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


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
            'thread_id': 'test_thread_id',
        }
    }


# @pytest.fixture
# def mock_search_service():
#     """Mock SearchService for testing"""
#     mock_service = Mock()
#     mock_service.search_by_query = AsyncMock()

#     # 설정 결과가 실제 호출 가능하도록 구성
#     async def _mock_search_by_query(query: str, limit: int = 1):
#         return {
#             "data": [
#                 {"product_id": "test_product_123"},
#                 {"product_id": "test_product_456"}
#             ],
#             "total_count": 2,
#             "message": "Search completed successfully"
#         }

#     mock_service.search_by_query = _mock_search_by_query
#     return mock_service


# @pytest.fixture
# def mock_http_session():
# 	"""Mock httpx.AsyncClient for testing"""

# 	async def mock_stream_request(*args, **kwargs):
# 		"""Mock response stream for testing"""
# 		import asyncio

# 		test_data = [
# 			'data: {"type": "status", "message": "분석 시작"}\n\n',
# 			'data: {"type": "content", "chunk": "현재 의류 조합을 분석해보겠습니다."}\n\n',
# 			'data: {"type": "content", "chunk": "색상과 스타일을 검토해드리겠습니다."}\n\n',
# 			'data: {"type": "complete"}\n\n',
# 		]

# 		for data_point in test_data:
# 			yield data_point
# 			await asyncio.sleep(0.01)  # 실제적인 비동기 시뮬레이션

# 	mock_session = Mock()
# 	mock_session.stream = Mock()
# 	mock_session.stream.return_value.__aenter__ = mock_stream_request
# 	mock_session.stream.return_value.__aexit__ = Mock(return_value=None)

# 	return mock_session


# @pytest.fixture
# def mock_config_for_external_llm(mock_http_session):
# 	"""Mock configuration for external_llm_node testing"""

# 	class MockRunnableConfig:
# 		def __init__(self, configurable):
# 			self.configurable = {'configurable': configurable}

# 	return MockRunnableConfig({'http_session': mock_http_session})


# @pytest.fixture
# def mock_config_for_search_node(mock_search_service):
# 	"""Mock configuration for search_node testing"""

# 	class MockRunnableConfig:
# 		def __init__(self, configurable):
# 			self.configurable = {'configurable': configurable}

# 	return MockRunnableConfig({'search_service': mock_search_service})


# @pytest.fixture
# def mock_external_streaming_response():
# 	"""Mock external streaming LLM response"""
# 	from graph.model.constants import SSETypes

# 	mock_data = [
# 		f'data: {{"type": "{SSETypes.STATUS.value}", "content": {{"state": "start", "content": "color_expert 분석 시작", "task_id": "color_expert"}}}}\n\n',
# 		f'data: {{"type": "{SSETypes.TOKEN.value}", "content": "적절한 색상 조합을 추천해드리겠습니다."}}\n\n',
# 		f'data: {{"type": "{SSETypes.TOKEN.value}", "content": "빨간색 상의와 검은색 하의가 잘 어울릴 것 같습니다."}}\n\n',
# 		f'data: {{"type": "{SSETypes.END.value}", "content": ""}}\n\n',
# 	]

# 	return mock_data


# @pytest.fixture
# def test_flow_state():
# 	"""Test state for complete flow testing"""
# 	return {
# 		'messages': [],
# 		'user_message': '출근룩 후보로 검은색 정장을 찾고 있어요',
# 		'experts_to_run': ['color_expert', 'fitting_coordinater'],
# 		'current_expert': None,
# 		'expert_opinions': '',
# 		'cloth_search': {'main_category': 'TOP', 'style': 'FORMAL'},
# 		'is_info_gathering_complete': False,
# 		'product_id': None,
# 		'intent': 'direct_search',
# 		'last_updated_fields': [],
# 	}
