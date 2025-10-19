# ruff: noqa: E501
import asyncio
import json

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from loguru import logger

from graph.common.state import State
from graph.constants import SSETypes
from graph.model.api_schema import StatusUpdate

MOCK_DATA_COLOR_EXPERT = [
    'data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "color_expert", "state": "progress", "content": "S3 매칭 성공: 8개 착장 발견", "error_details": null}}\n\n',
    'data: {"type": "token", "content":"블"}\n\n',
    'data: {"type": "token", "content":"루 "}\n\n',
    'data: {"type": "token", "content":"셔츠에"}\n\n',
    'data: {"type": "token", "content":" 네"}\n\n',
    'data: {"type": "token", "content":"이비 베"}\n\n',
    'data: {"type": "token", "content":"스트와"}\n\n',
    'data: {"type": "token", "content":" 그"}\n\n',
    'data: {"type": "token", "content":"레이 와"}\n\n',
    'data: {"type": "token", "content":"이드 슬"}\n\n',
    'data: {"type": "token", "content":"랙스는"}\n\n',
    'data: {"type": "token", "content":"톤온톤 "}\n\n',
    'data: {"type": "token", "content":"원"}\n\n',
    'data: {"type": "token", "content":"리"}\n\n',
    'data: {"type": "token", "content":"로"}\n\n',
    'data: {"type": "token", "content":" 세"}\n\n',
    'data: {"type": "token", "content":"련된 색"}\n\n',
    'data: {"type": "token", "content":"상"}\n\n',
    'data: {"type": "token", "content":" 조화"}\n\n',
    'data: {"type": "token", "content":"를 이루고"}\n\n',
    'data: {"type": "token", "content":" 있어"}\n\n',
    'data: {"type": "token", "content":"."}\n\n',
    'data: {"type": "token", "content":" 차"}\n\n',
    'data: {"type": "token", "content":"가"}\n\n',
    'data: {"type": "token", "content":"운 계"}\n\n',
    'data: {"type": "token", "content":"열의 블루"}\n\n',
    'data: {"type": "token", "content":"와 네"}\n\n',
    'data: {"type": "token", "content":"이비의 레"}\n\n',
    'data: {"type": "token", "content":"이어드는"}\n\n',
    'data: {"type": "token", "content":" 명"}\n\n',
    'data: {"type": "token", "content":"도 대비를"}\n\n',
    'data: {"type": "token", "content":" 통해 "}\n\n',
    'data: {"type": "token", "content":"깊이감"}\n\n',
    'data: {"type": "token", "content":"을 만"}\n\n',
    'data: {"type": "token", "content":"들어내."}\n\n',
    'data: {"type": "token", "content":" 화이트 "}\n\n',
    'data: {"type": "token", "content":"셔츠의"}\n\n',
    'data: {"type": "token", "content":" 포"}\n\n',
    'data: {"type": "token", "content":"인트와"}\n\n',
    'data: {"type": "token", "content":" 블랙 "}\n\n',
    'data: {"type": "token", "content":"로퍼의"}\n\n',
    'data: {"type": "token", "content":" 마"}\n\n',
    'data: {"type": "token", "content":"무리로"}\n\n',
    'data: {"type": "token", "content":" 전"}\n\n',
    'data: {"type": "token", "content":"체적인 색"}\n\n',
    'data: {"type": "token", "content":"상"}\n\n',
    'data: {"type": "token", "content":"밸런스가"}\n\n',
    'data: {"type": "token", "content":" 안"}\n\n',
    'data: {"type": "token", "content":"정적"}\n\n',
    'data: {"type": "token", "content":"으"}\n\n',
    'data: {"type": "token", "content":"로 구"}\n\n',
    'data: {"type": "token", "content":"성되어 있"}\n\n',
    'data: {"type": "token", "content":"어."}\n\n',
    'data: {"type": "[DONE]", "content": ""}\n\n',
]

MOCK_DATA_STYLE_ANALYST = [
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "S3 매칭 성공: 5개 착장 발견", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "최종 착장 선택: 056449ada2366d2f8f8266a3f69c923e", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "전문가 분석 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "style_analyst", "state": "progress", "content": "Claude API 호출 중...", "error_details": null}}\n\n',
    'data: {"type": "token", "content":"화"}\n\n',
    'data: {"type": "token", "content":"이트 버"}\n\n',
    'data: {"type": "token", "content":"튼다운 "}\n\n',
    'data: {"type": "token", "content":"반팔 "}\n\n',
    'data: {"type": "token", "content":"셔츠에"}\n\n',
    'data: {"type": "token", "content":" 블랙 "}\n\n',
    'data: {"type": "token", "content":"핀스트라"}\n\n',
    'data: {"type": "token", "content":"이프 슬"}\n\n',
    'data: {"type": "token", "content":"랙스가"}\n\n',
    'data: {"type": "token", "content":" 잘 어"}\n\n',
    'data: {"type": "token", "content":"울려. "}\n\n',
    'data: {"type": "token", "content":"셔츠 "}\n\n',
    'data: {"type": "token", "content":"앞부분만"}\n\n',
    'data: {"type": "token", "content":" 살짝 "}\n\n',
    'data: {"type": "token", "content":"넣어서"}\n\n',
    'data: {"type": "token", "content":" 캐주"}\n\n',
    'data: {"type": "token", "content":"얼하면서도"}\n\n',
    'data: {"type": "token", "content":" 세련된 "}\n\n',
    'data: {"type": "token", "content":"데"}\n\n',
    'data: {"type": "token", "content":"이트"}\n\n',
    'data: {"type": "token", "content":"룩을 완"}\n\n',
    'data: {"type": "token", "content":"성할"}\n\n',
    'data: {"type": "token", "content":" 수 있어"}\n\n',
    'data: {"type": "token", "content":"."}\n\n',
    'data: {"type": "token", "content":" 브"}\n\n',
    'data: {"type": "token", "content":"라운 "}\n\n',
    'data: {"type": "token", "content":"옥스포드 "}\n\n',
    'data: {"type": "token", "content":"슈즈로"}\n\n',
    'data: {"type": "token", "content":" 포멀한"}\n\n',
    'data: {"type": "token", "content":" 느"}\n\n',
    'data: {"type": "token", "content":"낌을 더"}\n\n',
    'data: {"type": "token", "content":"하"}\n\n',
    'data: {"type": "token", "content":"고"}\n\n',
    'data: {"type": "token", "content":" 실"}\n\n',
    'data: {"type": "token", "content":"버 가죽"}\n\n',
    'data: {"type": "token", "content":" 시계로 "}\n\n',
    'data: {"type": "token", "content":"포"}\n\n',
    'data: {"type": "token", "content":"인트를 "}\n\n',
    'data: {"type": "token", "content":"줘"}\n\n',
    'data: {"type": "token", "content":"." "}\n\n',
    'data: {"type": "token", "content":"셔츠 버"}\n\n',
    'data: {"type": "token", "content":"튼 "}\n\n',
    'data: {"type": "token", "content":"1"}\n\n',
    'data: {"type": "token", "content":"-2개 "}\n\n',
    'data: {"type": "token", "content":"풀어서"}\n\n',
    'data: {"type": "token", "content":" 답"}\n\n',
    'data: {"type": "token", "content":"답해"}\n\n',
    'data: {"type": "token", "content":"보이지 않"}\n\n',
    'data: {"type": "token", "content":"게 연"}\n\n',
    'data: {"type": "token", "content":"출하면 "}\n\n',
    'data: {"type": "token", "content":"돼."}\n\n',
    'data: {"type": "[DONE]", "content": ""}\n\n',
]

MOCK_DATA_FITTING_COORDINATOR = [
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "착장 매칭 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "S3에서 착장 검색 중...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "S3 매칭 성공: 15개 착장 발견", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "최종 착장 선택: 561a7db1f64f00f80a2160216c855d8f", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "전문가 분석 시작...", "error_details": null}}\n\n',
    'data: {"type": "status", "content": {"task_id": "fitting_coordinator", "state": "progress", "content": "Claude API 호출 중...", "error_details": null}}\n\n',
    'data: {"type": "token", "content": "베"}\n\n',
    'data: {"type": "token", "content": "이지 오버"}\n\n',
    'data: {"type": "token", "content": "핏 반"}\n\n',
    'data: {"type": "token", "content": "팔 셔"}\n\n',
    'data: {"type": "token", "content": "츠에 블"}\n\n',
    'data: {"type": "token", "content": "랙 와이드"}\n\n',
    'data: {"type": "token", "content": "슬랙"}\n\n',
    'data: {"type": "token", "content": "스가"}\n\n',
    'data: {"type": "token", "content": "잘 어"}\n\n',
    'data: {"type": "token", "content": "울려"}\n\n',
    'data: {"type": "token", "content": ". 면"}\n\n',
    'data: {"type": "token", "content": "소재의 "}\n\n',
    'data: {"type": "token", "content": "여"}\n\n',
    'data: {"type": "token", "content": "유로"}\n\n',
    'data: {"type": "token", "content": "운 "}\n\n',
    'data: {"type": "token", "content": "셔츠 "}\n\n',
    'data: {"type": "token", "content": "실"}\n\n',
    'data: {"type": "token", "content": "루엣에"}\n\n',
    'data: {"type": "token", "content": "깔끔한"}\n\n',
    'data: {"type": "token", "content": "블랙 "}\n\n',
    'data: {"type": "token", "content": "슬랙스"}\n\n',
    'data: {"type": "token", "content": "로"}\n\n',
    'data: {"type": "token", "content": "세"}\n\n',
    'data: {"type": "token", "content": "련된 데"}\n\n',
    'data: {"type": "token", "content": "이트"}\n\n',
    'data: {"type": "token", "content": "룩이"}\n\n',
    'data: {"type": "token", "content": "완성될"}\n\n',
    'data: {"type": "token", "content": "거"}\n\n',
    'data: {"type": "token", "content": "야"}\n\n',
    'data: {"type": "token", "content": ". "}\n\n',
    'data: {"type": "token", "content": "셔츠 "}\n\n',
    'data: {"type": "token", "content": "앞부분만"}\n\n',
    'data: {"type": "token", "content": "살짝 "}\n\n',
    'data: {"type": "token", "content": "넣어서"}\n\n',
    'data: {"type": "token", "content": "자"}\n\n',
    'data: {"type": "token", "content": "연스러운 "}\n\n',
    'data: {"type": "token", "content": "느"}\n\n',
    'data: {"type": "token", "content": "낌을 주"}\n\n',
    'data: {"type": "token", "content": "고, 위"}\n\n',
    'data: {"type": "token", "content": "쪽 버"}\n\n',
    'data: {"type": "token", "content": "튼 "}\n\n',
    'data: {"type": "token", "content": "1-2개 "}\n\n',
    'data: {"type": "token", "content": "정"}\n\n',
    'data: {"type": "token", "content": "도는"}\n\n',
    'data: {"type": "token", "content": "풀어두는"}\n\n',
    'data: {"type": "token", "content": "게"}\n\n',
    'data: {"type": "token", "content": "좋아."}\n\n',
    'data: {"type": "token", "content": "블"}\n\n',
    'data: {"type": "token", "content": "랙 옥"}\n\n',
    'data: {"type": "token", "content": "스포드 "}\n\n',
    'data: {"type": "token", "content": "슈즈로"}\n\n',
    'data: {"type": "token", "content": "포멀함"}\n\n',
    'data: {"type": "token", "content": "을 더하고"}\n\n',
    'data: {"type": "token", "content": "브"}\n\n',
    'data: {"type": "token", "content": "라운 가"}\n\n',
    'data: {"type": "token", "content": "죽 서류가"}\n\n',
    'data: {"type": "token", "content": "방으"}\n\n',
    'data: {"type": "token", "content": "로 포"}\n\n',
    'data: {"type": "token", "content": "인트를 더하고"}\n\n',
    'data: {"type": "token", "content": "줘"}\n\n',
    'data: {"type": "token", "content": "서"}\n\n',
    'data: {"type": "token", "content": "세련된 "}\n\n',
    'data: {"type": "token", "content": "분"}\n\n',
    'data: {"type": "token", "content": "위기를 연"}\n\n',
    'data: {"type": "token", "content": "출할"}\n\n',
    'data: {"type": "token", "content": "수 있어"}\n\n',
    'data: {"type": "token", "content": ". 여"}\n\n',
    'data: {"type": "token", "content": "유로"}\n\n',
    'data: {"type": "token", "content": "운 실"}\n\n',
    'data: {"type": "token", "content": "루엣이"}\n\n',
    'data: {"type": "token", "content": "지만 전체"}\n\n',
    'data: {"type": "token", "content": "적으로 균"}\n\n',
    'data: {"type": "token", "content": "형 "}\n\n',
    'data: {"type": "token", "content": "잡힌 "}\n\n',
    'data: {"type": "token", "content": "비율이"}\n\n',
    'data: {"type": "token", "content": "라"}\n\n',
    'data: {"type": "token", "content": "데이트 "}\n\n',
    'data: {"type": "token", "content": "장"}\n\n',
    'data: {"type": "token", "content": "소 "}\n\n',
    'data: {"type": "token", "content": "어디든"}\n\n',
    'data: {"type": "token", "content": "잘 어울"}\n\n',
    'data: {"type": "token", "content": "릴 거야."}\n\n',
    'data: {"type": "[DONE]", "content": ""}\n\n',
]


async def mock_external_streaming_llm(expert_type: str):
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


async def mock_external_llm_node(state: State, config: RunnableConfig) -> dict:
    """외부 LLM 스트리밍 결과를 반환하는 노드 - 사용자 입력을 분석하여 검색 쿼리 생성"""

    text = state['user_message']  # noqa: F841
    current_expert = state.get('current_expert')
    writer = get_stream_writer()
    response_text = ''

    content = StatusUpdate(state='start', content=f'{current_expert} 의류 조합 분석 시작', task_id=current_expert).model_dump()
    writer({'type': SSETypes.STATUS.value, 'content': content})

    try:
        async for chunk in mock_external_streaming_llm(expert_type=current_expert):
            chunk = chunk.strip()
            if chunk.startswith('data: '):
                data = chunk[6:]
                parsed = json.loads(data)
                # logger.info(f'parsed: {parsed}')
                match parsed['type']:
                    case SSETypes.TOKEN:
                        response_text += parsed['content']
                        writer({'type': SSETypes.TOKEN, 'content': parsed['content']})
                    case SSETypes.STATUS:
                        writer({'type': SSETypes.STATUS, 'content': parsed['content']})
                    case SSETypes.END:
                        content = StatusUpdate(
                            state='end',
                            content=f'{current_expert} 분석 완료',
                            task_id=current_expert,
                        ).model_dump()
                        writer({'type': SSETypes.STATUS, 'content': content})
                        break
    except Exception as e:
        logger.error(f'Error in external external_llm_node : {e}')
        response_text = '의류 분석 중 오류가 발생했습니다.'
        content = StatusUpdate(
            state='error',
            content=f'{current_expert} 분석 오류',
            task_id=current_expert,
            error_details=str(e),
        ).model_dump()
        writer({'type': SSETypes.STATUS.value, 'content': content})

    return {'expert_opinions': response_text}
