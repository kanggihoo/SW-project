from langgraph.graph.message import MessagesState
from typing import Annotated , Any


from langgraph.graph import StateGraph , END , START
from langgraph.checkpoint.memory import MemorySaver

from .edges import build_graph
# import uuid # No longer needed here


builder = build_graph()
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# thread_id = str(uuid.uuid4())
# config = {
#     "configurable": {
#         "thread_id": thread_id,
#         "llm_model" : {
#             "model": "gemini-1.5-flash",
#             "prompt_template": "You are a helpful assistant that recommends clothing items based on the user's query. ",
#         },
#         "k": 3
#     },
#     "tags" : ["tmp" , "test"],
#     "run_name" : "test_run"
    
# }
# # 인터럽트 걸리기 전까지 실행
# for chunk in graph.stream({"user_query": "I want to buy a shirt"} , stream_mode="updates" , config=config , interrupt_before=["wait_for_user_feedback_node"]):
#     print(chunk)

# print("인터럽트 걸림")    
# while 1:
#     current_graph_state = graph.get_state(config)
    
#     if not current_graph_state.next:
#         print("반복 종료 ")
#         break
    
#     user_feedback = input("Press Enter to continue...")
    
#     graph.update_state(config , {"user_feedback": user_feedback})
#     for chunk in graph.stream(None , stream_mode="updates" , config=config , interrupt_before=["wait_for_user_feedback_node"]):
#         for node_name , updated_state in chunk.items():
#             if updated_state is not None:
#                 print(f"Node: {node_name} , State: {updated_state}")
        

# print("그래프 종료!! ")
    
    
            
    
    



