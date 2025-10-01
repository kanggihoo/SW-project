# ruff: noqa: E501
from unittest.mock import patch

import pytest
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from graph.builders.llm_search_once_builder import build_llm_search_once_graph
from graph.model.api_schema import ChatMessage, StatusUpdate, UserInput
from graph.utils.utils import test_message_generator

from .conftest import (
    _parse_stream_line,
    mock_async_generator,
)

# 1. Mock으로 전송할 SSE 데이터 미리 준비 (color_expert 예시)
# 실제 SSE 데이터는 줄바꿈 문자(\n\n)까지 포함하므로 동일하게 맞춰줍니다.


# 2. 실제 동작을 담당할 "비동기 제너레이터 함수"


@pytest.mark.asyncio
async def test_config(test_state, test_config, capture_log):
    logger.info(f'test_config: {test_config}')
    logger.info(f'test_state: {test_state()}')


@pytest.mark.asyncio
@patch('graph.common.node.external_streaming_llm', side_effect=mock_async_generator)
async def test_build_external_llm_graph(mock_llm_call, test_state, test_config, capture_log):
    agent = build_llm_search_once_graph()
    assert isinstance(agent, CompiledStateGraph)
    state = test_state()
    logger.info(f'state: {state}')
    async for line in test_message_generator(agent=agent, input=state, config=test_config, user_input=UserInput(message='데이트')):
        if line.strip():
            parsed = _parse_stream_line(line)
            if parsed is None:
                break
            if isinstance(parsed, ChatMessage):
                assert parsed.content
                if parsed.additional_kwargs.get('type') == 'refer':
                    assert parsed.additional_kwargs.get('product_ids'), f'product_ids is not in additional_kwargs , {parsed.additional_kwargs}'
                    product_ids = parsed.additional_kwargs.get('product_ids')
                    assert isinstance(product_ids, list), f'product_ids is not a list , {product_ids}'
                    logger.info(f'message : {parsed.content} , product_ids : {product_ids}')
            elif isinstance(parsed, StatusUpdate):
                pass

            elif isinstance(parsed, str):
                ...

            else:
                logger.error(f'parsed: {parsed} , type: {type(parsed)}')
                raise Exception()


# @pytest.mark.asyncio
# @patch('graph.common.node.external_streaming_llm', side_effect=mock_async_generator)
# async def test_concurrent_external_llm_graph_execution(mock_llm_call, test_state, test_config):
#     """
#     동시처리 테스트: 여러 expert 타입을 동시에 실행하여 실제로 동시처리가 되는지 확인
#     asyncio.gather()를 사용하여 동시 실행 성능을 측정하고 검증
#     """

#     graph = build_external_llm_graph()
#     assert isinstance(graph, CompiledStateGraph)

#     # 테스트할 expert 타입들
#     expert_types = ['color_expert', 'style_analyst', 'fitting_coordinator']

#     # 각 expert별로 독립적인 state 생성
#     states = [test_state(messages=[HumanMessage(content=f'테스트 메시지 - {expert}')], current_expert=expert) for expert in expert_types]

#     logger.info(f'동시처리 테스트 시작 - {len(expert_types)}개 expert 동시 실행')

#     # 1. 순차 실행 시간 측정
#     start_sequential = time.time()
#     sequential_results = []
#     for i, (state, expert) in enumerate(zip(states, expert_types, strict=True)):
#         logger.info(f'순차 실행 {i + 1}/{len(expert_types)}: {expert}')
#         result = await show_graph_stream(graph=graph, input=state, config=test_config, user_input=UserInput(message=f'순차테스트-{expert}'))
#         sequential_results.append(result)
#     sequential_time = time.time() - start_sequential

#     # 2. 동시 실행 시간 측정 (asyncio.gather 사용)
#     start_concurrent = time.time()

#     # 새로운 state 객체들 생성 (이전 실행으로 인한 상태 변경 방지)
#     concurrent_states = [
#         test_state(messages=[HumanMessage(content=f'동시 테스트 메시지 - {expert}')], current_expert=expert) for expert in expert_types
#     ]

#     concurrent_tasks = [
#         show_graph_stream(graph=graph, input=state, config=test_config, user_input=UserInput(message=f'동시테스트-{expert}'))
#         for state, expert in zip(concurrent_states, expert_types, strict=True)
#     ]

#     logger.info(f'동시 실행 시작 - {len(expert_types)}개 expert 병렬 처리')
#     concurrent_results = await asyncio.gather(*concurrent_tasks)
#     concurrent_time = time.time() - start_concurrent

#     # 3. 성능 비교 및 검증
#     time_improvement = sequential_time - concurrent_time
#     improvement_percentage = (time_improvement / sequential_time) * 100 if sequential_time > 0 else 0

#     logger.info('=== 동시처리 성능 분석 ===')
#     logger.info(f'순차 실행 시간: {sequential_time:.2f}초')
#     logger.info(f'동시 실행 시간: {concurrent_time:.2f}초')
#     logger.info(f'시간 단축: {time_improvement:.2f}초 ({improvement_percentage:.1f}% 개선)')

#     # 4. 동시처리 효과 검증
#     # 동시 실행이 순차 실행보다 빠르거나 비슷해야 함 (네트워크 지연, CPU 오버헤드 고려)
#     assert concurrent_time <= sequential_time + 2.0, f'동시처리 성능이 예상보다 나쁨. 순차: {sequential_time:.2f}초, 동시: {concurrent_time:.2f}초'

#     # 5. 결과 검증
#     assert len(concurrent_results) == len(expert_types), '동시 실행 결과 개수가 expert 개수와 일치하지 않음'
#     assert len(sequential_results) == len(expert_types), '순차 실행 결과 개수가 expert 개수와 일치하지 않음'

#     # 6. Mock 호출 검증
#     # 각 expert 타입별로 적절히 호출되었는지 확인
#     mock_call_args = [call[1] for call in mock_llm_call.call_args_list if 'expert_type' in call[1]]

#     # 모든 expert 타입이 호출되었는지 확인 (순차 + 동시 실행으로 인해 각각 2번씩 호출)
#     expected_call_count = len(expert_types) * 2  # 순차 + 동시
#     assert len(mock_call_args) >= expected_call_count, f'Mock 호출 횟수가 예상보다 적음. 예상: {expected_call_count}, 실제: {len(mock_call_args)}'

#     logger.info(f'동시처리 테스트 완료 - 성능 개선: {improvement_percentage:.1f}%')

#     # 성능 개선이 20% 이상이면 성공으로 간주
#     if improvement_percentage >= 20:
#         logger.info('✅ 동시처리가 효과적으로 작동하고 있습니다!')
#     else:
#         logger.warning(f'⚠️ 동시처리 효과가 미미합니다 ({improvement_percentage:.1f}% 개선)')
