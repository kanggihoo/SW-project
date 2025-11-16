from graph.common.state import State
from graph.constants import StateName


def custom_pre_model_node(state: State):
    """마지막 메시지의 내용을 수정하는 노드"""

    last_message = state['messages'][-1]
    product_id = state[StateName.PRODUCT_ID.value]

    new_message = f"""
    **Product ID:** `{product_id}`
    **User's Question:** "{last_message.content}"
    Please analyze the user's question, use the available tools to find the correct information, and provide a helpful answer in Korean.
    """
    modified = last_message.model_copy(update={'content': new_message})
    # 새로운 메시지로 교체 (직접 수정 방식)

    return {'messages': [modified]}
