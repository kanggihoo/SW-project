# Separated nodes from llm_search.py and external_llm.py
import json

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from loguru import logger

from db.services.search import SearchService
from graph.common.state import State
from graph.common.utils import external_streaming_llm
from graph.model.api_schema import StatusUpdate
from graph.model.constants import SSETypes
from graph.prompt.chatbot import chatbot_prompt
from graph.utils.messages import create_message
from llm import get_llm_model


async def chatbot(state: State, config: RunnableConfig) -> dict:
    chain = chatbot_prompt | get_llm_model(config.get('configurable', {}).get('model', 'google/gemini-2.0-flash-lite'))
    response = await chain.ainvoke({'messages': state['messages']})
    response = create_message(message_type='ai', content=response.content)
    return {'messages': [response]}


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
            http_session=config.get('configurable', {}).get('http_session'),
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
        logger.error(f'Error in external external_llm_node : {e}', exc_info=True)
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
    search_service: SearchService = config.get('configurable', {}).get('search_service', '')
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
        else:
            raise ValueError(f'Search result is empty | search_result: {search_result}')
        metadata = {'type': 'refer', 'expert_type': current_expert, 'product_ids': product_ids}

        search_result_message = create_message(message_type='ai', content=expert_opinions, metadata=metadata)
        return {'messages': [search_result_message]}

    except Exception as e:
        logger.error(f'Error in search node: {e}', exc_info=True)
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
    logger.info(f'config in call_external_llm_node: {config}')
    api_endpoint = config.get('configurable', {}).get('api_endpoint')
    if api_endpoint is None:
        raise ValueError('api_endpoint is required')

    http_session = config.get('configurable', {}).get('http_session')
    if http_session is None:
        raise ValueError('http_session is required')

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

    async for chunk in external_streaming_llm(
        text,
        api_endpoint=api_endpoint,
        http_session=http_session,
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


# product_info_agent = create_react_agent(
#     model=model,
#     tools=[product_info],
#     prompt='You are a product info agent. You are given a product name and you need to fetch the product information.',
#     name=NodeName.PRODUCT_INFO_AGENT,
# )


def handle_inappropriate_node(state: State):
    """부적절한 질문 처리 노드"""
    print('\n--- 노드 실행: handle_inappropriate_node ---')
    canned_response = '죄송합니다. 해당 질문에는 답변해 드릴 수 없습니다. 의류 추천과 관련하여 도움이 필요하시면 말씀해주세요.'
    return {'messages': [AIMessage(content=canned_response)]}


def chatbot_node(state: State):
    """일상 대화 처리 노드 (플레이스홀더)"""
    print('\n--- 노드 실행: chatbot_node ---')
    # 실제 구현 시에는 대화의 맥락을 유지하며 자연스럽게 의류 추천으로 유도하는 로직 추가
    return {'messages': [AIMessage(content='네, 안녕하세요! 어떤 옷을 찾아드릴까요?')]}


def info_qa_node(state: State):
    """정보 질문 처리 노드 (플레이스홀더)"""
    print('\n--- 노드 실행: info_qa_node ---')
    # 실제 구현 시에는 웹 검색 등의 도구를 사용하여 전문적인 답변 제공
    return {'messages': [AIMessage(content='패션에 대해 궁금한 점이 있으시군요! 무엇이든 물어보세요.')]}


def test_search_node(state: State):
    """최종 검색 실행 노드"""
    print('\n--- 노드 실행: search_node ---')
    search_info = state['cloth_search']
    search_result_message = f'검색을 시작합니다: {search_info.model_dump_json(indent=2)}'
    print(search_result_message)
    return {'messages': [AIMessage(content=search_result_message)]}
