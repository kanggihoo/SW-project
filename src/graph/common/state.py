from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import Field

from graph.model.graph_schemas import ClothSearch


# ======================================================================
# 그래프 전체 state 상태 정의
# ======================================================================
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    cloth_search: ClothSearch
    is_info_gathering_complete: bool
    product_id: str
    intent: str
    user_message: str

    # -----------------------------------------
    last_updated_fields: Annotated[list[str], Field(description='마지막으로 업데이트된 필드')]
    # --- Expert Loop Control State ---
    experts_to_run: Annotated[list[str], Field(description='실행할 전문가 목록')]
    current_expert: Annotated[str, Field(description='현재 실행중인 전문가')]
    # --- Result State ---
    expert_opinions: Annotated[str, Field(description='current_expert의 전문가 의견으로 해당 정보로 쿼리 분석 진행')]
    # search_result_offset: int = 0
