from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from agents.gather_info.models import UserProfile
from agents.gather_info.tools import SearchInfo
from langgraph.graph import add_messages


class ConversationState(TypedDict):
    """
    정보_수집 노드의 상태
    문서에 명시된 '읽기 → 처리 → 쓰기' 사이클을 위한 구조
    """
    # 대화 메시지 목록 - 점진적으로 누적
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 검색 조건 - 사용자 입력에 따라 점진적으로 완성
    search_info: SearchInfo
    
    # 사용자 프로필 - 개인화된 질문과 제안을 위한 정보
    user_profile: Optional[UserProfile]
    
    # 현재 처리 중인 단계 - 디버깅과 흐름 제어를 위한 정보
    current_step: str

    is_info_gathering_complete: bool = False


