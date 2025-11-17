# ruff : noqa: E501
import asyncio
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse
from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from app.api_docs import ERROR_RESPONSES, get_mock_sse_response, sse_response_example
from app.config.dependencies import AgentDep, DBConnectionDep, HTTPClientDep, SearchServiceDep, get_agents
from graph.builders import DEFAULT_AGENT_NAME, get_all_agent_info
from graph.model.api_schema import (
    ChatHistory,
    ChatMessage,
    DeleteHistoryResponse,
    ServiceMetadata,
    StreamInput,
)
from graph.settings import settings
from graph.utils import langchain_to_chat_message, message_generator

router = APIRouter(tags=['langgraph'])

# Reusable error response for API documentation


@router.get('/info', summary='사용가능한 llm 모델 및 에이전트 정보 조회')
async def get_info() -> ServiceMetadata:
    try:
        models = settings.AVAILABLE_LLM_MODELS
        return ServiceMetadata(
            agents=get_all_agent_info(),
            models=list(models),
            default_model=settings.DEFAULT_LLM_MODEL,
            default_agent=DEFAULT_AGENT_NAME,
        )
    except Exception as e:
        logger.error(f'Error getting info: {e}')
        raise e


# @router.post('/{agent_name}/invoke', summary='에이전트 호출 스트리밍X', deprecated=True)
# async def invoke(
#     user_input: UserInput,
#     agent: AgentDep,
# ) -> ChatMessage:
#     """
#     지정된 에이전트를 사용자 입력으로 호출하고 응답을 반환합니다.
#     """
#     # agent:CompiledStateGraph = get_agent(agent_name)
#     kwargs, run_id = await handle_user_input(user_input, agent)

#     try:
#         response_events: list[tuple[str, Any]] = await agent.ainvoke(**kwargs, stream_mode=["updates", "values"])  # type: ignore # fmt: skip
#         response_type, response = response_events[-1]
#         if response_type == 'values':
#             # Normal response, the agent completed successfully
#             output = langchain_to_chat_message(response['messages'][-1])  # 맨 마지막 message에 대해서 변환
#         elif response_type == 'updates' and '__interrupt__' in response:
#             # The last thing to occur was an interrupt
#             # Return the value of the first interrupt as an AIMessage
#             output = langchain_to_chat_message(AIMessage(content=response['__interrupt__'][0].value))
#         else:
#             raise ValueError(f'Unexpected response type: {response_type}')

#         output.run_id = str(run_id)
#         return output
#     except Exception as e:
#         logger.error(f'An exception occurred: {e}')
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error') from e


@router.post(
    '/{agent_name}/stream',
    summary='에이전트 호출 및 응답 스트리밍',
    response_class=StreamingResponse,
    responses=sse_response_example(),
)
async def stream(
    user_input: StreamInput,
    agent: AgentDep,
    http_session: HTTPClientDep,
    search_service: SearchServiceDep,
) -> StreamingResponse:
    """
    **지정된 에이전트를 사용자 입력으로 호출하고 Server-Sent Events (SSE)를 사용하여 응답을 스트리밍합니다.**
    SSE 스트림은 챗봇과 같은 애플리케이션에 적합한 실시간 서버 통신을 가능하게 합니다. 스트림은 여러 이벤트 유형으로 구성됩니다:

    - `status`: 에이전트의 내부 상태에 대한 업데이트를 제공합니다 (예: 'tool 시작', '처리 중...'). `content` 필드에는 `StatusUpdate` 객체가 포함됩니다.
    - `token`: 실시간 타이핑 효과를 위해 LLM의 응답을 토큰 단위로 스트리밍합니다. `content`는 문자열 청크입니다.
    - `message`: 에이전트의 턴이 끝나면 최종적이고 완전한 메시지 객체(`ChatMessage`)를 전달합니다. 여기에는 이미지 URL과 같은 구조화된 데이터가 포함될 수 있습니다.
    - `error`: 처리 중 오류가 발생했음을 알립니다. `content`에는 오류 메시지가 포함됩니다.
    - `[DONE]`: 스트림의 끝을 표시하는 특별한 이벤트입니다.

    각 이벤트는 `data: ` 접두사가 붙고 두 개의 개행 문자로 끝나는 JSON 문자열입니다.

    SSE를 통해 에이전트 응답의 스트리밍을 처리합니다.

    이 엔드포인트는 사용자 입력을 받아 지정된 LangGraph 에이전트로 전달하고,
    에이전트의 출력을 실시간으로 클라이언트에 다시 스트리밍합니다.
    """
    logger.info(f'user_input_message: {user_input.message}')
    return StreamingResponse(
        message_generator(user_input, agent, http_session=http_session, search_service=search_service, search_limit=5),
        media_type='text/event-stream',
    )


@router.get(
    '/{agent_name}/{thread_id}/history',
    response_model=ChatHistory,
    summary='사용자 채팅 내역 조회',
    responses={200: {'description': '사용자 채팅 내역 조회 성공', 'model': ChatHistory}, **ERROR_RESPONSES},
)
async def get_history(
    thread_id: Annotated[str, Path(..., description='사용자 채팅 내역 조회할 스레드 ID', examples=['847c6285-8fc9-4560-a83f-4e6285809254'])],
    agent: AgentDep,
    agent_name: Annotated[str, Path(..., description=f'사용자 채팅 내역 조회할 에이전트 이름 \n 에이전트 목록 : {get_all_agent_info()}')],
) -> ChatHistory:
    logger.info(f'agent_name: {agent_name}')
    try:
        state_snapshot = await agent.aget_state(config=RunnableConfig(configurable={'thread_id': thread_id}))
        messages: list[AnyMessage] = state_snapshot.values.get('messages', [])
        chat_messages: list[ChatMessage] = [langchain_to_chat_message(m) for m in messages]
        return ChatHistory(messages=chat_messages)
    except Exception as e:
        logger.error(f'An exception occurred: {e}')
        raise HTTPException(status_code=500, detail='Unexpected error') from e


@router.delete(
    '/{thread_id}/history',
    summary='사용자 채팅 내역 삭제',
    response_model=DeleteHistoryResponse,
    responses={200: {'description': '사용자 채팅 내역 삭제 성공', 'model': DeleteHistoryResponse}, **ERROR_RESPONSES},
)
async def delete_history(
    thread_id: Annotated[str, Path(description='사용자 채팅 내역 삭제할 스레드 ID')],
    agents: Annotated[dict[str, CompiledStateGraph], Depends(get_agents)],
) -> DeleteHistoryResponse:
    try:
        for agent in agents.values():
            await agent.checkpointer.adelete_thread(thread_id)
        return DeleteHistoryResponse(success=True, message='사용자 채팅 내역 삭제 완료', data={'thread_id': thread_id})
    except Exception as e:
        logger.error(f'An exception occurred: {e}')
        raise HTTPException(status_code=500, detail='Unexpected error') from e


@router.get('/threads', summary='모든 thread_id 조회', response_model=dict)
async def get_all_thread_ids(
    connection: DBConnectionDep,
) -> dict:
    """
    데이터베이스에 저장된 모든 고유한 thread_id를 조회합니다.
    """
    try:
        async with connection.cursor() as cursor:
            await cursor.execute('SELECT DISTINCT thread_id FROM checkpoints')
            result = await cursor.fetchall()
            # thread_ids = [row[0] for row in rows if row[0] is not None]
            return {
                'thread_ids': [r.get('thread_id') for r in result if r.get('thread_id') is not None],
                'count': len(result),
            }
    except Exception as e:
        logger.error(f'Error getting all thread_ids: {e}')
        raise HTTPException(status_code=500, detail='Unexpected error') from e


@router.delete(
    '/histories',
    summary='모든 사용자 채팅 내역 삭제',
    response_model=DeleteHistoryResponse,
    responses={200: {'description': '모든 사용자 채팅 내역 삭제 성공', 'model': DeleteHistoryResponse}, **ERROR_RESPONSES},
)
async def delete_all_histories(
    agents: Annotated[dict[str, CompiledStateGraph], Depends(get_agents)],
    connection: DBConnectionDep,
) -> DeleteHistoryResponse:
    """
    데이터베이스에 저장된 모든 사용자의 채팅 내역을 삭제합니다.
    """
    try:
        # 1. 모든 thread_id 가져오기
        async with connection.cursor() as cursor:
            await cursor.execute('SELECT DISTINCT thread_id FROM checkpoints')
            result = await cursor.fetchall()
            thread_ids = [r.get('thread_id') for r in result if r.get('thread_id') is not None]

        if not thread_ids:
            return DeleteHistoryResponse(success=True, message='삭제할 채팅 내역이 없습니다.', data={'deleted_threads_count': 0})

        # 2. 모든 thread_id에 대해 모든 agent의 내역을 삭제하는 태스크 생성
        tasks = []
        for thread_id in thread_ids:
            for agent in agents.values():
                tasks.append(agent.checkpointer.adelete_thread(thread_id))

        # 3. asyncio.gather를 사용하여 동시 처리
        await asyncio.gather(*tasks)

        return DeleteHistoryResponse(
            success=True,
            message=f'총 {len(thread_ids)}개의 스레드에 대한 채팅 내역 삭제 완료',
            data={'deleted_threads_count': len(thread_ids)},
        )
    except Exception as e:
        logger.error(f'An exception occurred while deleting all histories: {e}')
        raise HTTPException(status_code=500, detail='Unexpected error') from e


@router.get(
    '/{agent_name}/{thread_id}/state',
    summary='사용자 채팅 내역 조회',
    response_model=dict[str, Any],
    responses={200: {'description': '사용자 채팅 내역 조회 성공', 'model': ChatHistory}, **ERROR_RESPONSES},
)
async def get_state(
    thread_id: Annotated[str, Path(..., description='사용자 채팅 내역 조회할 스레드 ID', examples=['847c6285-8fc9-4560-a83f-4e6285809254'])],
    agent: AgentDep,
) -> dict[str, Any]:
    try:
        state_snapshot = await agent.aget_state(config=RunnableConfig(configurable={'thread_id': thread_id}))
        return state_snapshot.values
    except Exception as e:
        logger.error(f'An exception occurred: {e}')
        raise HTTPException(status_code=500, detail='Unexpected error') from e


@router.get(
    '/stream/mock',
    response_class=StreamingResponse,
    responses=sse_response_example(),
    summary='테스트 목적으로 mock SSE 응답을 스트리밍합니다.',
)
async def stream_mock() -> StreamingResponse:
    """
    테스트 목적으로 mock SSE 응답을 스트리밍합니다.
    """

    async def mock_sse_generator() -> AsyncGenerator[str, None]:
        mock_data_str = get_mock_sse_response()
        print(f'mock_data_str: {mock_data_str}')
        for line in mock_data_str.split('\n\n'):
            print(f'line: {line}')
            if line:
                yield f'{line}\n\n'
                await asyncio.sleep(0.1)

    return StreamingResponse(
        mock_sse_generator(),
        media_type='text/event-stream',
    )


@router.get(
    '/health',
    summary='health check',
)
async def health_check() -> dict:
    """ """
    return {'status': 'ok'}
