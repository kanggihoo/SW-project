import json
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from loguru import logger

from graph.model.api_schema import ChatMessage, StreamInput, UserInput
from graph.model.constants import SSETypes

from .messages import convert_message_content_to_string, create_ai_message, create_message, langchain_to_chat_message, remove_tool_calls


async def handle_user_input(user_input: UserInput, agent: CompiledStateGraph, **kwargs) -> tuple[dict[str, Any], uuid4]:
    """
    user_input을 parsing 하고 , 현재 graph 상태가 interrupt 상태인지 확인 후 재개가 필요한 경우 Command 객체를 생성하여 "input" 키에 사용자가 입력한 메세지를 전달
    그렇지 않다면 "input" 키에 HumanMessage 객체에 사용자가 입력한 메세지 전달(문자열)
    Return kwargs for agent invocation and the run_id
    Args:
        user_input (UserInput): user input
        agent (CompiledStateGraph): agent

    Returns:
        tuple[dict[str, Any], str]: kwargs and run_id

    Raises:
        HTTPException: 입력 검증 실패 시
        ValueError: 필수 파라미터 누락 시
        Exception: 기타 예상치 못한 오류 시
    """
    try:
        run_id = uuid4()
        thread_id = user_input.thread_id
        user_id = user_input.user_id

        if not thread_id:
            logger.error('thread_id is required')
            raise ValueError('thread_id is required')

        if not user_id:
            logger.error('user_id is required')
            raise ValueError('user_id is required')

        configurable = {'thread_id': thread_id, 'user_id': user_id, 'model': user_input.model, **kwargs}
        callbacks = []

        # if settings.LANGFUSE_TRACING:
        #     # Initialize Langfuse CallbackHandler for Langchain (tracing)
        #     langfuse_handler = CallbackHandler()

        #     callbacks.append(langfuse_handler)

        if user_input.agent_config:
            if overlap := user_input.agent_config.keys() & configurable.keys():
                raise HTTPException(status_code=400, detail=f'Overlapping keys in agent_config: {overlap}')
            configurable.update(user_input.agent_config)

            try:
                config = RunnableConfig(configurable=configurable, callbacks=callbacks, run_id=run_id)
            except Exception as e:
                logger.error(f'Failed to create RunnableConfig: {e}')
                raise ValueError(f'Failed to create RunnableConfig: {e}')

            # 현재 agent(CompiledStateGraph) 의 상태를 가져와서 interrupt 상태인지 확인
            try:
                state = await agent.aget_state(config)
            except Exception as e:
                logger.error(f'Failed to get agent state: {e}')
                raise ValueError(f'Failed to get agent state: {e}')

            interrupted_task = [task for task in state.tasks if hasattr(task, 'interrupt') and task.interrupts]

            input: Command | dict[str, Any]

        if interrupted_task:
            input = Command(resume=user_input.message)
        else:
            input = {
                'messages': create_message(message_type='human', content=user_input.message),
                'user_message': user_input.message,
                'experts_to_run': ['color_expert', 'style_analyst', 'fitting_coordinator'],
            }

            kwargs = {
                'input': input,
                'config': config,
            }

            logger.info(f'Successfully handled user input for run_id: {run_id}')
            return kwargs, run_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Unexpected error in handle_user_input: {e}', exc_info=True)
        raise


# TODO : SSE 응답 결과도 서버에서 확인을 해야 해서 logging 추가
async def message_generator(user_input: StreamInput, agent: CompiledStateGraph, **kwargs) -> AsyncGenerator[str, None]:
    """Generate a stream of messages from the agent
    스트리밍 모드로 요청을 받았을 때, graph의 동작과정을 SSE 방식으로 전송하기 위한 비동기 제너레이터

    Args:
        user_input (StreamInput): user input
        agent (CompiledStateGraph): agent / agent_name에 맞는 CompiledStateGraph 객체
    """
    try:
        kwargs, run_id = await handle_user_input(user_input, agent, **kwargs)

    except Exception as e:
        logger.error(f'Failed to handle user input: {e}', exc_info=True)
        yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Failed to process user input: {str(e)}"})}\n\n'
        return

    try:
        async for stream_event in agent.astream(**kwargs, stream_mode=['updates', 'custom', 'messages'], subgraphs=True):
            if not isinstance(stream_event, tuple):
                continue

            # subgraphs = True 인 경우
            if len(stream_event) == 3:
                name_space, stream_mode_type, data = stream_event

            else:
                stream_mode_type, data = stream_event

            filtered_messages = []  # "updates" 모드에서 특정 노드의 결과를 포함할 메세지 리스트

            if stream_mode_type == 'updates':
                # ===============================================================================================================
                # stream_mode == "updates" 인 경우 , data에는 특정 노드에서 업데이트 된 모든 정보를 dict로 담고 있음
                # => 여기서는 해당 dict로 부터 "messages" 키에 있는 메세지 리스트 만을 추출해서 처리
                # ===============================================================================================================
                if not isinstance(data, dict):
                    logger.warning(f'Expected dict for updates data, got {type(data)}')
                    continue

                for node_name, updates in data.items():
                    # 특정 노드에서 업데이트 된 딕셔너리로 부터 messages 키에 있는 메세지 리스트 추출
                    if not isinstance(updates, dict):
                        logger.warning(f'Expected dict for node updates, got {type(updates)} for node {node_name}')
                        continue

                    updated_messages = updates.get('messages', [])

                    # node_name 이름에 따라 처리 (supervisor 노드의 도구 호출 결과가 필요한 경우만 처리, 나머지 중간노드 결과는 pass)
                    if node_name == 'supervisor':
                        if isinstance(updated_messages[-1], ToolMessage):  # tool 메세지만 필요
                            updated_messages = [updated_messages[-1]]
                        else:
                            # 중간 노드 메세지 제거
                            updated_messages = []

                    if node_name in ('research_expert', 'math_expert'):
                        # 중간 노드 메세지 제거
                        updated_messages = []

                    filtered_messages.extend(updated_messages)

            # updates 모드에서 사용자에게 결과 보여줄 메세지 추가 가공 (튜플 형식으로 제공되는 메세지인 경우(ChatMessage)는 분리 후 AIMessage 객체로 변환??)
            processed_messages: list[AIMessage | BaseMessage] = []
            current_message: dict[str, Any] = {}
            for message in filtered_messages:
                try:
                    if isinstance(message, tuple):
                        key, value = message
                        # Store parts in temporary dict
                        current_message[key] = value
                    else:
                        # Add complete message if we have one in progress
                        if current_message:
                            try:
                                processed_messages.append(create_ai_message(current_message))
                            except Exception as e:
                                logger.error(f'Error creating AI message from parts: {e}, parts: {current_message}', exc_info=True)
                            current_message = {}
                        processed_messages.append(message)
                except Exception as e:
                    logger.error(f'Error processing message: {e}, message: {message}', exc_info=True)
                    continue

                # Add any remaining message parts
                if current_message:
                    try:
                        processed_messages.append(create_ai_message(current_message))
                    except Exception as e:
                        logger.error(f'Error creating final AI message from parts: {e}, parts: {current_message}', exc_info=True)

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "updates" 인 경우) => {"type": "message", "content": ChatMessage}
            # 1. langgraph에서 반환된 BaseMessage 객체를 ChatMessage 객체로 변환 (langchain_to_chat_message 함수 참고)
            # 2. ChatMessage 객체를 SSE 응답 형식으로 변환
            # 사용자가 입력한 메세지는 다시 전송하지 않음.
            # ===============================================================================================================
            for message in processed_messages:
                try:
                    if isinstance(message, BaseMessage):
                        chat_message = langchain_to_chat_message(message)
                        # chat_message.run_id = str(run_id)
                    else:
                        data = {
                            'type': 'ai',
                            'content': message,
                        }
                        chat_message = ChatMessage.model_validate(data)
                except Exception as e:
                    logger.error(f'Error parsing message: {e}, message: {message}', exc_info=True)
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error parsing message: {str(e)}"})}\n\n'
                    continue

                # 사용자가 입력한 메세지를 다시 전송하는 것을 방지
                if chat_message.type == 'human' and chat_message.content == user_input.message:
                    continue
                logger.debug(f'stream_mode_type: update인 경우 : {chat_message.model_dump()}')
                yield f'data: {json.dumps({"type": SSETypes.MESSAGE.value, "content": chat_message.model_dump()})}\n\n'

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "messages" 인 경우) => {"type": "token", "content": ChatMessage}
            # ===============================================================================================================
            if stream_mode_type == 'messages':
                try:
                    if not user_input.stream_tokens:
                        continue
                    msg, metadata = data
                    if 'skip_stream' in metadata.get('tags', []):
                        continue

                    # ===============================================================================================================
                    # 특정 노드에서 BaseMessage 형태로 반환하는 경우 "updates" 모드와 "messages" 모드에서 모두 반환.
                    # 따라서 messages 모드에서는 AIMessageChunk 형태가 아닌 경우는 Drop 처리.
                    # ===============================================================================================================
                    if not isinstance(msg, AIMessageChunk):
                        continue
                    content = remove_tool_calls(msg.content)
                    if content:
                        # Empty content in the context of OpenAI usually means
                        # that the model is asking for a tool to be invoked.
                        # So we only print non-empty content.
                        logger.info(f'stream_mode_type: messages인 경우 : {convert_message_content_to_string(content)}')
                        yield f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": convert_message_content_to_string(content)})}\n\n'
                except Exception as e:
                    logger.error(f'Error processing messages stream: {e}', exc_info=True)
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing messages: {str(e)}"})}\n\n'

            # ===============================================================================================================
            # stream_mode_type == "custom" 인 경우 처리 (외부 LLM 스트리밍 결과 처리 및 writer를 이용해서 출력을 내보내는 경우 처리)
            # 실제 데이터는 python dict 형식으로 {"type": "token" | "status" , "content": "데이터"} 형식으로 전달됨
            # 이때 content 데이터는 StatusUpdate 모델 형식으로 전달됨
            # ===============================================================================================================
            if stream_mode_type == 'custom':
                try:
                    if not isinstance(data, dict) or 'type' not in data or 'content' not in data:
                        logger.warning(f'Invalid custom data format: {data}')
                        continue

                    type, content = data['type'], data['content']
                    logger.info(f'stream_mode_type: custom인 경우 : {type} , {content}')
                    match type:
                        case SSETypes.TOKEN.value:
                            yield f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": content})}\n\n'
                        case SSETypes.STATUS.value:
                            yield f'data: {json.dumps({"type": SSETypes.STATUS.value, "content": content})}\n\n'
                        case _:
                            logger.warning(f'Unknown custom type: {type}')
                except Exception as e:
                    logger.error(f'Error processing custom stream: {e}', exc_info=True)
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing custom stream: {str(e)}"})}\n\n'

    except Exception as e:
        logger.error(f'Critical error in message generator: {e}', exc_info=True)
        yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Critical error: {str(e)}"})}\n\n'
    finally:
        logger.info('Message generation completed')
        yield f'data: {json.dumps({"type": SSETypes.END.value, "content": ""})}\n\n'


async def show_graph_stream(
    graph: CompiledStateGraph, input: dict, config: RunnableConfig, user_input: UserInput, return_result: bool = False
) -> None | ChatMessage:
    try:
        async for stream_event in graph.astream(input=input, config=config, stream_mode=['updates', 'custom', 'messages'], subgraphs=True):
            if not isinstance(stream_event, tuple):
                continue

            # subgraphs = True 인 경우
            if len(stream_event) == 3:
                name_space, stream_mode_type, data = stream_event

            else:
                stream_mode_type, data = stream_event

            filtered_messages = []  # "updates" 모드에서 특정 노드의 결과를 포함할 메세지 리스트

            if stream_mode_type == 'updates':
                # ===============================================================================================================
                # stream_mode == "updates" 인 경우 , data에는 특정 노드에서 업데이트 된 모든 정보를 dict로 담고 있음
                # => 여기서는 해당 dict로 부터 "messages" 키에 있는 메세지 리스트 만을 추출해서 처리
                # ===============================================================================================================
                if not isinstance(data, dict):
                    logger.warning(f'Expected dict for updates data, got {type(data)}')
                    continue

                for node_name, updates in data.items():
                    # 특정 노드에서 업데이트 된 딕셔너리로 부터 messages 키에 있는 메세지 리스트 추출
                    if not isinstance(updates, dict):
                        logger.warning(f'Expected dict for node updates, got {type(updates)} for node {node_name}')
                        continue

                    if return_result and node_name == 'external_streaming_llm':
                        return updates.get('expert_opinions', '')

                    updated_messages = updates.get('messages', [])
                    filtered_messages.extend(updated_messages)

                # updates 모드에서 사용자에게 결과 보여줄 메세지 추가 가공 (튜플 형식으로 제공되는 메세지인 경우(ChatMessage)는 분리 후 AIMessage 객체로 변환??)
            processed_messages: list[AIMessage | BaseMessage] = []
            current_message: dict[str, Any] = {}
            for message in filtered_messages:
                try:
                    if isinstance(message, tuple):
                        key, value = message
                        # Store parts in temporary dict
                        current_message[key] = value
                    else:
                        # Add complete message if we have one in progress
                        if current_message:
                            try:
                                processed_messages.append(create_ai_message(current_message))
                            except Exception as e:
                                logger.error(f'Error creating AI message from parts: {e}, parts: {current_message}', exc_info=True)
                            current_message = {}
                        processed_messages.append(message)
                except Exception as e:
                    logger.error(f'Error processing message: {e}, message: {message}', exc_info=True)
                    continue

                # Add any remaining message parts
                if current_message:
                    try:
                        processed_messages.append(create_ai_message(current_message))
                    except Exception as e:
                        logger.error(f'Error creating final AI message from parts: {e}, parts: {current_message}', exc_info=True)

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "updates" 인 경우) => {"type": "message", "content": ChatMessage}
            # 1. langgraph에서 반환된 BaseMessage 객체를 ChatMessage 객체로 변환 (langchain_to_chat_message 함수 참고)
            # 2. ChatMessage 객체를 SSE 응답 형식으로 변환
            # 사용자가 입력한 메세지는 다시 전송하지 않음.
            # ===============================================================================================================
            for message in processed_messages:
                try:
                    if isinstance(message, BaseMessage):
                        chat_message = langchain_to_chat_message(message)
                        # chat_message.run_id = str(run_id)
                    else:
                        data = {
                            'type': 'ai',
                            'content': message,
                        }
                        chat_message = ChatMessage.model_validate(data)
                except Exception as e:
                    logger.error(f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error parsing message: {str(e)}"})}\n\n')
                    continue

                # 사용자가 입력한 메세지를 다시 전송하는 것을 방지
                if chat_message.type == 'human' and chat_message.content == user_input.message:
                    continue
                logger.info(f'data: {json.dumps({"type": SSETypes.MESSAGE.value, "content": chat_message.model_dump()})}\n\n')

                if return_result and chat_message and isinstance(chat_message, ChatMessage):
                    return chat_message

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "messages" 인 경우) => {"type": "token", "content": ChatMessage}
            # ===============================================================================================================
            if stream_mode_type == 'messages':
                try:
                    msg, metadata = data
                    if 'skip_stream' in metadata.get('tags', []):
                        continue

                    # ===============================================================================================================
                    # 특정 노드에서 BaseMessage 형태로 반환하는 경우 "updates" 모드와 "messages" 모드에서 모두 반환.
                    # 따라서 messages 모드에서는 AIMessageChunk 형태가 아닌 경우는 Drop 처리.
                    # ===============================================================================================================
                    if not isinstance(msg, AIMessageChunk):
                        continue
                    content = remove_tool_calls(msg.content)
                    if content:
                        # Empty content in the context of OpenAI usually means
                        # that the model is asking for a tool to be invoked.
                        # So we only print non-empty content.
                        logger.info(f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": convert_message_content_to_string(content)})}\n\n')
                except Exception as e:
                    logger.error(f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing messages: {str(e)}"})}\n\n')

            # ===============================================================================================================
            # stream_mode_type == "custom" 인 경우 처리 (외부 LLM 스트리밍 결과 처리 및 writer를 이용해서 출력을 내보내는 경우 처리)
            # 실제 데이터는 python dict 형식으로 {"type": "token" | "status" , "content": "데이터"} 형식으로 전달됨
            # 이때 content 데이터는 StatusUpdate 모델 형식으로 전달됨
            # ===============================================================================================================
            if stream_mode_type == 'custom':
                try:
                    if not isinstance(data, dict) or 'type' not in data or 'content' not in data:
                        logger.warning(f'Invalid custom data format: {data}')
                        continue

                    type, content = data['type'], data['content']
                    logger.debug(f'stream_mode_type: custom인 경우 : {type} , {content}')
                    match type:
                        case SSETypes.TOKEN.value:
                            logger.info(f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": content})}\n\n')
                        case SSETypes.STATUS.value:
                            logger.info(f'data: {json.dumps({"type": SSETypes.STATUS.value, "content": content})}\n\n')
                        case _:
                            logger.warning(f'Unknown custom type: {type}')
                except Exception as e:
                    logger.error(f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing custom stream: {str(e)}"})}\n\n')

    except Exception as e:
        logger.error(f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Critical error: {str(e)}"})}\n\n')

    finally:
        logger.info(f'data: {json.dumps({"type": SSETypes.END.value, "content": ""})}\n\n')


async def test_message_generator(agent: CompiledStateGraph, input: dict, config: RunnableConfig, user_input: UserInput) -> AsyncGenerator[str, None]:
    """Generate a stream of messages from the agent
    스트리밍 모드로 요청을 받았을 때, graph의 동작과정을 SSE 방식으로 전송하기 위한 비동기 제너레이터

    Args:
        user_input (StreamInput): user input
        agent (CompiledStateGraph): agent / agent_name에 맞는 CompiledStateGraph 객체
    """
    try:
        async for stream_event in agent.astream(input=input, config=config, stream_mode=['updates', 'custom', 'messages'], subgraphs=True):
            if not isinstance(stream_event, tuple):
                continue

            # subgraphs = True 인 경우
            if len(stream_event) == 3:
                name_space, stream_mode_type, data = stream_event

            else:
                stream_mode_type, data = stream_event

            filtered_messages = []  # "updates" 모드에서 특정 노드의 결과를 포함할 메세지 리스트

            if stream_mode_type == 'updates':
                # ===============================================================================================================
                # stream_mode == "updates" 인 경우 , data에는 특정 노드에서 업데이트 된 모든 정보를 dict로 담고 있음
                # => 여기서는 해당 dict로 부터 "messages" 키에 있는 메세지 리스트 만을 추출해서 처리
                # ===============================================================================================================
                if not isinstance(data, dict):
                    logger.warning(f'Expected dict for updates data, got {type(data)}')
                    continue

                for node_name, updates in data.items():
                    # 특정 노드에서 업데이트 된 딕셔너리로 부터 messages 키에 있는 메세지 리스트 추출
                    if not isinstance(updates, dict):
                        logger.warning(f'Expected dict for node updates, got {type(updates)} for node {node_name}')
                        continue

                    updated_messages = updates.get('messages', [])

                    # node_name 이름에 따라 처리 (supervisor 노드의 도구 호출 결과가 필요한 경우만 처리, 나머지 중간노드 결과는 pass)
                    # if node_name == 'supervisor':
                    #     if isinstance(updated_messages[-1], ToolMessage):  # tool 메세지만 필요
                    #         updated_messages = [updated_messages[-1]]
                    #     else:
                    #         # 중간 노드 메세지 제거
                    #         updated_messages = []

                    # if node_name in ('research_expert', 'math_expert'):
                    #     # 중간 노드 메세지 제거
                    #     updated_messages = []

                    filtered_messages.extend(updated_messages)

            # updates 모드에서 사용자에게 결과 보여줄 메세지 추가 가공 (튜플 형식으로 제공되는 메세지인 경우(ChatMessage)는 분리 후 AIMessage 객체로 변환??)
            processed_messages: list[AIMessage | BaseMessage] = []
            current_message: dict[str, Any] = {}
            for message in filtered_messages:
                try:
                    if isinstance(message, tuple):
                        key, value = message
                        # Store parts in temporary dict
                        current_message[key] = value
                    else:
                        # Add complete message if we have one in progress
                        if current_message:
                            try:
                                processed_messages.append(create_ai_message(current_message))
                            except Exception as e:
                                logger.error(f'Error creating AI message from parts: {e}, parts: {current_message}', exc_info=True)
                            current_message = {}
                        processed_messages.append(message)
                except Exception as e:
                    logger.error(f'Error processing message: {e}, message: {message}', exc_info=True)
                    continue

                # Add any remaining message parts
                if current_message:
                    try:
                        processed_messages.append(create_ai_message(current_message))
                    except Exception as e:
                        logger.error(f'Error creating final AI message from parts: {e}, parts: {current_message}', exc_info=True)

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "updates" 인 경우) => {"type": "message", "content": ChatMessage}
            # 1. langgraph에서 반환된 BaseMessage 객체를 ChatMessage 객체로 변환 (langchain_to_chat_message 함수 참고)
            # 2. ChatMessage 객체를 SSE 응답 형식으로 변환
            # 사용자가 입력한 메세지는 다시 전송하지 않음.
            # ===============================================================================================================
            for message in processed_messages:
                try:
                    if isinstance(message, BaseMessage):
                        chat_message = langchain_to_chat_message(message)
                        # chat_message.run_id = str(run_id)
                    else:
                        data = {
                            'type': 'ai',
                            'content': message,
                        }
                        chat_message = ChatMessage.model_validate(data)
                except Exception as e:
                    logger.error(f'Error parsing message: {e}, message: {message}', exc_info=True)
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error parsing message: {str(e)}"})}\n\n'
                    continue

                # 사용자가 입력한 메세지를 다시 전송하는 것을 방지
                if chat_message.type == 'human' and chat_message.content == user_input.message:
                    continue
                data = chat_message.model_dump()
                logger.info(f'type: {SSETypes.MESSAGE} , content: {data}')
                yield f'data: {json.dumps({"type": SSETypes.MESSAGE, "content": data})}\n\n'

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "messages" 인 경우) => {"type": "token", "content": ChatMessage}
            # ===============================================================================================================
            if stream_mode_type == 'messages':
                msg = None
                try:
                    msg, metadata = data
                    if 'skip_stream' in metadata.get('tags', []):
                        continue

                    # ===============================================================================================================
                    # 특정 노드에서 BaseMessage 형태로 반환하는 경우 "updates" 모드와 "messages" 모드에서 모두 반환.
                    # 따라서 messages 모드에서는 AIMessageChunk 형태가 아닌 경우는 Drop 처리.
                    # ===============================================================================================================
                    if not isinstance(msg, AIMessageChunk):
                        continue
                    content = remove_tool_calls(msg.content)
                    if content:
                        # Empty content in the context of OpenAI usually means
                        # that the model is asking for a tool to be invoked.
                        # So we only print non-empty content.
                        data = convert_message_content_to_string(content)
                        logger.info(f'type: {SSETypes.TOKEN} , content: {data}')
                        yield f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": data})}\n\n'
                except Exception as e:
                    logger.error(f'Error processing messages stream | content : {msg} ,  error: {e}', exc_info=True)
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing messages: {str(e)}"})}\n\n'

            # ===============================================================================================================
            # stream_mode_type == "custom" 인 경우 처리 (외부 LLM 스트리밍 결과 처리 및 writer를 이용해서 출력을 내보내는 경우 처리)
            # 실제 데이터는 python dict 형식으로 {"type": "token" | "status" , "content": "데이터"} 형식으로 전달됨
            # 이때 content 데이터는 StatusUpdate 모델 형식으로 전달됨
            # ===============================================================================================================
            if stream_mode_type == 'custom':
                type, content = None, None
                try:
                    if not isinstance(data, dict) or 'type' not in data or 'content' not in data:
                        logger.warning(f'Invalid custom data format: {data}')
                        continue

                    type, content = data['type'], data['content']
                    match type:
                        case SSETypes.TOKEN.value:
                            logger.info(f'type: {SSETypes.TOKEN} , content: {content}')
                            yield f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": content})}\n\n'
                        case SSETypes.STATUS.value:
                            logger.info(f'type: {SSETypes.STATUS} , content: {content}')
                            yield f'data: {json.dumps({"type": SSETypes.STATUS.value, "content": content})}\n\n'
                        case _:
                            logger.warning(f'Unknown custom type: {type} , content: {content}')
                except Exception as e:
                    logger.error(f'Error processing custom stream | content : {content} , error: {e}', exc_info=True)
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing custom stream: {str(e)}"})}\n\n'

    except Exception as e:
        logger.error(f'Critical error in message generator: {e}', exc_info=True)
        yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Critical error: {str(e)}"})}\n\n'
    finally:
        logger.info('Message generation completed')
        yield f'data: {json.dumps({"type": SSETypes.END.value, "content": ""})}\n\n'
