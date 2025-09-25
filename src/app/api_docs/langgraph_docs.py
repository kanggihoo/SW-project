from typing import Any
import json
from fastapi import status
from graph.agents import get_all_agent_info
from graph.model.api_schema import ErrorResponse


AGENTS = get_all_agent_info()
def get_agents_openapi_examples() -> dict[str, Any]:
    result = {}
    for agent in AGENTS:
        result[agent] = {
            "summary": f"{agent} 에이전트",
            "value": agent,
        }
    return result

def sse_response_example() -> dict[str, Any]:
    """
    FastAPI 문서에 포함될 상세한 SSE 응답 예시를 생성합니다.
    
    이 함수는 프로젝트 워크플로우 문서에 기술된 모든 가능한 이벤트 타입(`status`, `token`, `message`, `error`, `[DONE]`)에 대한
    포괄적인 예시를 제공합니다.
    """
    # Example data for different SSE event types
    status_start_example = {
        "type": "status",
        "content": {
            "task_id": "color_expert",
            "state": "start",
            "content": "color_expert 의류 조합 분석 시작",
            "error_details": None,
        },
    }
    status_progress_example = {
        "type": "status",
        "content": {
            "task_id": "color_expert",
            "state": "progress",
            "content": "S3에서 착장 검색 중...",
            "error_details": None,
        },
    }
    status_end_example = {
        "type": "status",
        "content": {
            "task_id": "color_expert",
            "state": "end",
            "content": "color_expert 분석 완료",
            "error_details": None,
        },
    }
    
    token_example = {"type": "token", "content": "아"}
    
    message_example = {
        "type": "message",
        "content": {
            "type": "ai",
            "content": "아이보리 니트 폴로 셔츠에 화이트 와이드 슬랙스는 톤온톤 원리로 세련된 밝은 색상 조화를 이루고 있어...",
            "tool_calls": [],
            "tool_call_id": None,
            "run_id": "5c1a5d2a-9ca6-44fb-979a-49e8556f25da",
            "response_metadata": {},
            "additional_kwargs": {
                "type": "image",
                "created_at": "2025-09-23T06:59:52.279758+00:00",
                "image_urls": [
                    "https://sw-fashion-image-data.s3.amazonaws.com/color_expert/1.png",
                    "https://sw-fashion-image-data.s3.amazonaws.com/color_expert/2.png"
                ],
                "metadata": {
                    "expert_type": "color_expert"
                }
            },
            "custom_data": {}
        }
    }
    
    error_example = {"type": "error", "content": "오류가 발생했습니다."}
    end_example = {"type": "[DONE]", "content": ""}

    sse_stream_example = get_mock_sse_response()

    return {
        status.HTTP_200_OK: {
            "description": "성공적인 SSE 스트림 응답입니다. 스트림은 여러 이벤트 타입으로 구성되며, 각 이벤트는 'data: ' 접두사가 붙은 JSON 문자열 형식입니다. 스트림은 `[DONE]` 이벤트로 종료됩니다.",
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "examples": {
                        "전체 스트림": {
                            "summary": "전체 SSE 스트림에 대한 예시입니다.",
                            "description": "클라이언트가 수신하는 전체 SSE 스트림의 완전한 예시입니다. 여기에는 여러 에이전트의 상태 업데이트, 토큰 스트리밍, 최종 메시지 및 스트림 종료가 포함됩니다.",
                            "value": sse_stream_example,
                        },
                        "토큰 이벤트": {
                            "summary": "LLM 응답의 실시간 스트리밍을 위한 'token' 이벤트입니다.",
                            "description": "LLM이 생성하는 응답을 토큰 단위로 클라이언트에 실시간으로 전송할 때 사용됩니다. `content` 필드에는 응답의 일부인 문자열 조각이 포함됩니다. 클라이언트는 이 이벤트들을 순서대로 조합하여 전체 메시지를 구성할 수 있습니다.",
                            "value": f"data: {json.dumps(token_example)}\n\n",
                        },
                        "상태 이벤트": {
                            "summary": "백그라운드 작업의 진행 상태를 보고하기 위한 'status' 이벤트입니다.",
                            "description": "백그라운드에서 실행되는 작업(에이전트)의 현재 상태를 클라이언트에 알립니다. `content` 객체는 다음 필드를 포함합니다:\n- `task_id`: 상태를 보고하는 작업의 고유 식별자입니다 (예: 'color_expert', 'search').\n- `state`: 작업의 현재 상태를 나타내며, 'start'(시작), 'progress'(진행 중), 'end'(완료) 중 하나의 값을 가집니다.\n- `content`: 현재 상태에 대한 사람이 읽을 수 있는 설명입니다.\n- `error_details`: 작업 중 오류가 발생한 경우, 오류에 대한 상세 정보를 포함합니다. 성공 시에는 `null`입니다.",
                            "value": (
                                f"data: {json.dumps(status_start_example)}\n\n"
                                f"data: {json.dumps(status_progress_example)}\n\n"
                                f"data: {json.dumps(status_end_example)}\n\n"
                            ),
                        },
                        "메시지 이벤트": {
                            "summary": "최종 결과물인 구조화된 메시지를 전송하기 위한 'message' 이벤트입니다.",
                            "description": "하나의 에이전트 작업이 완료된 후, 완전하고 구조화된 최종 결과물을 클라이언트에 전달할 때 사용됩니다. `content`는 `ChatMessage` 객체이며 다음을 포함합니다:\n- `type`: 메시지 유형으로, 보통 'ai'입니다.\n- `content`: AI가 생성한 최종 텍스트 응답입니다.\n- `additional_kwargs`: 추가적인 메타데이터를 포함하는 객체입니다.\n  - `created_at`: 메시지 생성 타임스탬프입니다.\n  - `image_urls`: 응답과 관련된 이미지 URL 리스트입니다.\n  - `metadata`: 응답을 생성한 전문가의 유형(`expert_type`)과 같은 추가 정보가 포함됩니다 (예: 'style_analyst', 'color_expert').",
                            "value": f"data: {json.dumps(message_example)}\n\n",
                        },
                        "종료 이벤트": {
                            "summary": "SSE 스트림의 끝을 알리는 '[DONE]' 이벤트입니다.",
                            "description": "모든 데이터 전송이 완료되었음을 클라이언트에 알리는 특별한 이벤트입니다. 이 이벤트를 수신하면 클라이언트는 스트림 연결을 안전하게 종료할 수 있습니다. `content` 필드는 비어 있습니다.",
                            "value": f"data: {json.dumps(end_example)}\n\n",
                        },
                    },
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR:
            {
                "description": "스트림 중 문제가 발생했을 때 전송되는 에러 이벤트입니다.",
                "content": {
                    "text/event-stream": {
                        "schema": {"type": "string"},
                        "example": f"data: {json.dumps(error_example)}\n\n",
                    }
                },
            },
    }


ERROR_RESPONSES = {
    500: {
        "description": "서버 내부 오류가 발생했습니다",
        "model": ErrorResponse
    }
}


def get_mock_sse_response() -> str:
    return '''data: {"type": "status", "content": {"task_id": "color_expert", "state": "start", "content": "color_expert 의류 조합 분석 시작", "error_details": null}}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "S3 매칭 성공: 11개 착장 발견", "error_details": null}}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "최종 착장 선택: aef3dbacc1076182e6e733fd3563f463", "error_details": null}}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "전문가 분석 시작...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "Claude API 호출 중...", "error_details": null}}

data: {"type": "token", "content": "네이"}

data: {"type": "token", "content": "비 베이직"}

data: {"type": "token", "content": " 반팔 "}

data: {"type": "token", "content": "셔츠에"}

data: {"type": "token", "content": "밸런스를 완"}

data: {"type": "token", "content": "성할 수 있어"}

data: {"type": "token", "content": "."}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "전문가 분석 완료", "error_details": null}}

data: {"type": "status", "content": {"task_id": "color_expert", "state": "end", "content": "color_expert 분석 완료", "error_details": null}}

data: {"type": "status", "content": {"task_id": "search", "state": "start", "content": "이미지 검색 시작", "error_details": null}}

data: {"type": "status", "content": {"task_id": "search", "state": "end", "content": "이미지 검색 완료!", "error_details": null}}

data: {"type": "message", "content": {"type": "ai", "content": "네이비 베이직 반팔 셔츠에 아이보리 와이드 슬랙스가 잘 어울려! 네이비와 아이보리는 명도 대비를 통해 세련된 균형감을 만들어내고, 차가운 네이비와 따뜻한 아이보리의 색상 온도 대비로 시각적 긴장감을 형성해. 블랙 로퍼와 블랙 가방으로 포인트를 더하면서 전체적인 색상 밸런스를 완성할 수 있어.", "tool_calls": [], "tool_call_id": null, "additional_kwargs": {"type": "image", "created_at": "2025-09-25T08:51:48.710757+00:00", "expert_type": "color_expert", "product_ids": ["3858441_블루", "4109513_화이트"]}}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "start", "content": "style_analyst 의류 조합 분석 시작", "error_details": null}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "S3 매칭 성공: 11개 착장 발견", "error_details": null}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "최종 착장 선택: 184e375ed44293d5e73b630d4476ad92", "error_details": null}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "전문가 분석 시작...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "Claude API 호출 중...", "error_details": null}}

data: {"type": "token", "content": "화"}

data: {"type": "token", "content": "이트 셔"}

data: {"type": "token", "content": "츠에 블랙 "}

data: {"type": "token", "content": "색없을 만"}

data: {"type": "token", "content": "한 스타일이"}

data: {"type": "token", "content": "야."}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "전문가 분석 완료", "error_details": null}}

data: {"type": "status", "content": {"task_id": "style_analyst", "state": "end", "content": "style_analyst 분석 완료", "error_details": null}}

data: {"type": "status", "content": {"task_id": "search", "state": "start", "content": "이미지 검색 시작", "error_details": null}}

data: {"type": "status", "content": {"task_id": "search", "state": "end", "content": "이미지 검색 완료!", "error_details": null}}

data: {"type": "message", "content": {"type": "ai", "content": "화이트 셔츠에 블랙 와이드 슬랙스가 잘 어울려. 데이트 분위기에 맞게 소매는 자연스럽게 내리고 셔츠 단추 위쪽 1-2개만 살짝 풀어주는 게 좋아. 셔츠는 전체적으로 바지 안에 넣어서 깔끔한 실루엣을 만들면서, 블랙 벨트로 허리선을 살짝 강조해봐. 블랙 클래식 로퍼랑 매치하면 세련된 데이트룩이 완성될 거야. 캐주얼하면서도 포멀한 느낌이 적절히 섞여서 특별한 날에도 손색없을 만한 스타일이야.", "tool_calls": [], "tool_call_id": null, "additional_kwargs": {"type": "image", "created_at": "2025-09-25T08:51:57.832308+00:00", "expert_type": "style_analyst", "product_ids": ["2171532_화이트", "2503135_블랙"]}}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "start", "content": "fitting_coordinator 의류 조합 분석 시작", "error_details": null}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "S3 매칭 성공: 11개 착장 발견", "error_details": null}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "최종 착장 선택: c96192fc7e225468fbd88137717364ea", "error_details": null}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "전문가 분석 시작...", "error_details": null}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "Claude API 호출 중...", "error_details": null}}

data: {"type": "token", "content": "베"}

data: {"type": "token", "content": "이지 오버"}

data: {"type": "token", "content": "인을 더 "}

data: {"type": "token", "content": "길어보이게"}

data: {"type": "token", "content": " 만들어"}

data: {"type": "token", "content": "줘."}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "전문가 분석 완료", "error_details": null}}

data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "end", "content": "fitting_coordinator 분석 완료", "error_details": null}}

data: {"type": "status", "content": {"task_id": "search", "state": "start", "content": "이미지 검색 시작", "error_details": null}}

data: {"type": "status", "content": {"task_id": "search", "state": "end", "content": "이미지 검색 완료!", "error_details": null}}

data: {"type": "message", "content": {"type": "ai", "content": "베이지 오버핏 반팔 셔츠에 블랙 와이드 슬랙스가 잘 어울려. 여유있는 실루엣으로 편안하면서도 세련된 데이트룩을 완성할 수 있어. 셔츠 앞부분만 살짝 넣어서 자연스러운 캐주얼함을 더하고, 위쪽 단추 1-2개 풀어주면 더 멋스러워. 블랙 옥스포드 슈즈로 포멀함을 더하고, 브라운 가죽 서류가방으로 포인트를 줘서 센스있는 데이트 스타일을 연출할 수 있어. 면 소재라 여름에도 시원하게 입을 수 있고, 슬랙스의 와이드한 실루엣이 다리라인을 더 길어보이게 만들어줘.", "tool_calls": [], "tool_call_id": null, "additional_kwargs": {"type": "image", "created_at": "2025-09-25T08:52:07.677316+00:00", "expert_type": "fitting_coordinator", "product_ids": ["4227290_베이지", "2503135_블랙"]}}}

data: {"type": "[DONE]", "content": ""}
'''
