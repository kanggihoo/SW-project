import json
import logging
from collections.abc import AsyncGenerator
from typing import Literal

from graph.model.api_schema import StatusUpdate
from graph.model.constants import SSETypes

logger = logging.getLogger(__name__)


async def external_streaming_llm(
    text: str, api_endpoint: str, http_session, expert_type: Literal['color_expert', 'style_analyst', 'fitting_coordinater']
) -> AsyncGenerator[str, None]:
    """특정 노드에서 외부 LLM 스트리밍 결과를 반환하는 비동기 제너레이터"""
    headers = {'Accept': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    payload = {
        'user_input': text,
        'room_id': 0,
        'expert_type': expert_type,
        'user_profile': {'additionalProp1': {}},
        'context_info': {'additionalProp1': {}},
        'json_data': {'additionalProp1': {}},
    }
    try:
        async with http_session.stream('POST', api_endpoint, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    data = line[6:]
                    parsed = json.loads(data)
                    match parsed['type']:
                        case 'status':
                            content = StatusUpdate(state='progress', content=parsed['message'], task_id=expert_type).model_dump()
                            yield f'data: {json.dumps({"type": SSETypes.STATUS.value, "content": content})}\n\n'
                        case 'content':
                            yield f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": parsed["chunk"]})}\n\n'
                        case 'complete':
                            yield f'data: {json.dumps({"type": SSETypes.END.value, "content": ""})}\n\n'
    except Exception as e:
        logger.error(f'Error in {expert_type} external_streaming_llm: {e}')
        yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": "Unexpected error", "agent_name": expert_type})}\n\n'
