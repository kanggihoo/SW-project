# LangGraph 기반 의도 분류기 설계 문서

이 시스템은 크게 **세 가지 주요 흐름**으로 나뉩니다.

1.  **제품 ID 기반 검색**: 사용자가 명확한 제품 ID를 제공하면, `product_info_agent` 노드로 직접 라우팅되어 해당 제품에 대한 정보를 제공합니다.
2.  **자연어 기반 검색**: 제품 ID가 없는 경우, **사용자의 의도를 먼저 파악하고, 의도에 따라 적절한 경로로 분기**하여 처리합니다.
3.  **템플릿 기반 검색**: 사용자가 "주말 데이트룩 찾아줘"와 같이 미리 만들어진 버튼/템플릿을 클릭하면, **의도 분류 과정을 생략하고 즉시 정보 수정(`information_update_node`) 단계로 진입**하여 빠른 사용자 경험을 제공합니다.

## 1. 사용자 의도 파악: 지능형 2단계 분류 전략

의도 분류기의 핵심 목표는 **속도와 정확성의 균형**을 맞추는 것입니다. 이를 위해 다음과 같은 지능적인 2단계 분류 전략을 사용합니다.

### 1단계: 상태 기반 동적 프롬프트 최적화

기존에는 단일 프롬프트로 모든 상황을 처리하려다 보니, 정보 수집이 완료된 상태(`is_info_gathering_complete=True`)에서 검색 조건을 수정하려는 입력("파란색은 어때?")을 `info_qa`(정보 질문)로 오분류하는 문제가 있었습니다. 원인은 LLM이 **어떤 조건으로 검색이 완료되었는지(`cloth_search`의 현재 상태)라는 핵심 문맥을 몰랐기 때문**입니다.

이 문제를 해결하기 위해, **대화의 상태(`is_info_gathering_complete`)에 따라 두 개의 고도로 최적화된 프롬프트를 동적으로 선택**하도록 시스템을 전면 개편했습니다.

1.  **`intent_prompt_gathering` (정보 수집 단계)**
    *   **사용 시점**: `is_info_gathering_complete`가 `False`일 때.
    *   **특징**: `search_refinement`(검색 조건 수정) 의도를 선택지에서 아예 제외합니다. LLM은 `direct_search`, `info_qa` 등 새로운 요청에 해당하는 5가지 의도 중에서만 선택해야 하므로, 혼동의 여지가 원천적으로 차단됩니다.

2.  **`intent_prompt_refinement` (검색 완료/수정 단계)**
    *   **사용 시점**: `is_info_gathering_complete`가 `True`일 때.
    *   **특징**: `direct_search`를 제외하고 `search_refinement`를 강조하며, **`{cloth_search}` 문맥을 제공**하여 정확한 판단을 유도합니다.
    *   **핵심 개선**: 프롬프트에 현재 검색 조건인 **`{cloth_search}` 변수를 명시적으로 주입**합니다. 이를 통해 LLM은 '현재 이런 조건으로 검색 중인데, 사용자가 "파란색"이라고 말했구나. 이것은 `color` 필드를 수정하려는 `search_refinement` 의도일 것이다'라고 정확하게 추론할 수 있게 됩니다.

이러한 동적 프롬프트 전략은 LLM의 인지 부하를 줄이고, 각 상황에 맞는 명확한 문맥을 제공하여 분류 정확도를 극대화합니다.

### 2단계: 심층 재분류 (Contextual Fallback)

만약 1단계 동적 프롬프트 분류 시도에서 의도가 불분명하다고(`unclear`) 판단될 경우, 분류기는 자동으로 이전 대화 기록을 포함하여 다시 한번 분석을 수행합니다.

-   이때, **사용자 메시지의 길이에 따라 동적으로 컨텍스트의 양을 조절**합니다. (예: "별로"와 같은 초단답에는 더 많은 대화 기록을, 긴 문장에는 더 적은 기록을 참고)
-   만약 재분류 시도 후에도 의도가 여전히 `unclear` 하다면, 시스템은 이를 포기하지 않고 **의도를 `chatbot`으로 변경하고 `is_unclear_fallback` 플래그를 활성화**합니다. 이를 통해 `chatbot` 노드가 사용자에게 직접 의도를 물어보는 방식으로 대화를 자연스럽게 이어나갑니다.

## 2. 의도 분류 모델 정의 (Pydantic)

LLM이 일관된 형식의 결과만 반환하도록 강제하기 위해 Pydantic 모델을 사용합니다. 특히 `Literal` 타입을 활용하여, **미리 정의된 6가지 의도 중 하나만 반환하도록 제**한합니다. (실제 프롬프트에서는 이 중 일부만 선택지로 제시될 수 있습니다.)

```python
from pydantic import BaseModel, Field
from typing import Literal
from graph.constants import IntentTypes

class UserIntent(BaseModel):
    """
    사용자 메시지의 핵심 의도를 6가지 유형 중 하나로 분류합니다.

    - direct_search: 특정 의류를 찾거나 구매하려는 명확한 요청.
    - info_qa: 의류 관련 정보, 트렌드, 용어 등에 대한 질문.
    - search_refinement: 이미 검색된 결과에 대한 수정 또는 구체화 요청.
    - chatbot: 의류와 관련 없는 일상적인 대화.
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
        description="사용자 발화의 핵심 의도를 6가지 중 하나로 분류한 결과입니다."
    )
```

## 3. 의도 분류기 시스템 프롬프트 설계

분류기의 핵심은 상태에 따라 동적으로 선택되는 두 개의 시스템 프롬프트입니다.

### 프롬프트 1: `INTENT_PROMPT_GATHERING_SYSTEM` (정보 수집 중)

`is_info_gathering_complete`가 `False`일 때 사용되며, `search_refinement`가 제외된 5가지 선택지만을 제시하여 LLM이 명확하게 초기 의도를 파악하도록 합니다.

```python
# From: src/graph/prompt/intent_classifier.py

INTENT_PROMPT_GATHERING_SYSTEM = """
You are an expert AI assistant that analyzes a user's message to classify their intent.
You must respond ONLY in the `UserIntent` Pydantic model format and nothing else.

[Current Conversation State]
- `information gathering complete`: False (You are in the initial information gathering phase)

[Classification Criteria]
Your task is to classify the user's intent into one of the following 5 types.
At this stage, the user is starting a new search or asking a general question.

1. `direct_search`: The user has a clear intention to find, get recommendations for, or purchase clothing. (e.g., "Find me a shirt", "for a weekend date")
2. `info_qa`: The user is asking for general information about fashion, such as trends, terms, or styling tips. (e.g., "What's in style?", "How do I wash jeans?")
3. `chatbot`: The user is engaging in casual, everyday conversation unrelated to clothing.
4. `inappropriate_query`: The user's message contains sexual, violent, unethical, or offensive content.
5. `unclear`: The user's intent is ambiguous and cannot be confidently placed in any of the other categories.
"""
```

### 프롬프트 2: `INTENT_PROMPT_REFINEMENT_SYSTEM` (검색 완료 후)

`is_info_gathering_complete`가 `True`일 때 사용됩니다. `direct_search`를 제외하고 `search_refinement`를 강조하며, **`{cloth_search}` 문맥을 제공**하여 정확한 판단을 유도합니다.

```python
# From: src/graph/prompt/intent_classifier.py

INTENT_PROMPT_REFINEMENT_SYSTEM = """
You are an expert AI assistant that analyzes a user's feedback to classify their intent.
You must respond ONLY in the `UserIntent` Pydantic model format and nothing else.

[Current Conversation State]
- `information gathering complete`: True
- `current_search_criteria`: {cloth_search}

[Classification Criteria]
Your task is to classify the user's intent based on the existing search.
Choose from one of the following 5 types:

1. `search_refinement`: The user is requesting to **modify, add to, or change** the `current_search_criteria`. **This is the most likely intent** for any new clothing-related request.
    - (e.g., "What about blue?", "Change style to formal", "Show me something else")
2. `info_qa`: The user is asking for general information about fashion, **clearly unrelated** to the `current_search_criteria`. (e.g., "How do I wash jeans?", "What's the weather?")
3. `chatbot`: The user is engaging in casual, everyday conversation.
4. `inappropriate_query`: The user's message contains sexual, violent, unethical, or offensive content.
5. `unclear`: The user's intent is ambiguous and cannot be confidently placed in any of the other categories.
"""
```

## 4. 의도별 후속 처리 노드 설계

의도가 분류된 후, 각 상황에 맞는 전문화된 노드(에이전트)가 응답을 처리합니다.

### 💬 `chat bot` (일상 대화 및 의도 명확화) 처리 노드

`chatbot` 노드는 의류 추천 시스템의 핵심 기능(검색, 정보 제공) 외의 모든 대화를 처리하는 "만능 게이트웨이" 역할을 수행합니다.
이 노드의 목적은 단순히 잡담(chatbot)에 응대하는 것이 아니라, 어떤 상황에서든 사용자를 다시 핵심 기능인 '의류 검색'으로 자연스럽게 유도하는 것입니다.
또한, `intent_classify_node`가 사용자의 의도를 1, 2차에 걸쳐 분석했음에도 불구하고 `unclear`(불명확)로 판단한 경우, 이 모호함을 해결하는 최종 폴백(Fallback) 처리라는 매우 중요한 임무도 맡고 있습니다.

#### 설계 원칙: "명확한 4-Way 분기"

`chatbot` 노드는 LLM의 신뢰성과 일관성을 확보하기 위해, 하나의 거대하고 복잡한 프롬프트를 사용하지 않습니다.
대신, `chatbot` 노드 함수(Python 코드)가 먼저 `State`를 확인하여 현재 상황을 4가지 시나리오 중 하나로 명확하게 분류한 뒤, 각 상황에 100% 최적화된 4개의 개별 프롬프트(`ChatPromptTemplate`) 중 하나를 동적으로 호출합니다.

이 분류는 두 가지 핵심 `State` 값을 기준으로 이루어집니다.

- **`is_gathering_complete` (정보 수집 완료 여부)**: 사용자가 검색에 필요한 정보(TPO, 스타일 등)를 모두 입력했는지(`True`), 아니면 아직 입력 중인지(`False`)를 나타냅니다.
- **`is_unclear_fallback` (의도 불명확 여부)**: `intent_classify_node`가 의도 분류에 실패하여 이 노드를 호출했는지(`True`), 아니면 의도 분류 결과가 명확히 '일상 대화(chatbot)'였는지(`False`)를 나타냅니다.

이 두 변수는 다음과 같은 2x2 매트릭스를 구성하여 4가지 고유한 상황을 정의합니다.

| | `is_gathering_complete: False` (정보 수집 중) | `is_gathering_complete: True` (검색 완료 후) |
| :--- | :--- | :--- |
| **`is_unclear_fallback: False`<br>(일반 대화)** | **상황 1: GATHERING_CHATBOT** | **상황 2: SEARCH_READY_CHATBOT** |
| **`is_unclear_fallback: True`<br>(의도 불명확)** | **상황 3: GATHERING_UNCLEAR** | **상황 4: SEARCH_READY_UNCLEAR** |

#### 4가지 상황별 동작 상세

##### 상황 1: GATHERING_CHATBOT (정보 수집 중 + 일반 대화)

- **발생 시점**: 사용자가 아직 검색 정보를 다 입력하지 않았는데(`missing_fields` 존재), 의류와 무관한 대화(예: "오늘 날씨 좋다")를 한 경우.
- **노드의 임무**:
    1. 사용자의 말에 친절하고 짧게 응대합니다.
    2. 즉시 대화의 초점을 '정보 수집'으로 되돌립니다.
    3. `missing_fields`에 남아있는 정보를 자연스럽게 다시 질문합니다.
- **예시 응답**: "정말 날씨 좋네요! 😊 계속해서 옷을 찾아볼까요? 데이트룩으로 찾으시는데, 혹시 선호하는 스타일이나 색상이 있으실까요?"

##### 상황 2: SEARCH_READY_CHATBOT (검색 완료 후 + 일반 대화)

- **발생 시점**: 사용자가 이미 검색 결과를 본 상태에서, 의류와 무관한 대화(예: "배고프다")를 한 경우.
- **노드의 임무**:
    1. 사용자의 말에 친절하게 응대합니다.
    2. 즉시 대화의 초점을 '검색 결과 피드백'으로 되돌립니다.
    3. 사용자의 다음 행동(다른 코디 보기, 조건 변경)을 유도하여 `information_update_node`로 연결될 수 있도록 돕습니다.
- **예시 응답**: "맛있는 점심 드세요! 🍔 혹시 방금 보여드린 코디는 어떠셨나요? 마음에 드는 상품이 없었다면, 다른 코디를 더 보여드릴까요? 아니면 스타일이나 색상을 변경해서 다시 찾아볼까요?"

##### 상황 3: GATHERING_UNCLEAR (정보 수집 중 + 의도 불명확)

- **발생 시점**: 사용자가 아직 검색 정보를 다 입력하지 않았는데, 모호한 입력(예: "음 그냥...")을 하여 `intent_classify_node`가 분류에 실패한 경우.
- **노드의 임무**:
    1. "이해하지 못했습니다"라는 부정적인 응답을 절대 하지 않습니다.
    2. 잡담 응대를 생략하고, 사용자의 의도를 명확히 하는 '가이드' 질문을 즉시 제시합니다.
    3. 가장 가능성이 높은 선택지(A: `missing_fields` 정보 입력, B: 기타 도움 요청)를 제시합니다.
- **예시 응답**: "알겠습니다. 계속해서 옷을 추천해 드리기 위해, 혹시 찾으시는 옷의 스타일이나 색상을 말씀하려던 것이었나요? 아니면 다른 도움이 필요하신가요?"

##### 상황 4: SEARCH_READY_UNCLEAR (검색 완료 후 + 의도 불명확)

- **발생 시점**: 사용자가 이미 검색 결과를 본 상태에서, 모호한 입력(예: "파란색", "별로")을 하여 `intent_classify_node`가 분류에 실패한 경우.
- **노드의 임무**:
    1. "이해하지 못했습니다"라는 부정적인 응답을 절대 하지 않습니다.
    2. 사용자의 모호한 입력을 문맥(검색 결과)에 맞게 해석하여, 가장 가능성이 높은 두 가지 '검색 행동'을 선택지로 제시합니다.
- **예시 응답**: (사용자가 "파란색"이라고 입력한 경우) "혹시 '파란색'으로 검색 조건을 변경해서 다시 찾아드릴까요? 아니면 지금 조건으로 다른 코디를 더 보여드릴까요?"

#### 결론

이러한 4-Way 분기 설계는 `chatbot` 노드가 단순한 잡담 응답기를 넘어, 어떤 대화의 갈림길이나 막다른 길에서도 사용자를 다시 올바른 경로로 안내하는 '지능형 가이드' 역할을 수행하도록 보장합니다. 이를 통해 LLM 응답의 신뢰도를 높이고 훨씬 더 매끄러운 사용자 경험(UX)을 제공합니다.

### 🧠 `info_qa` (의류 정보 질문) 처리 노드

- **목표**: 전문적인 정보 제공 및 Tool(웹 검색 등) 활용
- **시스템 프롬프트**:
    
    > 너는 패션 트렌드, 스타일링, 의류 관리에 대한 모든 것을 알고 있는 패션 전문가다. **사용자의 의류 관련 정보 질문에 대해 명확하고 전문적인 답변을 제공**해야 한다.
    너는 최신 정보를 찾기 위해 **[웹 검색 도구]**를 사용할 수 있다. 사용자가 트렌드에 대해 물으면, 반드시 웹 검색을 통해 가장 최신 정보를 찾아서 답변해라.
    답변 후에는 "또 궁금한 패션 정보가 있으신가요?" 또는 "이제 원하시는 옷을 찾아드릴까요?" 와 같이 다음 행동을 제안하여 대화를 이끌어라.
    > 

# 핵심 구성 요소 분석

## 1. State

`State` TypedDict는 그래프의 모든 노드가 공유하는 "중앙 메모리" 역할을 합니다.

- `messages`: 전체 대화 기록을 저장하여 문맥을 유지합니다.
- `cloth_search`: `ClothSearch` Pydantic 모델 인스턴스로, 검색에 필요한 정보(TPO, 색상, 스타일)를 점진적으로 채워나갑니다.
- `is_info_gathering_complete`: 정보 수집이 완료되었는지 여부를 나타내는 플래그입니다. 라우터의 핵심적인 분기 조건이 됩니다.
- `product_id`: 사용자가 제공한 제품 ID를 저장합니다. `master_router`의 첫 번째 분기 조건으로 사용됩니다.
- `intent`: 분류된 사용자의 의도를 저장합니다.
- `user_message`: 현재 사용자의 입력 메시지를 저장합니다.
- `user_name`: 사용자 이름 정보입니다.
- `is_predefined_template`: 사용자가 미리 정의된 템플릿을 클릭했는지 여부를 나타냅니다. `master_router`의 핵심 분기 조건 중 하나입니다.
- `is_unclear_fallback`: `unclear` 의도가 `chatbot`으로 넘어왔는지 여부를 나타내는 플래그입니다. `chatbot` 노드의 핵심 분기 조건입니다.

```python
# 그래프 state
class State(TypedDict):
    # 대화 기록 (사용자와 AI의 메시지)
    messages: Annotated[list[BaseMessage], add_messages]
    # 사용자가 찾고 있는 의류 정보 (TPO, 색상, 스타일)
    cloth_search: ClothSearch
    # 의류 정보를 모두 수집했는지 여부 (True/False)
    is_info_gathering_complete: bool
    # (미사용) 특정 상품 ID
    product_id: str
    # LLM이 분석한 사용자의 핵심 의도
    intent: str
    # 사용자가 마지막으로 입력한 메시지
    user_message: str
    # 사용자 이름
    user_name: str
    # 미리 정의된 템플릿 클릭 여부
    is_predefined_template: bool
    # 정보 업데이트 시 어떤 필드가 변경되었는지 기록
    last_updated_fields: Annotated[list[str], Field(description='마지막으로 업데이트된 필드')]
    # UNCLEAR 상황에서 chatbot으로 폴백되었는지 여부
    is_unclear_fallback: Annotated[bool, Field(description='UNCLEAR 상황에서 chatbot으로 폴백되었는지 여부', default=False)]
    
    # --- Expert Loop 관련 상태 (현재 그래프에서는 미사용) ---
    experts_to_run: Annotated[list[str], Field(description='실행할 전문가 목록')]
    current_expert: Annotated[str, Field(description='현재 실행중인 전문가')]
    expert_opinions: Annotated[str, Field(description='current_expert의 전문가 의견')]
```

## 2. 라우터 (Routers)

- `master_router`: 시스템의 가장 첫 관문입니다. `State`에 담긴 정보를 바탕으로 다음 세 가지 경로 중 하나를 결정합니다.
    1. `product_id`가 있으면 → `product_info_agent`로 라우팅합니다.
    2. `is_predefined_template`이 `True`이면(사용자가 템플릿을 클릭한 경우) → `prepare_template_search_node`로 라우팅하여 검색 준비를 시작합니다.
    3. 위 두 가지에 해당하지 않으면 → `classify_intent`로 보내 일반적인 의도 분석을 시작합니다.
  ```python
  def master_router(state: State):
      logger.debug('---\n--- 라우팅: master_router ---')
      if state.get(StateName.PRODUCT_ID):
          logger.debug('- 라우팅: product_info_agent_node로 이동')
          return RouterReturnNames.PRODUCT_INFO_AGENT
      elif state.get(StateName.IS_PREDEFINED_TEMPLATE):
          logger.debug('- 라우팅: prepare_template_search_node로 이동 (템플릿 처리 준비)')
          return RouterReturnNames.PREPARE_TEMPLATE_SEARCH
      else:
          logger.debug('- 라우팅: classify_intent_node로 이동')
          return RouterReturnNames.CLASSIFY_INTENT
  ```
- `route_after_classification`: `classify_intent` 노드에서 분류된 `intent` 값을 기반으로, 정보 수집, 부적절한 질문 처리, 챗봇 등 다음 단계로 작업을 분배합니다. **LLM이 실수를 하더라도 문맥에 맞게 복구해주는 2-Way 안전망** 역할을 겸합니다.
    - **안전망 로직 1**: `is_info_gathering_complete=False`일 때 `search_refinement` 의도가 감지되면, 이를 `direct_search`와 동일하게 취급하여 `information_gathering_node`로 자동 보정 라우팅합니다.
    - **안전망 로직 2**: `is_info_gathering_complete=True`일 때 `direct_search` 의도가 감지되면, 이를 `search_refinement`와 동일하게 취급하여 `information_update_node`로 자동 보정 라우팅합니다.
    - 이 "지능형 복구" 로직 덕분에, LLM이 최적화된 프롬프트의 지시를 따르지 않더라도 대화 흐름이 끊기지 않고 매우 견고하게 유지됩니다.

```python
def route_after_classification(state: State):
    """의도 분류 결과에 따라 다음 노드를 결정하고, LLM의 실수를 보정합니다."""
    intent = state[StateName.INTENT.value]
    is_info_gathering_complete = state.get(StateName.IS_INFO_GATHERING_COMPLETE, False)

    # 안전망 1: 정보 수집 중 search_refinement가 감지되면 -> 정보 수집으로 보정
    if not is_info_gathering_complete and intent in [IntentTypes.DIRECT_SEARCH, IntentTypes.SEARCH_REFINEMENT]:
        if intent == IntentTypes.SEARCH_REFINEMENT:
            logger.warning(f'- 로직 보정: Gathering 상태에서 {intent}가 감지되어 {RouterReturnNames.INFORMATION_GATHERING}(으)로 보정 라우팅합니다.')
        return RouterReturnNames.INFORMATION_GATHERING

    # 안전망 2: 정보 수집 완료 후 direct_search가 감지되면 -> 정보 수정으로 보정
    elif is_info_gathering_complete and intent in [IntentTypes.SEARCH_REFINEMENT, IntentTypes.DIRECT_SEARCH]:
        if intent == IntentTypes.DIRECT_SEARCH:
            logger.warning(
                f'- 로직 보정: Gathering 완료 상태에서 {intent}가 감지되어 {RouterReturnNames.INFORMATION_UPDATE}(으)로 보정 라우팅합니다.'
            )
        return RouterReturnNames.INFORMATION_UPDATE

    elif intent == IntentTypes.INAPPROPRIATE_QUERY:
        logger.debug('- 라우팅: handle_inappropriate_node로 이동')
        return RouterReturnNames.HANDLE_INAPPROPRIATE
    elif intent == IntentTypes.CHATBOT:
        logger.debug('- 라우팅: chatbot_node로 이동')
        return RouterReturnNames.CHATBOT
    elif intent == IntentTypes.INFO_QA:
        logger.debug('- 라우팅: info_qa_node로 이동')
        return RouterReturnNames.INFO_QA
    else:  # unclear 또는 기타
        logger.info('- 라우팅: END (분류 실패 또는 추가 처리 불필요)')
        return END

```

- `route_after_gathering`: 정보 수집 노드(`information_gathering`) 실행 후, `is_info_gathering_complete` 상태를 확인하여 실제 검색(`search_node`)으로 나아갈지, 아니면 추가 정보를 요청하며 사용자 입력을 더 기다릴지 결정합니다.

```python
def route_after_gathering(state: State):
    """정보 수집 후 다음 노드를 결정"""
    logger.debug('\n--- 라우팅: route_after_gathering ---')
    if state.get(StateName.IS_INFO_GATHERING_COMPLETE):
        logger.debug('- 라우팅: search_node로 이동')
        return NodeName.SEARCH_NODE
    else:
        logger.debug('- 라우팅: END (추가 사용자 입력 대기)')
        return END

```
    

## 3. 노드 (Nodes)


- `intent_classify_node` : 사용자 질문에 대한 의도 파악 노드
  1.  `is_info_gathering_complete` 상태를 확인하여 `intent_prompt_gathering`과 `intent_prompt_refinement` 중 현재 상황에 최적화된 프롬프트를 동적으로 선택합니다.
  2.  만약 `refinement` 모드일 경우, 현재 검색 조건(`cloth_search`)을 프롬프트에 함께 주입하여 LLM에 더 명확한 문맥을 제공합니다.
  3.  선택된 프롬프트로 1차 의도 분류를 시도합니다.
  4.  만약 의도가 불분명(`unclear`)하면, 사용자 메시지 길이에 따라 동적으로 이전 대화 내용의 양을 조절하여 2차 심층 분류를 진행합니다. (이때도 상태에 맞는 프롬프트와 문맥이 사용됩니다.)
  5.  만약 2차 분류에서도 의도가 `unclear`하다면, 의도를 `chatbot`으로 강제하고 `is_unclear_fallback` 플래그를 `True`로 설정하여 `chatbot` 노드가 직접 사용자에게 의도를 명확히 하도록 유도합니다.
  6.  분류된 최종 의도(`intent`)를 State에 저장합니다.

- `information_gathering_node`: 검색 의도(`direct_search`)가 감지되었을 때 실행됩니다.
  1. LLM을 호출하여 사용자 메시지에서 TPO, 색상, 스타일 등의 정보를 **추출**합니다.
  2. 기존 `state.cloth_search`에 추출된 정보를 **업데이트**합니다.
  3. 모든 정보가 채워졌는지 **확인**합니다.
  4. **만약 부족한 정보가 있다면, 해당 정보를 묻는 질문을 LLM으로 생성하여 사용자에게 되돌려줍**니다.
   
- `information_update_node`:
  1. 정보 수집이 완료된 상태(`is_info_gathering_complete=True`)에서 사용자가 검색 조건을 수정(`search_refinement`)하거나 추가 검색(`direct_search`)을 요청할 때 호출됩니다.
  2. 혹은, 사용자가 미리 정의된 템플릿을 클릭했을 때 `prepare_template_search_node`를 거쳐 호출됩니다.
  3. LLM을 호출하여 기존 검색 조건과 사용자 메시지(혹은 템플릿 텍스트)를 분석해 변경/추가할 정보를 추출합니다.
  4. **(캐시 로직)** 만약 LLM이 정보 변경이 필요 없다고 판단하면(예: "다른 거 보여줘"), `last_updated_fields`에 `__SHOW_CACHED__` 플래그를 설정하여 `search_subgraph`가 새로운 검색 없이 다음 결과를 보여주도록 합니다.
  5. 수정된 `cloth_search`를 State에 반영하고 `search_node`로 이동합니다.

- `prepare_template_search_node`: 사용자가 템플릿 버튼을 클릭했을 때 `master_router`에 의해 호출되는 준비 노드입니다. `is_info_gathering_complete`를 `True`로 설정하고 `cloth_search`를 비어있는 모델로 초기화한 뒤, `information_update_node`로 제어를 넘겨 템플릿의 내용을 바탕으로 검색 정보를 채우게 합니다.

- `search_node`: 모든 정보 수집이 완료되었을 때 최종적으로 실행되는 노드입니다. 현재는 플레이스홀더(Placeholder)이지만, 향후 이 노드에서 실제 벡터 기반 이미지 검색 로직이 실행될 것입니다.
- `handle_inappropriate_node`: 사용자의 입력이 성적, 폭력적, 비윤리적, 모욕적인 내용에 해당할 경우, 미리 준비된 정중한 거절 메시지(하드코딩된 응답)를 반환하여 안전한 대화 환경을 유지합니다.
- `chatbot_node`: 시스템의 핵심 기능 외의 모든 대화를 처리하는 게이트웨이입니다. `is_gathering_complete`와 `is_unclear_fallback` 상태를 조합하여 4가지 시나리오(정보 수집 중 잡담, 검색 후 잡담, 정보 수집 중 의도 불명확, 검색 후 의도 불명확)에 맞춰 동적으로 대응하며, 사용자를 항상 핵심 기능으로 유도하거나 모호함을 해결합니다.
- `info_qa_node`: 패션 전문가로서 사용자의 정보성 질문에 답변합니다. 최신 트렌드, 스타일링 팁, 의류 관리법 등에 대해 웹 검색과 같은 도구를 사용하여 정확하고 전문적인 정보를 제공합니다. 답변 후에는 "또 궁금한 점이 있으신가요?"처럼 다음 행동을 제안하여 대화를 주도적으로 이끌어 나갑니다. 또한, 검색 후 사용자의 피드백을 처리하고 재검색으로 연결하는 중요한 역할을 담당할 수 있습니다.
- `product_info_agent`: 제품 ID를 기반으로 정보를 조회하는 에이전트입니다. 데이터베이스 조회나 API 호출과 같은 도구를 사용하여 특정 제품 정보를 가져오는 역할을 수행할 수 있습니다.

## 4. pydantic model
- langgraph 특정 노드에서의 llm의 구조화된 출력을 위해 사용되는 pydantic 모델
```python
class ClothSearch(BaseModel):
    """사용자의 의류 검색 요청에 대한 정보를 추출합니다."""

    tpo: str | None = Field(default=None, description='TPO(시간, 장소, 상황)')
    color: str | None = Field(default=None, description='색상')
    style: str | None = Field(default=None, description='스타일')


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
        IntentTypes.DIRECT_SEARCH,
        IntentTypes.INFO_QA,
        IntentTypes.SEARCH_REFINEMENT,
        IntentTypes.CHATBOT,
        IntentTypes.INAPPROPRIATE_QUERY,
        IntentTypes.UNCLEAR,
    ] = Field(description='사용자 발화의 핵심 의도를 분류한 결과입니다.')

```

## 5. langgraph_enum
- 직접 문자열로 하드코딩을 피하기 위한 StrEnum 적용
```python
from enum import StrEnum

class IntentTypes(StrEnum):
    """Intent type"""

    DIRECT_SEARCH = 'direct_search'
    INFO_QA = 'info_qa'
    SEARCH_REFINEMENT = 'search_refinement'
    CHATBOT = 'chatbot'
    INAPPROPRIATE_QUERY = 'inappropriate_query'
    UNCLEAR = 'unclear'

class NodeName(StrEnum):
    # 의도 분류 관련 노드
    CLASSIFY_INTENT = 'classify_intent'
    RECLASSIFY_INTENT = 'reclassify_intent'
    HANDLE_INAPPROPRIATE = 'handle_inappropriate'
    CHATBOT = 'chatbot'
    INFO_QA = 'info_qa'

    # 정보 수집 및 업데이트 관련
    INFORMATION_GATHERING = 'information_gathering'
    INFORMATION_UPDATE = 'information_update'

    # search_subgraph 관련 노드
    SEARCH_NODE = 'search_node'

    PREPARE_TEMPLATE_SEARCH = 'prepare_template_search'
    POP_NEXT_EXPERT = 'pop_next_expert'
    RUN_EXPERT_EVALUATION = 'run_expert_evaluation'
    VECTOR_SEARCH = 'vector_search'
    GET_CACHED_ITEM = 'get_cached_item'
    SEND_REFINEMENT_PROMPT = 'send_refinement_prompt'
    PREPARE_CACHE_CYCLE = 'prepare_cache_cycle'
    PREPARE_SEARCH_CYCLE = 'prepare_search_cycle'

    # 상품 정보 조회 관련 노드
    PRODUCT_INFO_AGENT = 'product_info_agent'

    # 테스트 관련 노드
    TEST_SEARCH_NODE = 'test_search_node'


class StateName(StrEnum):
    MESSAGES = 'messages'
    CLOTH_SEARCH = 'cloth_search'
    IS_INFO_GATHERING_COMPLETE = 'is_info_gathering_complete'
    PRODUCT_ID = 'product_id'
    INTENT = 'intent'
    USER_MESSAGE = 'user_message'
    LAST_UPDATED_FIELDS = 'last_updated_fields'
    EXPERT_OPINIONS = 'expert_opinions'
    EXPERTS_TO_RUN = 'experts_to_run'
    CURRENT_EXPERT = 'current_expert'

    EXPERT_OFFSETS = 'expert_offsets'
    EXPERT_SEARCH_CACHE = 'expert_search_cache'
    SHOWN_IN_PRODUCT_IDS = 'shown_in_product_ids'
    CACHE_CYCLABLE = 'cache_cyclable'

    USER_NAME = 'user_name'
    IS_PREDEFINED_TEMPLATE = 'is_predefined_template'
    IS_UNCLEAR_FALLBACK = 'is_unclear_fallback'
```
