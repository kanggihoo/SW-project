import pytest
from langchain_core.messages import HumanMessage


@pytest.mark.asyncio
class TestExternalLLMNode:
    """TDD Test cases for the external_llm_node function using real httpx AsyncClient."""

    async def test_external_llm_node_initialization(self, test_state, test_config):
        """
        Test 1: Verify that the node initializes correctly with proper state and config.
        This is the first TDD test - Red phase: we expect the node to accept our inputs.
        """
        # Given: We have a valid state and config
        state = test_state(messages=[HumanMessage(content='데이트')], current_expert='style_analyst')
        assert state['current_expert'] == 'style_analyst'

        assert test_config['configurable']['http_session'] is not None
        assert test_config['configurable']['api_endpoint'] is not None

        # When/Then: The node should be callable with these parameters
        # This test ensures our fixtures are properly set up

    # @patch('graph.common.node.external_streaming_llm', side_effect=mock_async_generator)
    # async def test_external_llm_node_handles_single_experts(self, mock_writer, test_state, test_config):
    #     """
    #     한명의 전문가 호출 테스트
    #     """
    #     state = test_state(messages=[HumanMessage(content='데이트')], current_expert='style_analyst')

    #     result = await external_llm_node(state, test_config)

    #     assert isinstance(result, dict)
    #     assert 'expert_opinions' in result
    #     assert result['expert_opinions'] != ''
    #     print(f'✅ external_llm_node 성공 실행 확인: {len(result["expert_opinions"])} 문자')

    # @patch('graph.common.node.get_stream_writer', side_effect=mock_get_stream_writer)
    # async def test_external_llm_node_different_experts(self, mock_writer, test_state, test_config):
    #     """
    #     Test 3: Verify that the node works with different expert types.
    #     TDD Red phase: We expect the node to handle various expert types.
    #     """
    #     expert_types = ['color_expert', 'style_analyst', 'fitting_coordinator']

    #     for expert_type in expert_types:
    #         # Given: State with different expert type
    #         state = test_state(messages=[HumanMessage(content='데이트')], current_expert=expert_type)

    #         # When: We call the external_llm_node
    #         result = await external_llm_node(state, test_config)

    #         # Then: We should get a valid response
    #         assert isinstance(result, dict)
    #         assert 'expert_opinions' in result

    # @patch('graph.common.node.get_stream_writer', side_effect=mock_get_stream_writer)
    # async def test_external_llm_node_error_handling(self, mock_writer, test_config):
    #     """
    #     Test 5: Verify that the node handles errors gracefully.
    #     TDD Red phase: We expect proper error handling.
    #     """
    #     # Given: State with invalid data that might cause errors
    #     invalid_state = {
    #         'messages': [HumanMessage(content='Test message')],
    #         'user_message': '',  # Empty message might cause issues
    #         'current_expert': 'invalid_expert',
    #         'experts_to_run': ['invalid_expert'],
    #         'expert_opinions': '',
    #         'cloth_search': ClothSearch(tpo='데일리', color='검은색', style='캐주얼'),
    #         'is_info_gathering_complete': False,
    #         'product_id': None,
    #         'intent': None,
    #         'last_updated_fields': None,
    #     }

    #     # When: We call the external_llm_node with invalid state
    #     result = await external_llm_node(invalid_state, test_config)

    #     # Then: We should still get a response (possibly error message)
    #     assert isinstance(result, dict)
    #     assert 'expert_opinions' in result
