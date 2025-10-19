from unittest.mock import patch

import pytest
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from graph.builders.llm_search_builder import build_llm_search_graph
from graph.model.api_schema import ChatMessage, UserInput
from graph.utils.utils import test_message_generator

from .conftest import (
    _parse_stream_line,
    mock_async_generator,
)


@pytest.mark.asyncio
class TestSearchNode:
    """Test cases for search_node"""

    async def test_config(self, test_state, test_config, capture_log):
        logger.info(f'test_config: {test_config}')
        state = test_state(experts_to_run=['color_expert', 'style_analyst', 'fitting_coordinator'])
        logger.info(f'state: {state}')
        assert state['experts_to_run'] == ['color_expert', 'style_analyst', 'fitting_coordinator']

    @patch('graph.common.node.external_streaming_llm', side_effect=mock_async_generator)
    async def test_build_llm_search(self, mock_llm_call, test_state, test_config, capture_log):
        agent = build_llm_search_graph()
        assert isinstance(agent, CompiledStateGraph)
        state = test_state(experts_to_run=['color_expert', 'style_analyst', 'fitting_coordinator'])
        logger.info(f'state: {state}')
        async for line in test_message_generator(agent=agent, input=state, config=test_config, user_input=UserInput(message='데이트')):
            if line.strip():
                parsed = _parse_stream_line(line)
                if parsed is None:
                    break

                if isinstance(parsed, ChatMessage):
                    assert parsed.content
                    if parsed.additional_kwargs.get('type') == 'refer':
                        assert parsed.additional_kwargs.get('product_ids')
                        product_ids = parsed.additional_kwargs.get('product_ids')
                        assert isinstance(product_ids, list)
                        logger.info(f'message : {parsed.content} , product_ids : {product_ids}')
                    else:
                        logger.error(f'parsed: {parsed} , type: {type(parsed)}')
                        raise Exception()

                # if isinstance(parsed, ChatMessage):
                #     assert parsed.content
                #     assert parsed.additional_kwargs.get('type') == 'refer'
                #     assert parsed.additional_kwargs.get('product_ids')

    async def test_graph_properties(self, test_state, test_config, capture_log):
        agent = build_llm_search_graph()
        assert isinstance(agent, CompiledStateGraph)
        logger.info(dir(agent))
        logger.info(agent.get_input_jsonschema())
        logger.info(agent.get_input_schema())
        logger.info(agent.get_name())
        logger.info(agent.name)

    # @pytest.mark.asyncio
    # async def test_search_node_success(self, mock_state, mock_config_for_search_node):
    #     """Test successful search operation"""
    #     # Given
    #     test_state = mock_state.copy()
    #     test_state['expert_opinions'] = '색상 조합 추천: 빨간 상의와 검은색 하의'
    #     test_state['current_expert'] = 'color_expert'

    #     with patch('graph.agents.llm_search.llm_search.get_stream_writer') as mock_stream_writer:
    #         mock_writer = Mock()
    #         mock_stream_writer.return_value = mock_writer

    #         # When
    #         result = await search_node(test_state, mock_config_for_search_node)

    #         # Then
    #         assert 'messages' in result
    #         assert len(result['messages']) > 0
    #         message = result['messages'][0]
    #         assert hasattr(message, 'content')
    #         assert len(message.content) > 0
    #         print('✅ search_node 성공 실행 확인')
    #         print(f'   생성된 메시지 수: {len(result["messages"])}')
    #         print(f'   첫 번째 메시지 내용: {message.content[:100]}...')

    # @pytest.mark.asyncio
    # async def test_search_node_empty_search_results(self, mock_state, mock_config_for_search_node):
    #     """Test handling of empty search results"""
    #     # Given
    #     test_state = mock_state.copy()
    #     test_state['expert_opinions'] = '분석된 내용'
    #     test_state['current_expert'] = 'style_anal'

    #     # Mock empty search results
    #     mock_empty_service = Mock()
    #     mock_empty_service.search_by_query = AsyncMock(return_value={'data': [], 'total_count': 0, 'message': 'No results found'})

    #     config = MockRunnableConfig({'configurable': {'search_service': mock_empty_service}})

    #     with patch('graph.agents.llm_search.llm_search.get_stream_writer') as mock_stream_writer:
    #         mock_writer = Mock()
    #         mock_stream_writer.return_value = mock_writer

    #         # When
    #         result = await search_node(test_state, config)

    #         # Then
    #         assert 'messages' in result
    #         print('✅ search_node 빈 검색 결과 처리 확인')

    # @pytest.mark.asyncio
    # async def test_search_node_error_handling(self, mock_state, mock_config_for_search_node):
    #     """Test error handling in search node"""
    #     # Given
    #     test_state = mock_state.copy()
    #     test_state['expert_opinions'] = '분석 내용'
    #     test_state['current_expert'] = 'fitting_coordinater'

    #     # Mock service to raise an error
    #     mock_error_service = Mock()
    #     mock_error_service.search_by_query = AsyncMock(side_effect=Exception('Search service error'))

    #     config = MockRunnableConfig({'configurable': {'search_service': mock_error_service}})

    #     with patch('graph.agents.llm_search.llm_search.get_stream_writer') as mock_stream_writer:
    #         mock_writer = Mock()
    #         mock_stream_writer.return_value = mock_writer

    #         # When
    #         result = await search_node(test_state, config)

    #         # Then
    #         assert 'messages' in result
    #         assert len(result['messages']) > 0
    #         message = result['messages'][0]
    #         assert '오류가 발생했습니다' in message.content
    #         print('✅ search_node 에러 처리 확인')
