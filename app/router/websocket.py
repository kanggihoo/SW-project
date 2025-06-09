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
            else:
                # It's feedback, so update the state and continue the run
                #FIXME :   이 부분에서 문제가 발생할 수 있음 (State 구조 변하는 순간)
                await graph.aupdate_state(config, {"user_feedback": user_message})
                # input_data is None to continue from the interrupted state

            # Stream the graph execution and send updates to the client
            async for chunk in graph.astream(
                input_data, 
                config=config, 
                stream_mode="updates", 
                interrupt_before=["wait_for_user_feedback_node"]
            ):
                # Send each chunk from the stream to the client
                # The client will handle parsing the node and its output
                for node_name, updated_state in chunk.items():
                    if updated_state is not None:
                        # Check if this is an intermediate LLM stream chunk
                        if "llm_stream_chunk" in updated_state:
                            print("--------------------------------")
                            print("llm_stream_chunk")
                            print(f"Node: {node_name}, State: {updated_state}")
                            await websocket.send_json({
                                "status": "streaming_chunk",
                                "node": node_name,
                                "content": updated_state["llm_stream_chunk"]
                            })
                        # Check if this is the final output of the streaming node
                        elif "final_recommendation" in updated_state:
                             await websocket.send_json({
                                "status": "node_complete",
                                "node": node_name,
                                "response": jsonable_encoder(updated_state)
                            })
                             print("--------------------------------")
                             print("final_recommendation")
                             print(f"Node: {node_name}, State: {updated_state}")
                        else:
                            # This is a regular node's final output
                            print(f"Node: {node_name}, State: {updated_state}")
                            print()
                            await websocket.send_json({
                                "status": "node_complete",
                                "node": node_name,
                                "response": jsonable_encoder(updated_state)
                            })

            # After streaming, check if the graph is finished or waiting for feedback
            final_state = await graph.aget_state(config)
            if not final_state or not final_state.next:
                await websocket.send_json({"status": "finished", "response": "Conversation finished."})
                #TODO : 음 여기서 break 하고 다시 client 측에서 disconnect 버튼 누르고 다시 연결 한 뒤 메세지 보내야 다시 동작.
                break  # End the session
            else:
                await websocket.send_json({"status": "waiting_for_feedback", "response": "Please provide feedback or your next query."})

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


