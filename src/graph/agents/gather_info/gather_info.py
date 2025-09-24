"""
정보_수집 그래프 구성 및 컴파일
문서 gather_info.md에 명시된 그래프 구조 구현

그래프 흐름:
1. load_user_profile: 사용자 프로필 로드
2. information_gathering: 정보 수집 및 LLM 처리 (반복 가능)
3. 조건부 라우팅: 완료 시 END, 계속 시 대기

핵심 특징:
- 점진적 상태 업데이트 사이클 (읽기 → 처리 → 쓰기)
- 개인화된 대화 (사용자 프로필 활용)
- 복합 의도 파악 (제외 조건, 복합 요구사항)
- 적극적 제안 기능 (막연한 답변 시 선택지 제공)
"""

import os
from typing import Optional
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
import httpx
from agents.gather_info.state import ConversationState


from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.gather_info.tools import SearchInfo
from agents.gather_info.state import ConversationState
from agents.gather_info.prompt import build_information_gathering_prompt, format_prompt_variables

def next_node(state: ConversationState) -> Dict[str, Any]:
    """
    다음 노드로 이동
    """
    print("🔄 다음 노드로 이동")
    return ConversationState(current_step="next_node")

def information_gathering_node(state: ConversationState) -> Dict[str, Any]:
    """
    문서에 명시된 '읽기 → 처리 → 쓰기' 사이클 구현:
    - 읽기: 현재 상태에서 대화 내역, 검색 조건, 사용자 프로필 읽기
    - 처리: LLM이 도구 호출을 통해 다음 행동 결정 (질문 or 검색)
    - 쓰기: 도구 호출 결과에 따라 상태 업데이트
    """
    print("🧠 정보 수집 및 분석 중...")
    
    # 1단계: 읽기 - 현재 상태 읽기
    current_messages = state.get("messages", [])
    current_criteria = state.get("search_criteria", SearchInfo())
    user_profile = state.get("user_profile")
    user_message = state.get("user_message", "")
    
    # 2단계: 처리 - LLM에게 상황 전달 및 도구 호출을 통한 다음 행동 결정
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.3)
    llm_with_tools = llm.bind_tools([SearchInfo])
    
    # 프롬프트 템플릿 생성 및 변수 포맷팅
    prompt = build_information_gathering_prompt()
    prompt_variables = format_prompt_variables(user_profile, current_criteria, user_message)
    print("prompt_variables: ", prompt_variables)
    # 체인 구성
    chain = prompt | llm_with_tools
    
    # LLM 호출
    ai_response = chain.invoke({
        "messages": current_messages,
        **prompt_variables
    })
    
    # 3단계: 쓰기 - 도구 호출 결과에 따라 상태 업데이트
    updated_state = _process_tool_call_response(ai_response, current_criteria)
    print("updated_state: ", updated_state)
    return ConversationState(**updated_state)



def _process_tool_call_response(ai_response, current_criteria: SearchInfo) -> Dict[str, Any]:
    """
    도구 호출 응답을 처리하여 상태 업데이트 정보 반환
    """

    if hasattr(ai_response, 'tool_calls') and ai_response.tool_calls:
        return {"search_info": ai_response.tool_calls[0]['args'] , "is_info_gathering_complete": True}
    else:
        return {"messages": [ai_response.content]}



def should_continue_gathering(state: ConversationState) -> str:
    """
    조건부 엣지: 도구 호출 타입에 따라 다음 단계 결정
    
    Returns:
        "complete": SearchInfo 도구 호출됨, 검색 단계로 이동
        "continue": AskQuestionAndUpdateState 호출됨, 계속 대화 필요
    """
    if state.get("is_info_gathering_complete"):
        return "complete"
    else:
        return "continue"



def build_graph(http_session: httpx.AsyncClient):
    """
    정보_수집 그래프 생성 및 컴파일
    
    Args:
        checkpointer: 상태 저장을 위한 체크포인터 (옵션)
    
    Returns:
        compiled_graph: 컴파일된 LangGraph 객체
    """
    print("🔧 정보 수집 그래프 구성 중...")
    
    # 그래프 초기화
    workflow = StateGraph(ConversationState)
    
    # 노드 추가
    
    workflow.add_node("gather_info", information_gathering_node)
    workflow.add_node("next_node", next_node)
    workflow.set_entry_point("gather_info")
    
    # 조건부 엣지: 정보 수집 완료 여부에 따른 분기
    workflow.add_conditional_edges(
        "gather_info",
        should_continue_gathering,
        {
            "complete": "next_node",     # 모든 정보 수집 완료 → 종료 (다음 노드로 이동)
            "continue": END  # 더 수집 필요 → 다시 정보 수집
        }
    )

    
    return workflow.compile()


