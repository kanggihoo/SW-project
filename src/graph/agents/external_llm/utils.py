import json
from typing import AsyncGenerator, Literal
import httpx
from model.type import SSETypes, ExternalLLMNames
from model.schema import StatusUpdate


async def external_streaming_llm(text:str , api_end_point:str, httpx_client , expert_type:Literal["color_expert" , "style_anal" , "fitting_coordinater"])->AsyncGenerator[str, None]:
    """특정 노드에서 외부 LLM 스트리밍 결과를 반환하는 비동기 제너레이터"""
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    payload = {
        "user_input": text,
        "room_id": 0,
        "expert_type": expert_type,
        "user_profile": {
            "additionalProp1": {}
        },
        "context_info": {
            "additionalProp1": {}
        },
        "json_data": {
            "additionalProp1": {}
        }
    }
    try:
        async with httpx_client.stream(
            "POST", 
            api_end_point, 
            headers=headers, 
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    data = line[6:]
                    parsed = json.loads(data)
                    match parsed["type"]:
                        case "status":
                            content = StatusUpdate(state="progress", content=parsed["message"] , task_id=expert_type).model_dump()
                            yield f"data: {json.dumps({'type': SSETypes.STATUS.value, 'content': content})}\n\n"
                        case "content":
                            yield f"data: {json.dumps({'type': SSETypes.TOKEN.value, 'content': parsed['chunk'] })}\n\n"
                        case "complete":
                            yield f"data: {json.dumps({'type': SSETypes.END.value, 'content': ""})}\n\n"
    except Exception as e:
        print(e)
        yield f"data: {json.dumps({'type': SSETypes.ERROR.value, 'content': 'Unexpected error' , 'agent_name': ExternalLLMNames.STYLE_ANALYST.value})}\n\n"
