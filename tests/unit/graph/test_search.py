from unittest.mock import AsyncMock, Mock, patch

import pytest

from graph.common.node import search_node


class TestSearchNode:
    """Test cases for search_node"""

    @pytest.mark.asyncio
    async def test_search_node_success(self, mock_state, mock_config_for_search_node):
        """Test successful search operation"""
        # Given
        test_state = mock_state.copy()
        test_state['expert_opinions'] = '색상 조합 추천: 빨간 상의와 검은색 하의'
        test_state['current_expert'] = 'color_expert'

        with patch('graph.agents.llm_search.llm_search.get_stream_writer') as mock_stream_writer:
            mock_writer = Mock()
            mock_stream_writer.return_value = mock_writer

            # When
            result = await search_node(test_state, mock_config_for_search_node)

            # Then
            assert 'messages' in result
            assert len(result['messages']) > 0
            message = result['messages'][0]
            assert hasattr(message, 'content')
            assert len(message.content) > 0
            print('✅ search_node 성공 실행 확인')
            print(f'   생성된 메시지 수: {len(result["messages"])}')
            print(f'   첫 번째 메시지 내용: {message.content[:100]}...')

    @pytest.mark.asyncio
    async def test_search_node_empty_search_results(self, mock_state, mock_config_for_search_node):
        """Test handling of empty search results"""
        # Given
        test_state = mock_state.copy()
        test_state['expert_opinions'] = '분석된 내용'
        test_state['current_expert'] = 'style_anal'

        # Mock empty search results
        mock_empty_service = Mock()
        mock_empty_service.search_by_query = AsyncMock(return_value={'data': [], 'total_count': 0, 'message': 'No results found'})

        config = MockRunnableConfig({'configurable': {'search_service': mock_empty_service}})

        with patch('graph.agents.llm_search.llm_search.get_stream_writer') as mock_stream_writer:
            mock_writer = Mock()
            mock_stream_writer.return_value = mock_writer

            # When
            result = await search_node(test_state, config)

            # Then
            assert 'messages' in result
            print('✅ search_node 빈 검색 결과 처리 확인')

    @pytest.mark.asyncio
    async def test_search_node_error_handling(self, mock_state, mock_config_for_search_node):
        """Test error handling in search node"""
        # Given
        test_state = mock_state.copy()
        test_state['expert_opinions'] = '분석 내용'
        test_state['current_expert'] = 'fitting_coordinater'

        # Mock service to raise an error
        mock_error_service = Mock()
        mock_error_service.search_by_query = AsyncMock(side_effect=Exception('Search service error'))

        config = MockRunnableConfig({'configurable': {'search_service': mock_error_service}})

        with patch('graph.agents.llm_search.llm_search.get_stream_writer') as mock_stream_writer:
            mock_writer = Mock()
            mock_stream_writer.return_value = mock_writer

            # When
            result = await search_node(test_state, config)

            # Then
            assert 'messages' in result
            assert len(result['messages']) > 0
            message = result['messages'][0]
            assert '오류가 발생했습니다' in message.content
            print('✅ search_node 에러 처리 확인')
