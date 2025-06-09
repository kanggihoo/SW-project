from langgraph.graph.message import MessagesState
from typing import Any

class ClothingRAGState(MessagesState):
    user_query: str
    embedded_query: list[float] | None
    candidate_items: list[dict[str, Any]] | None
    candidate_items_with_metadata: list[dict[str, Any]] | None
    external_info: dict[str, Any] | None   
    ranked_candidates: list[dict[str, Any]] | None
    final_recommendation: dict[str, Any] | None
    user_feedback: str | None # e.g., "rerank_cheaper", "rerank_review", "restart", "accept"
    # error_message: Annotated[str, ""]
    