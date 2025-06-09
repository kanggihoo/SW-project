from fastapi import WebSocket, WebSocketDisconnect , APIRouter
import uuid
import json
from fastapi.encoders import jsonable_encoder

# Import the compiled graph object
from app.langgraph.graph import graph

router = APIRouter(tags=["websocket"])

@router.websocket("/ws" )
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles WebSocket connections, running the LangGraph chain for each session.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": session_id,
            "llm_model" : {
                "model": "gemini-1.5-flash",
                "prompt_template": "You are a helpful assistant that recommends clothing items based on the user's query. ",
            },
            "k": 3
        },
    }
    print(f"New client connected: {session_id}")

    try:
        while True:
            # Receive JSON data from the client
            data = await websocket.receive_json()
            user_message = data.get("message")
            
            if not user_message:
                continue

            # Determine if this is the start of the conversation or feedback
            current_state = await graph.aget_state(config)
            input_data = None
            if current_state is None or not current_state.next:
                # Start a new graph run
                input_data = {"user_query": user_message}
            else: # 인터럽트 걸린 경우 
                # It's feedback, so update the state and continue the run
                #FIXME :   이 부분에서 문제가 발생할 수 있음 (State 구조 변하는 순간)
                await graph.aupdate_state(config, {"user_feedback": user_message})
                # input_data is None to continue from the interrupted state

            # Stream the graph execution and send updates to the client
            recommendation = ""
            async for stream_type , chunk in graph.astream(
                input_data, 
                config=config, 
                stream_mode=["updates","messages"], 
                interrupt_before=["wait_for_user_feedback_node"]
            ):
                if stream_type == "messages":
                    AIMessage_chunk , metadata = chunk
                    message = AIMessage_chunk.content
                    node_name = metadata["langgraph_node"]
                    if message:
                        await websocket.send_json({
                            "status": "llm_stream_chunk",
                            "node": node_name,
                            "content": message
                        })
                        recommendation += message
                elif stream_type == "updates":
                    node_name = list(chunk.keys())[0]
                    updated_state = chunk[node_name]
                    if updated_state is not None and not isinstance(updated_state, tuple): # 특정 Node에서 State 변환가 없는 경우 None을 반환하는 경우 , interrupt가 발생됨을 알리는 {'__interrupt__': ()} 제외
                        updated_state_name = list(updated_state.keys())[0]
                        updated_state_value = updated_state[updated_state_name]
                        
                        # llm node의 맨 마지막 출력에는 stream이 결합된 하나의 문자열로 전송
                        if node_name == "select_final_item_node" and updated_state_name == "llm_output" and recommendation:
                            print("--------------------------------")
                            print(recommendation)
                            await websocket.send_json({
                                "status": "final_recommendation",
                                "node": node_name,
                                "response": recommendation
                            })
                        else:
                            await websocket.send_json({
                                "status": updated_state_name,
                                "node": node_name,
                                "response": updated_state_value
                            })
                else:
                    ...    
                            

            # After streaming, check if the graph is finished or waiting for feedback
            final_state = await graph.aget_state(config)
            if not final_state or not final_state.next: # 최종 상태가 없거나 다음 상태가 없는 경우(whiule 문 중단)
                await websocket.send_json(
                    {
                        "status": "finished",
                        "response": "Conversation finished.",
                    }
                )
                #TODO : 음 여기서 break 하고 다시 client 측에서 disconnect 버튼 누르고 다시 연결 한 뒤 메세지 보내야 다시 동작.
                break  # End the session
            else:
                await websocket.send_json(
                    {
                        "status": "waiting_for_feedback",
                        "response": "Please provide feedback or your next query."
                    }
                )

    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    except Exception as e:
        error_message = f"An error occurred: {e}"
        print(error_message)
        try:
            # Try to inform the client about the error
            await websocket.send_json({"error": error_message})
        except RuntimeError:
            # Websocket might be closed already
            pass


