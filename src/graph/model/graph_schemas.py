from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


# ======================================================================
# 노드 이름 Enum 정의
# ======================================================================
class NodeName(StrEnum):
    CLASSIFY_INTENT = 'classify_intent'
    RECLASSIFY_INTENT = 'reclassify_intent'
    HANDLE_INAPPROPRIATE = 'handle_inappropriate'
    CHATBOT = 'chatbot'
    INFO_QA = 'info_qa'
    UNCLEAR = 'unclear'
    INAPPROPRIATE_QUERY = 'inappropriate_query'
    SEARCH_REFINEMENT = 'search_refinement'
    DIRECT_SEARCH = 'direct_search'

    PRODUCT_INFO_AGENT = 'product_info_agent'
    INFORMATION_GATHERING = 'information_gathering'
    SEARCH_NODE = 'search_node'
    INFORMATION_UPDATE = 'information_update'

    POP_NEXT_EXPERT = 'pop_next_expert'
    RUN_EXPERT_EVALUATION = 'run_expert_evaluation'
    QUERY_ANALYSIS = 'query_analysis'
    VECTOR_SEARCH = 'vector_search'
    SHOW_NEXT_RESULTS = 'show_next_results'


# ======================================================================
# pydnatic 모델
# ======================================================================
class ClothSearch(BaseModel):
    """사용자의 의류 검색 요청에 대한 정보를 추출합니다."""

    tpo: str = Field(description='TPO(시간, 장소, 상황)')
    color: str = Field(description='색상')
    style: str = Field(description='스타일')


class UserIntent(BaseModel):
    """
    사용자 메시지의 핵심 의도를 6가지 유형 중 하나로 분류합니다.
    - direct_search: 특정 의류를 찾거나 구매하려는 명확한 요청.
    - info_qa: 의류 관련 정보, 트렌드, 용어 등에 대한 질문.
    - search_refinement: 이미 검색된 결과에 대한 수정 또는 구체화 요청.
    - chatbot: 의류와 관련 없는 일상 대화.
    - inappropriate_query: 성적, 폭력적, 비윤리적인 내용의 부적절한 질문.
    - unclear: 위 다섯 가지로 명확하게 분류하기 어려운 모호한 경우.
    """

    intent: Literal[
        NodeName.DIRECT_SEARCH, NodeName.INFO_QA, NodeName.SEARCH_REFINEMENT, NodeName.CHATBOT, NodeName.INAPPROPRIATE_QUERY, NodeName.UNCLEAR
    ] = Field(description='사용자 발화의 핵심 의도를 분류한 결과입니다.')
