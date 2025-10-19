# flake8: noqa
"""Graph test fixtures and shared utilities"""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
import httpx
import asyncio

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from graph.model.graph_schemas import ClothSearch
from loguru import logger
import sys
import json
from graph.constants import SSETypes
from graph.model.api_schema import ChatMessage, StatusUpdate


def serialize_log(record):
    """로그 레코드를 커스텀 JSON으로 직렬화"""
    log_entry = {
        'timestamp': record['time'].strftime('%Y-%m-%d %H:%M:%S'),
        'level': record['level'].name,
        'message': record['message'],
        'position': f'{record["module"]}:{record["function"]}:{record["line"]}',
    }

    # extra 필드가 있으면 추가
    if record['extra']:
        log_entry.update(record['extra'])

    # return json.dumps(log_entry, ensure_ascii=False)
    return log_entry


def formatter(record):
    """format 파라미터용 함수 - 템플릿 문자열 반환"""
    record['extra']['serialized'] = serialize_log(record)
    return '{extra[serialized]}\n'


@pytest.fixture(scope='session')
def capture_log():
    """Real logger fixture with proper resource management."""
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level='DEBUG',
        format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>',
        colorize=True,
    )
    yield logger
    logger.remove()


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


search_service = AsyncMock()
search_service.search_by_query.return_value = {
    'query': 'test',
    'data': [{'product_id': 'product_id1'}, {'product_id': 'product_id2'}],
    'total_count': 2,
    'message': 'Search completed successfully',
}


@pytest.fixture
def test_config(http_client) -> RunnableConfig:
    """Provides a test config with real httpx client."""
    return {
        'configurable': {
            'http_session': http_client,
            'api_endpoint': 'https://the-first-take.com/llm/api/expert/single/stream',
            'thread_id': 'test_thread_id',
            'search_service': search_service,
        }
    }


def _parse_stream_line(line: str) -> ChatMessage | StatusUpdate | str | None:
    line = line.strip()
    if line.startswith('data: '):
        data = line[6:]
        try:
            parsed: dict[str, Any] = json.loads(data)
        except Exception as e:
            raise Exception(f'Failed to parse stream line: {e}')
        # print("client.py : _parse_stream_line : parsed => " , parsed)
        match parsed['type']:
            case SSETypes.END.value:
                return None
            case SSETypes.MESSAGE.value:
                try:
                    return ChatMessage.model_validate(parsed['content'])
                except Exception as e:
                    raise Exception(f'Failed to parse stream line: {e}')

            case SSETypes.TOKEN.value:
                return parsed['content']
            case SSETypes.STATUS.value:
                try:
                    return StatusUpdate.model_validate(parsed['content'])
                except Exception as e:
                    raise Exception(f'Failed to parse stream line: {e}')

            case SSETypes.ERROR.value:
                error_msg = 'Error: ' + parsed['content']
                return ChatMessage(
                    type='ai',
                    content=error_msg,
                )
    return None


MOCK_DATA_COLOR_EXPERT = [
    'data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "S3 매칭 성공: 8개 착장 발견", "error_details": null}}\n\n',
    'data: {"type": "token", "content": "화이트 베이직 티셔츠에"}\n\n',
    'data: {"type": "token", "content": " 베이지 슬림 슬랙스는"}\n\n',
    'data: {"type": "token", "content": " 톤온톤 원리에 따라"}\n\n',
    'data: {"type": "token", "content": " 부드러운 색상 조화를 이룹니다."}\n\n',
    'data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "전문가 분석 완료", "error_details": null}}\n\n',
    'data: {"type": "[DONE]", "content": ""}\n\n',
]

MOCK_DATA_STYLE_ANALYST = [
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "S3 매칭 성공: 5개 착장 발견", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "최종 착장 선택: 056449ada2366d2f8f8266a3f69c923e", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "전문가 분석 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "Claude API 호출 중...", "error_details": null}}\n\n',
    'data: {"type": "token", "content": "죄송하지만 현"}\n\n',
    'data: {"type": "token", "content": "재 여름"}\n\n',
    'data: {"type": "token", "content": "기 좋아."}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "전문가 분석 완료", "error_details": null}}\n\n',
    'data: {"type": "[DONE]", "content": ""}\n\n',
]

MOCK_DATA_FITTING_COORDINATOR = [
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "S3 매칭 성공: 15개 착장 발견", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "최종 착장 선택: 561a7db1f64f00f80a2160216c855d8f", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "전문가 분석 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "Claude API 호출 중...", "error_details": null}}\n\n',
    'data: {"type": "token", "content": "네이"}\n\n',
    'data: {"type": "token", "content": "비 데님 반팔 "}\n\n',
    'data: {"type": "token", "content": " 느낌을 더"}\n\n',
    'data: {"type": "token", "content": "해줘."}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "전문가 분석 완료", "error_details": null}}\n\n',
    'data: {"type": "[DONE]", "content": ""}\n\n',
]


async def _get_mock_stream(expert_type):
    """미리 정의된 SSE 데이터를 0.5초 간격으로 yield하는 비동기 제너레이터"""

    match expert_type:
        case 'color_expert':
            mock_sse_data = MOCK_DATA_COLOR_EXPERT
        case 'style_analyst':
            mock_sse_data = MOCK_DATA_STYLE_ANALYST
        case 'fitting_coordinator':
            mock_sse_data = MOCK_DATA_FITTING_COORDINATOR
        case _:
            mock_sse_data = MOCK_DATA_COLOR_EXPERT
    for chunk in mock_sse_data:
        yield chunk
        await asyncio.sleep(0.1)  # 0.5초 지연


# 3. @patch의 side_effect로 사용될 "일반 함수"
def mock_async_generator(*args, **kwargs):
    """
    patch에 의해 호출될 함수.
    실제 비동기 제너레이터 객체를 생성하여 반환합니다.
    """
    print(f'\n[Mock] external_streaming_llm 호출됨({kwargs.get("expert_type")}). Mock 스트림을 반환합니다.')
    # _get_mock_stream 함수를 호출하여 제너레이터 객체를 생성하고 즉시 반환
    return _get_mock_stream(kwargs.get('expert_type'))


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
