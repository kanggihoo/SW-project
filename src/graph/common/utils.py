import json
from collections.abc import AsyncGenerator
from typing import Literal

from loguru import logger

from graph.constants import SSETypes
from graph.model.api_schema import StatusUpdate


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
                            yield f'data: {json.dumps({"type": SSETypes.STATUS, "content": content})}\n\n'
                        case 'content':
                            yield f'data: {json.dumps({"type": SSETypes.TOKEN, "content": parsed["chunk"]})}\n\n'
                        case 'complete':
                            yield f'data: {json.dumps({"type": SSETypes.END, "content": ""})}\n\n'
    except Exception as e:
        logger.error(f'Error in {expert_type} external_streaming_llm: {e}')
        yield f'data: {json.dumps({"type": SSETypes.ERROR, "content": "Unexpected error", "agent_name": expert_type})}\n\n'


# TODO : 여기는
# def is_cache_cyclable(state: State) -> bool:
#     """
#     순환할 모든 전문가가 각자 '중복되지 않는' 다음 상품을 가지고 있는지 확인합니다.
#     하나의 전문가라도 보여줄 고유 상품이 없으면 즉시 False를 반환합니다.
#     """
#     expert_cache = state.get(StateName.EXPERT_SEARCH_CACHE, {})
#     expert_offsets = state.get(StateName.EXPERT_OFFSETS, {})
#     shown_ids = state.get("shown_in_product_ids", {})

#     # 'shown_in_current_cycle'은 route_search_logic에서 초기화되므로 여기서는 사용하지 않음
#     # 대신, 전체적으로 남은 아이템이 있는지 순회하며 확인

#     expert_names_with_cache = list(expert_cache.keys())
#     planned_items = set()

#     for expert_name in expert_names_with_cache:
#         cached_results = expert_cache.get(expert_name, [])
#         found_unique_product= False

#         while expert_offsets[expert_name] < len(cached_results):
#             item = cached_results[expert_offsets[expert_name]]
#             product_id = item['product_id']

#             if product_id not in shown_ids and product_id not in planned_items:
#                 found_unique_product = True
#                 planned_items.add(product_id)
#                 break
#             expert_offsets[expert_name] += 1

#         if not found_unique_product:
#             return False
#     return True
