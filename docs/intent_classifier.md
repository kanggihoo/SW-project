이 시스템은 크게 **세 가지 주요 흐름**으로 나뉩니다.

1. **제품 ID 기반 검색**: 사용자가 명확한 제품 ID를 제공하면, `product_info_agent` 노드로 직접 라우팅되어 해당 제품에 대한 정보를 제공합니다.
2. **자연어 기반 검색**: 제품 ID가 없는 경우, **사용자의 의도를 먼저 파악하고, 의도에 따라 적절한 경로로 분기**하여 처리합니다.
3. **템플릿 기반 검색**: 사용자가 "주말 데이트룩 찾아줘"와 같이 미리 만들어진 버튼/템플릿을 클릭하면, **의도 분류 과정을 생략하고 즉시 정보 수정 및 검색 단계로 진입**하여 빠른 사용자 경험을 제공합니다.

## 1. 사용자 의도 파악

의도 분류기의 핵심 목표는 **속도와 정확성의 균형**을 맞추는 것입니다.
하지만 `is_predefined_template` 상태가 True인 경우, 즉 사용자가 미리 정의된 템플릿을 클릭한 경우에는 이 의도 분류 과정을 완전히 건너뛰고 다음 단계로 바로 진행하여 응답 속도를 극대화합니다.

자연어 입력에 대해서는 다음과 같은 2단계 하이브리드(Hybrid) 전략을 사용합니다.

1. **1단계: 빠른 초벌 분류 (Fast Initial Pass)**
    - 분류기는 먼저 사용자의 가장 최근 메시지만을 보고 의도를 파악합니다. 이 방식은 90% 이상의 일반적인 경우에 해당하며, 매우 빠르고 효율적으로 작동합니다.
2. **2단계: 심층 재분류 (Contextual Fallback)**
    - 만약 첫 시도에서 의도가 불분명하다고(`unclear`) 판단될 경우, 분류기는 자동으로 이전 대화 2~3개의 기록을 포함하여 다시 한번 분석을 수행합니다.
    - 이는 문맥이 중요한 모호한 요청의 정확도를 높이기 위한 안전장치 역할을 합니다.

이러한 접근 방식은 평소에는 신속하게 작동하다가, 꼭 필요할 때만 더 많은 정보를 활용하여 지능적으로 대처하는 고성용 시스템을 구축하게 해줍니다.

## 2. 의도 분류 모델 정의 (Pydantic)

LLM이 일관된 형식의 결과만 반환하도록 강제하기 위해 Pydantic 모델을 사용합니다. 특히 `Literal` 타입을 활용하여, **미리 정의된 6가지 의도 중 하나만 반환하도록 제**한합니다.

```python
from pydantic import BaseModel, Field
from typing import Literal

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
        "direct_search",
        "info_qa",
        "search_refinement",
        "small_talk",
        "inappropriate_query",
        "unclear"
    ] = Field(
        description="사용자 발화의 핵심 의도를 6가지 중 하나로 분류한 결과입니다."
    )
```

## 3. 의도 분류기 시스템 프롬프트 설계

분류기의 핵심은 LLM에게 전달할 시스템 프롬프트입니다. 각 의도를 명확한 예시와 함께 설명하고, 현재 대화의 **상태(State)** 정보를 함께 제공하여 LLM이 문맥을 정확하게 파악하고 판단하도록 유도합니다.

```python
너는 사용자의 메시지와 현재 대화 상태를 분석하여 의도를 6가지 유형 중 하나로 분류하는 전문가다.
다른 말은 절대 하지 말고, 반드시 'UserIntent' Pydantic 모델 형식으로만 답변해야 한다.

[현재 대화 상태]
- 초기 정보 수집 완료 여부: {is_info_gathering_complete}

[분류 기준]
1. `direct_search`: 사용자가 특정 옷을 찾거나, 추천받거나, 구매하려는 명확한 의도.
2. `info_qa`: 패션 트렌드, 용어, 코디 팁 등 정보 질문.
3. `search_refinement`: '초기 정보 수집 완료 여부'가 True일 때, 이전 검색 결과에 대한 수정/구체화 요청.
4. `chatbot`: 의류와 관련 없는 일상 대화.
5. `inappropriate_query`: 성적, 폭력적, 비윤리적, 모욕적인 내용.
6. `unclear`: 위 5가지로 분류하기 어려운 모호한 경우.

```

## 4. 의도별 후속 처리 노드 설계

의도가 분류된 후, 각 상황에 맞는 전문화된 노드(에이전트)가 응답을 처리합니다.

### 💬 `chat bot` (일상 대화) 처리 노드

- **목표**: 친절한 응대와 자연스러운 대화 복귀 유도
- **시스템 프롬프트**:
    
    > 너는 사용자와 친근하게 대화하는 AI 어시스턴트다. 사용자의 일상적인 대화에 가볍고 긍정적으로 응답해야 한다.
    **가장 중요한 임무는 대화가 원래 목적인 '의류 검색'으로 자연스럽게 돌아가도록 유도하는 것**이다. 전체 대화 기록을 참고하여 AI가 마지막으로 했던 질문을 찾은 뒤, 사용자의 말에 답변하고 이어서 다시 한번 부드럽게 물어봐라.
    [대화 예시]
    (이전 AI 질문: "어떤 색상을 원하세요?")
    사용자: "오늘 날씨 정말 좋다!"
    너: "네, 정말 화창하네요! 이런 날 입기 좋은 옷을 찾아드릴까요? 혹시 생각하고 계신 색상이 있으셨나요? 😊"
    > 

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
- `is_info_gathering_complete`: 정보 수집이 완료되었는지 여부를 나타내는 플래그입니다. `route_after_gathering` 라우터의 핵심적인 분기 조건이 됩니다.
- `product_id`: 사용자가 제공한 제품 ID를 저장합니다. `master_router`의 첫 번째 분기 조건으로 사용됩니다.
- `intent`: 분류된 사용자의 의도를 저장합니다.
- `user_message`: 현재 사용자의 입력 메시지를 저장합니다.
- `is_predefined_template`: 사용자가 미리 정의된 템플릿을 클릭했는지 여부를 나타냅니다. `master_router`의 핵심 분기 조건 중 하나입니다.

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
    # 미리 정의된 템플릿 클릭 여부
    is_predefined_template: bool
    # 정보 업데이트 시 어떤 필드가 변경되었는지 기록
    last_updated_fields: Annotated[list[str], Field(description='마지막으로 업데이트된 필드')]
    
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
- `route_after_classification`: `classify_intent` 노드에서 분류된 `intent` 값을 기반으로, 정보 수집, 부적절한 질문 처리, 챗봇 등 다음 단계로 작업을 분배합니다.
    
```python
def route_after_classification(state: State):
    """의도 분류 결과에 따라 다음 노드를 결정
    state에 담긴 intent 와 is_info_gathering_complete 를 사용하여 라우팅 결정
    1. is_info_gathering_complete 가 False 이고 intent 가 DIRECT_SEARCH 이면 INFORMATION_GATHERING 으로 이동하여 정보 수집 노드 동작
    2. is_info_gathering_complete 가 True 이고 intent 가 SEARCH_REFINEMENT 이면 INFORMATION_UPDATE 으로 이동하여 정보 업데이트 노드 동작

    3. 그외의 부적절한 의도, 챗봇, 정보 검색 인 경우 해당 노드로 이동
    4. unclear 또는 기타 의도의 경우 END 로 이동
    """
    intent = state[StateName.INTENT]
    is_info_gathering_complete = state.get(StateName.IS_INFO_GATHERING_COMPLETE, False)
    if not is_info_gathering_complete and intent == NodeName.DIRECT_SEARCH:
        logger.debug('- 라우팅: information_gathering_node로 이동 (초기 수집)')
        return NodeName.INFORMATION_GATHERING
    elif is_info_gathering_complete and intent == NodeName.SEARCH_REFINEMENT:
        logger.debug('- 라우팅: information_update_node로 이동 (피드백 수정)')
        return NodeName.INFORMATION_UPDATE

    elif intent == NodeName.INAPPROPRIATE_QUERY:
        logger.debug('- 라우팅: handle_inappropriate_node로 이동')
        return NodeName.HANDLE_INAPPROPRIATE
    elif intent == NodeName.CHATBOT:
        logger.debug('- 라우팅: chatbot_node로 이동')
        return NodeName.CHATBOT
    elif intent == NodeName.INFO_QA:
        logger.debug('- 라우팅: info_qa_node로 이동')
        return NodeName.INFO_QA
    else:  # unclear 또는 기타
        logger.debug('- 라우팅: END (분류 실패 또는 추가 처리 불필요)')
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


- `information_gathering_node`: 검색 의도가 감지되었을 때 실행됩니다.
    1. LLM을 호출하여 사용자 메시지에서 TPO, 색상, 스타일 등의 정보를 **추출**합니다.
    2. 기존 `state.cloth_search`에 추출된 정보를 **업데이트**합니다.
    3. 모든 정보가 채워졌는지 **확인**합니다.
    4. **만약 부족한 정보가 있다면, 해당 정보를 묻는 질문을 LLM으로 생성하여 사용자에게 되돌려줍**니다.
   
- `intent_classify_node` : 사용자 질문에 대한 의도 파악 노드 
  1. 사용자의 최근 메시지(user_message)를 받아 1차 의도 분류를 시도합니다. (direct_search, chatbot 등) 
  2. 만약 의도가 불분명(UNCLEAR)하면, 이전 대화 내용까지 포함하여 더 넓은 맥락으로 2차 심층 분류를 진행하여 정확도를 높입니다.
  3. 분류된 의도(intent)를 State에 저장합니다.

- `information_gathering_node`: 검색 의도가 감지되었을 때 실행
  1. LLM을 호출하여 사용자 메시지에서 TPO, 색상, 스타일 등의 정보를 추출(extraction_llm)합니다.
  2. 기존 `state.cloth_search`에 추출된 정보를 **업데이트**합니다.
  3. cloth_search에 아직 채워지지 않은 정보(missing_fields)가 있는지 확인합니다.
  4. 정보가 부족하면: 사용자에게 추가 정보를 요청하는 질문을 생성(generation_llm)하여 messages 상태에 추가하고, is_info_gathering_complete를 False로 설정합니다.
  5. 모든 정보가 수집되면: is_info_gathering_complete를 True로 설정합니다.
   
- `information_update_node`:
  1. 이미 정보 수집이 완료된 상태(is_info_gathering_complete = True 인 경우)에서 사용자가 "청바지 말고 면바지로 찾아줘" 와 같이 검색 조건을 수정하려 할 때 호출됩니다.
  2. 기존 검색 조건(current_search_info)과 사용자 수정 요청(user_message)을 함께 LLM(update_llm)에 전달하여 변경이 필요한 부분만 수정합니다.
  3. 수정된 cloth_search를 State에 반영하고 search_subgraph로 이동
  4. 이때 정보가 업데이트 되었는지 혹은 업데이트 되지 않았냐에 따라서 이후의 search_subgraph의 동작이 달라짐.

- `search_node`: 모든 정보 수집이 완료되었을 때 최종적으로 실행되는 노드입니다. 현재는 플레이스홀더(Placeholder)이지만, 향후 이 노드에서 실제 벡터 기반 이미지 검색 로직이 실행될 것입니다.
- `handle_inappropriate_node`: 사용자의 입력이 성적, 폭력적, 비윤리적, 모욕적인 내용에 해당할 경우, 미리 준비된 정중한 거절 메시지(하드코딩된 응답)를 반환하여 안전한 대화 환경을 유지합니다.
- `chatbot_node`: 사용자의 일상적인 대화에 친근하게 응답하는 역할을 합니다. 핵심 목표는 사용자의 말에 긍정적으로 반응하면서도, 대화의 본래 목적인 '의류 검색'으로 자연스럽게 대화를 유도
- `info_qa_node`: 패션 전문가로서 사용자의 정보성 질문에 답변합니다. 최신 트렌드, 스타일링 팁, 의류 관리법 등에 대해 웹 검색과 같은 도구를 사용하여 정확하고 전문적인 정보를 제공합니다. 답변 후에는 "또 궁금한 점이 있으신가요?"처럼 다음 행동을 제안하여 대화를 주도적으로 이끌어 나갑니다. 또한, 검색 후 사용자의 피드백을 처리하고 재검색으로 연결하는 중요한 역할을 담당할 수 있습니다.
- `product_info_agent`: 제품 ID를 기반으로 정보를 조회하는 에이전트입니다. 데이터베이스 조회나 API 호출과 같은 도구를 사용하여 특정 제품 정보를 가져오는 역할을 수행할 수 있습니다.

## 4. pydantic model
- langgraph 특정 노드에서의 llm의 구조화된 출력을 위해 사용되는 pydantic 모델 
```python
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
        NodeName.DIRECT_SEARCH,
        NodeName.INFO_QA,
        NodeName.SEARCH_REFINEMENT,
        NodeName.CHATBOT,
        NodeName.INAPPROPRIATE_QUERY,
        NodeName.UNCLEAR,
    ] = Field(description='사용자 발화의 핵심 의도를 분류한 결과입니다.')

```

## 5. langgraph_enum
- 직접 문자열로 하드코딩을 피하기 위한 StrEnum 적용 
```python
from enum import StrEnum

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

    TEST_SEARCH_NODE = 'test_search_node'

    INFORMATION_UPDATE = 'information_update'

    POP_NEXT_EXPERT = 'pop_next_expert'
    RUN_EXPERT_EVALUATION = 'run_expert_evaluation'
    QUERY_ANALYSIS = 'query_analysis'
    VECTOR_SEARCH = 'vector_search'
    SHOW_NEXT_RESULTS = 'show_next_results'


class StateName(StrEnum):
    MESSAGES = 'messages'
    CLOTH_SEARCH = 'cloth_search'
    IS_INFO_GATHERING_COMPLETE = 'is_info_gathering_complete'
    PRODUCT_ID = 'product_id'
    INTENT = 'intent'
    USER_MESSAGE = 'user_message'
    LAST_UPDATED_FIELDS = 'last_updated_fields'
    EXPERT_OPINIONS = 'expert_opinions'
    SEARCH_RESULT_OFFSET = 'search_result_offset'
    EXPERT_TO_RUN = 'expert_to_run'
    CURRENT_EXPERT = 'current_expert'
    IS_PREDEFINED_TEMPLATE = 'is_predefined_template'

```

# 전체 그래프 구성 및 동작 과정

## 동작 시나리오 예시:

### 시나리오 1: 새로운 의류 검색
```plaintext
사용자: "여름에 입을 시원한 반팔티 좀 찾아줘"

START -> master_router -> intent_classify_node

intent를 DIRECT_SEARCH로 분류.

-> route_after_classification

is_info_gathering_complete는 False이고 intent는 DIRECT_SEARCH이므로 information_gathering_node로 이동.

-> information_gathering_node

"여름", "반팔티" 정보를 추출하여 cloth_search 상태에 저장.

color, style 정보가 부족한 것을 확인.

"어떤 색상이나 스타일을 원하시나요?" 같은 질문을 생성하여 messages에 추가.

is_info_gathering_complete는 여전히 False.

-> route_after_gathering

is_info_gathering_complete가 False이므로 END로 이동하여 사용자 응답 대기.
```

### 시나리오 2: 검색 조건 수정
``` plaintext
(이전 검색 후) 사용자: "청바지 말고 검은색 슬랙스로 바꿔줘"

START -> master_router -> intent_classify_node

intent를 SEARCH_REFINEMENT으로 분류.

-> route_after_classification

is_info_gathering_complete는 True이고 intent는 SEARCH_REFINEMENT이므로 information_update_node로 이동.

-> information_update_node

기존 cloth_search 정보와 사용자 요청을 바탕으로 바지 종류를 '청바지'에서 '슬랙스'로, 색상을 '검은색'으로 수정.

-> search_node (직선 연결)

수정된 cloth_search 정보로 다시 검색 실행.

-> END
```

### 시나리오 3: 미리 정의된 템플릿 검색
```plaintext
사용자: (미리 정의된 "출근할 때 입을 깔끔한 스타일 옷 추천" 템플릿 버튼 클릭)

START -> master_router

`is_predefined_template`이 True이므로 prepare_template_search_node로 이동.

-> prepare_template_search_node

`is_info_gathering_complete`를 True로, `cloth_search`를 빈 객체로 초기화.

-> information_update_node (직선 연결)

템플릿에 담긴 "출근할 때 입을 깔끔한 스타일 옷 추천" 메시지를 바탕으로 `cloth_search` 상태를 'tpo: 출근', 'style: 깔끔한'으로 채움.
새로운 검색을 위해 캐시 등 관련 상태 초기화.

-> search_node (직선 연결)

업데이트된 `cloth_search` 정보로 검색 실행.

-> END
```



