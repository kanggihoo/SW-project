# Separated nodes from llm_search.py and external_llm.py
import json

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from loguru import logger

from db.services.search import SearchService
from graph.common.state import State
from graph.common.utils import external_streaming_llm
from graph.model.api_schema import StatusUpdate
from graph.model.constants import SSETypes
from graph.utils.messages import create_message


async def pop_next_expert_node(state: State, config: RunnableConfig) -> dict:
    """전문가 리스트에서 다음 전문가를 꺼내 'current_expert'로 설정"""
    logger.debug('\n--- 노드 실행: pop_next_expert_node ---')
    experts_to_run = state['experts_to_run']
    logger.debug(f'experts_to_run: {experts_to_run}')
    current_expert = experts_to_run.pop(0)
    logger.debug(f'  (이번 전문가: {current_expert})')
    return {'current_expert': current_expert, 'experts_to_run': experts_to_run}


async def external_llm_node(state: State, config: RunnableConfig) -> dict:
    """외부 LLM 스트리밍 결과를 반환하는 노드 - 사용자 입력을 분석하여 검색 쿼리 생성"""
    host = 'https://the-first-take.com'
    path = 'llm/api/expert/single/stream'
    api_endpoint = f'{host}/{path}'

    text = state['user_message']
    current_expert = state.get('current_expert')
    writer = get_stream_writer()
    response_text = ''

    content = StatusUpdate(state='start', content=f'{current_expert} 의류 조합 분석 시작', task_id=current_expert).model_dump()
    writer({'type': SSETypes.STATUS.value, 'content': content})

    try:
        async for chunk in external_streaming_llm(
            text,
            api_endpoint,
            http_session=config['configurable']['http_session'],
            expert_type=current_expert,
        ):
            chunk = chunk.strip()
            if chunk.startswith('data: '):
                data = chunk[6:]
                parsed = json.loads(data)
                # logger.info(f'parsed: {parsed}')
                match parsed['type']:
                    case SSETypes.TOKEN.value:
                        response_text += parsed['content']
                        writer({'type': SSETypes.TOKEN.value, 'content': parsed['content']})
                    case SSETypes.STATUS.value:
                        writer({'type': SSETypes.STATUS.value, 'content': parsed['content']})
                    case SSETypes.END.value:
                        content = StatusUpdate(
                            state='end',
                            content=f'{current_expert} 분석 완료',
                            task_id=current_expert,
                        ).model_dump()
                        writer({'type': SSETypes.STATUS.value, 'content': content})
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


async def search_node(state: State, config: RunnableConfig) -> dict:
    """외부 LLM 결과를 기반으로 벡터 검색을 수행하는 노드"""
    writer = get_stream_writer()
    writer(
        {
            'type': SSETypes.STATUS.value,
            'content': StatusUpdate(state='start', content='이미지 검색 시작', task_id='search').model_dump(),
        }
    )

    expert_opinions = state['expert_opinions']
    current_expert = state['current_expert']
    search_service: SearchService = config['configurable']['search_service']
    try:
        # TODO : 반환된 값에 대한 리랭킹 필요
        search_result = await search_service.search_by_query(expert_opinions, limit=1)

        writer(
            {
                'type': SSETypes.STATUS.value,
                'content': StatusUpdate(state='end', content='이미지 검색 완료!', task_id='search').model_dump(),
            }
        )

        product_ids = []
        if search_result and 'data' in search_result:
            for item in search_result['data']:
                product_ids.append(item.get('product_id').strip())
                # url = search_service._generate_s3_url(item)
                # if url:

        metadata = {'type': 'refer', 'expert_type': current_expert, 'product_ids': product_ids}

        search_result_message = create_message(message_type='ai', content=expert_opinions, metadata=metadata)
        return {'messages': [search_result_message]}

    except Exception as e:
        logger.error(f'Error in search node: {e}')
        writer(
            {
                'type': SSETypes.STATUS.value,
                'content': StatusUpdate(
                    state='error',
                    content='이미지 검색 오류',
                    task_id='search',
                    error_details=str(e),
                ).model_dump(),
            }
        )

        error_message = create_message(message_type='ai', content='이미지 검색 중 오류가 발생했습니다.')

        return {'messages': [error_message]}


async def call_external_llm_node(state: State, config: RunnableConfig):
    """외부 LLM 스트리밍 결과를 반환하는 노드"""
    text = state['messages'][-1].content
    writer = get_stream_writer()
    response_text = ''
    # TODO : 각 전문가 연결
    # color_expert, fitting_coordinater, style_anal
    external_agent_name = state['current_expert']

    content = StatusUpdate(
        state='start',
        content=f'{external_agent_name} 의류 조합 분석 시작',
        task_id=external_agent_name,
    ).model_dump()
    writer({'type': SSETypes.STATUS.value, 'content': content})
    logger.info(f'config: {config}')

    async for chunk in external_streaming_llm(
        text,
        api_endpoint=config['configurable']['api_endpoint'],
        http_session=config['configurable']['http_session'],
        expert_type=external_agent_name,
    ):
        chunk = chunk.strip()
        if chunk.startswith('data: '):
            data = chunk[6:]
            parsed = json.loads(data)
            match parsed['type']:
                case SSETypes.TOKEN.value:
                    response_text += parsed['content']
                    writer({'type': SSETypes.TOKEN.value, 'content': parsed['content']})
                case SSETypes.STATUS.value:
                    writer({'type': SSETypes.STATUS.value, 'content': parsed['content']})
                case SSETypes.END.value:
                    content = StatusUpdate(
                        state='end',
                        content=f'{external_agent_name} 분석 완료',
                        task_id=external_agent_name,
                    ).model_dump()
                    writer({'type': SSETypes.STATUS.value, 'content': content})

    return {
        'messages': [create_message(message_type='ai', content=response_text)],
        'metadata': 'external_llm_response',
    }
