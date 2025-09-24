from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command , Interrupt

from langchain_core.messages import HumanMessage , AIMessageChunk , ToolMessage , AIMessage , BaseMessage
from langchain_core.runnables import RunnableConfig

from fastapi import HTTPException
from typing import Any , AsyncGenerator
import logging
from uuid import uuid4
import json


from graph.model.constants import SSETypes
from graph.model.api_schema import UserInput , StreamInput , StatusUpdate , ChatMessage
from .messages import (
    remove_tool_calls , 
    convert_message_content_to_string , 
    create_ai_message , 
    langchain_to_chat_message,
    create_message
)

logger = logging.getLogger(__name__)

async def handle_user_input(user_input:UserInput , agent:CompiledStateGraph , **kwargs)->tuple[dict[str , Any] , uuid4]:
    """
    user_input을 parsing 하고 , 현재 graph 상태가 interrupt 상태인지 확인 후 재개가 필요한 경우 Command 객체를 생성하여 "input" 키에 사용자가 입력한 메세지 전달
    그렇지 않다면 "input" 키에 HumanMessage 객체에 사용자가 입력한 메세지 전달(문자열)
    Return kwargs for agent invocation and the run_id
    Args:
        user_input (UserInput): user input
        agent (CompiledStateGraph): agent

    Returns:
        tuple[dict[str, Any], str]: kwargs and run_id
    """
    run_id = uuid4()
    thread_id = user_input.thread_id 
    user_id = user_input.user_id

    configurable = {"thread_id" : thread_id , "user_id" : user_id , "model" : user_input.model , **kwargs}
    callbacks = []

    # if settings.LANGFUSE_TRACING:
    #     # Initialize Langfuse CallbackHandler for Langchain (tracing)
    #     langfuse_handler = CallbackHandler()

    #     callbacks.append(langfuse_handler)

    if user_input.agent_config:
        if overlap := user_input.agent_config.keys() & configurable.keys():
            raise HTTPException(status_code=400 , detail=f"Overlapping keys in agent_config: {overlap}")
        configurable.update(user_input.agent_config)


    config = RunnableConfig(configurable=configurable , callbacks=callbacks , run_id=run_id)

    # 현재 agent(CompiledStateGraph) 의 상태를 가져와서 interrupt 상태인지 확인
    logger.info(f"agent_config: {config}")
    state = await agent.aget_state(config)
    interrupted_task = [
        task for task in state.tasks if hasattr(task , "interrupt") and task.interrupts
    ]

    input : Command | dict[str , Any]

    if interrupted_task:
        input = Command(resume = user_input.message)
    else:
        input = {"messages" : create_message(message_type="human" , content=user_input.message) , "user_message" : user_input.message , "experts_to_run" : ["color_expert" , "style_analyst" , "fitting_coordinator"]}

    kwargs = {
        "input" : input ,
        "config" : config ,
    }

    return kwargs , run_id


async def message_generator(user_input:StreamInput , agent:CompiledStateGraph)->AsyncGenerator[str , None]:
    """Generate a stream of messages from the agent
    스트리밍 모드로 요청을 받았을 때, graph의 동작과정을 SSE 방식으로 전송하기 위한 비동기 제너레이터 

    Args:
        user_input (StreamInput): user input
        agent (CompiledStateGraph): agent / agent_name에 맞는 CompiledStateGraph 객체 
    """
    kwargs , run_id = await handle_user_input(user_input , agent)
    logger.debug(f"kwargs: {kwargs} \n run_id: {run_id}")

    try:
        async for stream_event in agent.astream(
            **kwargs, stream_mode=["updates", "custom", "messages"] , subgraphs=True
            ):

            if not isinstance(stream_event , tuple):
                continue

            #subgraphs = True 인 경우 
            if len(stream_event) == 3:
                name_space , stream_mode_type , data = stream_event
            
            else:
                stream_mode_type , data = stream_event

            filtered_messages = [] # "updates" 모드에서 특정 노드의 결과를 포함할 메세지 리스트
            
            if stream_mode_type == "updates":
                #===============================================================================================================
                # stream_mode == "updates" 인 경우 , data에는 특정 노드에서 업데이트 된 모든 정보를 dict로 담고 있음
                # => 여기서는 해당 dict로 부터 "messages" 키에 있는 메세지 리스트 만을 추출해서 처리 
                #===============================================================================================================
                for node_name , updates in data.items():
                    # 인터럽트 처리 (대화 중단 시 인터럽트 메세지 처리)
                    # if node_name == "__interrupt__" : 
                    #     interrupt: Interrupt
                    #     for interrupt in updates: # 인터럽트 노드에서에 뭘 반환하길레 intrrupt.value로 접근하지?
                    #         new_messages.append(AIMessage(content=interrupt.value))
                    #     continue

                    # 특정 노드에서 업데이트 된 딕셔너리로 부터 messages 키에 있는 메세지 리스트 추출
                    updated_messages = updates.get("messages" , [])


                    # node_name 이름에 따라 처리 (supervisor 노드의 도구 호출 결과가 필요한 경우만 처리, 나머지 중간노드 결과는 pass)
                    if node_name == "supervisor" :
                        if isinstance(updated_messages[-1] , ToolMessage): # tool 메세지만 필요 
                            updated_messages = [updated_messages[-1]]
                        else:
                            # 중간 노드 메세지 제거 
                            updated_messages = []

                    if node_name in ("research_expert" , "math_expert"):
                        # 중간 노드 메세지 제거 
                        updated_messages = []
                    
                    filtered_messages.extend(updated_messages)

            # updates 모드에서 사용자에게 결과 보여줄 메세지 추가 가공 (튜플 형식으로 제공되는 메세지인 경우(ChatMessage)는 분리 후 AIMessage 객체로 변환??)
            processed_messages:list[AIMessage | BaseMessage] = []
            current_message: dict[str, Any] = {}
            for message in filtered_messages:
                if isinstance(message, tuple):
                    key, value = message
                    # Store parts in temporary dict
                    current_message[key] = value
                else:
                    # Add complete message if we have one in progress
                    if current_message:
                        processed_messages.append(create_ai_message(current_message))
                        current_message = {}
                    processed_messages.append(message)

            # Add any remaining message parts
            if current_message:
                processed_messages.append(create_ai_message(current_message))
            
            #===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "updates" 인 경우) => {"type": "message", "content": ChatMessage}
            # 1. langgraph에서 반환된 BaseMessage 객체를 ChatMessage 객체로 변환 (langchain_to_chat_message 함수 참고)
            # 2. ChatMessage 객체를 SSE 응답 형식으로 변환
            # 사용자가 입력한 메세지는 다시 전송하지 않음.
            #===============================================================================================================
            for message in processed_messages:
                try:
                    if isinstance(message, BaseMessage):
                        chat_message = langchain_to_chat_message(message)
                        chat_message.run_id = str(run_id)
                    else:
                        data = {
                            "type" : "ai",
                            "content" : message,
                        }
                        chat_message = ChatMessage.model_validate(data)
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
                    yield f"data: {json.dumps({'type': SSETypes.ERROR.value, 'content': 'Unexpected error'})}\n\n"
                    

                # 사용자가 입력한 메세지를 다시 전송하는 것을 방지 
                if chat_message.type == "human" and chat_message.content == user_input.message:
                    continue
                logger.info(f"stream_mode_type: update인 경우 : {chat_message.model_dump()} \n {processed_messages}")
                yield f"data: {json.dumps({'type': SSETypes.MESSAGE.value, 'content': chat_message.model_dump()})}\n\n"


             #===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "messages" 인 경우) => {"type": "token", "content": ChatMessage}
            #===============================================================================================================
            if stream_mode_type == "messages":
                if not user_input.stream_tokens:
                    continue
                msg, metadata = data
                if "skip_stream" in metadata.get("tags", []):
                    continue
                
                #===============================================================================================================
                # 특정 노드에서 BaseMessage 형태로 반환하는 경우 "updates" 모드와 "messages" 모드에서 모두 반환.
                # 따라서 messages 모드에서는 AIMessageChunk 형태가 아닌 경우는 Drop 처리.
                #===============================================================================================================
                if not isinstance(msg, AIMessageChunk):
                    continue
                content = remove_tool_calls(msg.content)
                if content:
                    # Empty content in the context of OpenAI usually means
                    # that the model is asking for a tool to be invoked.
                    # So we only print non-empty content.
                    logger.info(f"stream_mode_type: messages인 경우 : {convert_message_content_to_string(content)}")
                    yield f"data: {json.dumps({'type': SSETypes.TOKEN.value, 'content': convert_message_content_to_string(content)})}\n\n"

            #===============================================================================================================
            # stream_mode_type == "custom" 인 경우 처리 (외부 LLM 스트리밍 결과 처리 및 writer를 이용해서 출력을 내보내는 경우 처리)
            # 실제 데이터는 python dict 형식으로 {"type": "token" | "status" , "content": "데이터"} 형식으로 전달됨
            # 이때 content 데이터는 StatusUpdate 모델 형식으로 전달됨
            #===============================================================================================================
            if stream_mode_type =="custom":
                type , content = data["type"] , data["content"]
                logger.info(f"stream_mode_type: custom인 경우 : {type} , {content}")
                match type:
                    case SSETypes.TOKEN.value:
                        yield f"data: {json.dumps({'type': SSETypes.TOKEN.value, 'content': content})}\n\n"
                    case SSETypes.STATUS.value:
                        yield f"data: {json.dumps({'type': SSETypes.STATUS.value, 'content': content})}\n\n"
                    
    except Exception as e:
        logger.error(f"Error in message generator: {e}")
        yield f"data: {json.dumps({'type': SSETypes.ERROR.value, 'content': 'Internal server error'})}\n\n"
    finally:
        yield f"data: {json.dumps({'type': SSETypes.END.value, 'content': ''})}\n\n"
    


def save_graph_image(graph: StateGraph , file_name: str):
    graph.get_graph().draw_mermaid_png(file_name)
