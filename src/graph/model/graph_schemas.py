from typing import Literal

from pydantic import BaseModel, Field

from graph.constants import IntentTypes


# ======================================================================
# pydnatic 모델
# ======================================================================
class ClothSearch(BaseModel):
    """Extracts structured information about the clothing a user is looking for."""

    tpo: str | None = Field(
        default=None,
        description='Place, and Occasion for wearing the clothes.',
    )
    color: str | None = Field(
        default=None,
        description='The desired color of the clothing.',
    )
    style: str | None = Field(
        default=None,
        description='The desired style, type, or category of the clothing.',
    )


class UserIntent(BaseModel):
    """
    Classifies the user's core intent into one of six predefined categories.
    - direct_search: 특정 의류를 찾거나 구매하려는 명확한 요청.
    - info_qa: 의류 관련 정보, 트렌드, 용어 등에 대한 질문.
    - search_refinement: 이미 검색된 결과에 대한 수정 또는 구체화 요청.
    - chatbot: 의류와 관련 없는 일상 대화.
    - inappropriate_query: 성적, 폭력적, 비윤리적인 내용의 부적절한 질문.
    - unclear: 위 다섯 가지로 명확하게 분류하기 어려운 모호한 경우.
    """

    intent: Literal[
        IntentTypes.DIRECT_SEARCH,
        IntentTypes.INFO_QA,
        IntentTypes.SEARCH_REFINEMENT,
        IntentTypes.CHATBOT,
        IntentTypes.INAPPROPRIATE_QUERY,
        IntentTypes.UNCLEAR,
    ] = Field(
        description="The final classification of the user's intent. Must be one of: "
        "direct_search', 'info_qa', 'search_refinement', 'chatbot', "
        "inappropriate_query', or 'unclear'."
    )
