"""
정보 수집 노드를 위한 프롬프트 템플릿 관리
깔끔하고 체계적인 프롬프트 구성을 위한 모듈
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from agents.gather_info.models import UserProfile
from agents.gather_info.tools import SearchInfo


# 기본 시스템 프롬프트 템플릿
INFORMATION_GATHERING_SYSTEM_PROMPT = """당신은 의류 추천 전문가입니다. 

핵심 임무: 사용자와의 자연스러운 대화를 통해 의류 검색에 필요한 정보를 수집하는 것이며, 모든 필수 정보가 수집되면 SearchInfo 도구를 호출하세요.

필수 수집 정보:
- tpo: 언제 어느 상황에 입을 옷인지 (예: 봄 주말 데이트, 직장 회의, 친구 모임 등)
- style: 스타일 (캐주얼, 포멀, 스트릿, 미니멀 등)  
- color: 선호 색상

행동 원칙:
1. 개인화: 사용자 프로필을 적극 활용하여 맞춤형 질문과 제안을 하세요
2. 점진성: 한 번에 하나씩 자연스럽게 정보를 수집하세요
3. 유연성: 복합적인 의도("~만 빼고", "~와 어울리는")도 정확히 파악하세요
4. 적극성: 사용자가 막연한 답변을 할 경우 구체적인 선택지를 제안하세요
5. 반환값 : 
   - 모든 필수 정보가 수집되면 SearchInfo 도구호출하기 위한 인자값을 반환하세요.
   - 정보가 부족한 경우: 도구 호출하지 말고, 부족한 정보에 대해 사용자가 응답할 수 있도록 사용자에게 질문을 하세요

{user_profile_info}

{current_criteria_info}

# 최근 사용자 입력 메세지
{user_message}

대화 스타일: 친근하고 전문적이며, 패션에 대한 깊은 이해를 바탕으로 도움을 제공하세요."""


def build_information_gathering_prompt() -> ChatPromptTemplate:
    """정보 수집용 프롬프트 템플릿 생성"""
    return ChatPromptTemplate.from_messages([
        ("system", INFORMATION_GATHERING_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages")
    ])


def format_user_profile_info(user_profile: UserProfile) -> str:
    """유저 정보인 {user_profile_info} 포맷팅"""
    if not user_profile:
        return "사용자 프로필 정보: 없음"
    
    profile_info = f"""
사용자 프로필 정보:
- 선호 스타일: {user_profile.preferred_style or '없음'}
- 선호 색상: {', '.join(user_profile.preferred_colors) if user_profile.preferred_colors else '없음'}
- 기피 색상: {', '.join(user_profile.excluded_colors) if user_profile.excluded_colors else '없음'}
- 사이즈: {user_profile.size or '없음'}
이 정보를 활용하여 부족한 정보에 대한 개인화된 질문과 제안을 해주세요."""
    return profile_info.strip()


def format_current_criteria_info(criteria: SearchInfo) -> str:
    """현재 수집된 정보 상태를 포맷팅"""
    if not criteria:
        return "현재까지 수집된 정보: 없음"
    
    collected_info = []
    if criteria.tpo:
        collected_info.append(f"TPO: {criteria.tpo}")
    if criteria.style:
        collected_info.append(f"스타일: {criteria.style}")
    if criteria.color:
        collected_info.append(f"색상: {criteria.color}")
    if criteria.excluded_colors:
        collected_info.append(f"제외 색상: {', '.join(criteria.excluded_colors)}")
    
    missing_fields = criteria.get_missing_fields()
    status = "모든 필수 정보가 수집되었습니다! SearchInfo 도구를 호출하세요." if criteria.is_complete() else \
             f"필수 정보가 부족합니다. 부족한 정보를 사용자에게 질문하세요. \n 부족한 필수 정보: {', '.join(missing_fields)}"
    
    criteria_info = f""" 현재까지 수집된 정보: {chr(10).join(f"- {info}" for info in collected_info)} \n {status}"""
    
    return criteria_info.strip()


def format_prompt_variables(user_profile: UserProfile, criteria: SearchInfo , user_message: str) -> dict:
    """프롬프트 템플릿 변수들을 포맷팅하여 딕셔너리로 반환"""
    return {
        "user_profile_info": format_user_profile_info(user_profile),
        "current_criteria_info": format_current_criteria_info(criteria),
        "user_message": user_message
    }