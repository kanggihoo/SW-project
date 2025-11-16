# LangGraph 전체 아키텍처 가이드

이 문서는 의류 추천 시스템의 전체 아키텍처와 동작 과정을 설명합니다. 이 시스템은 크게 **1) 사용자 의도 분류**와 **2) 코디 검색 서브그래프** 두 부분으로 나뉩니다.

- **의도 분류 (Intent Classification)**: 사용자의 입력을 분석하여 대화의 핵심 의도를 파악하고, 정보 수집, 일반 대화, 정보 문의, 검색 등 적절한 작업으로 분기합니다.
- **코디 검색 (Coordinated Search)**: '검색' 의도가 확인되면, 여러 전문가 에이전트가 협력하여 사용자에게 조화로운 상하의 코디 세트를 추천하고, 효율적인 캐싱을 통해 빠른 피드백을 제공합니다.

---

## 1. 전체 시스템 흐름도

```
                               +-------------------------+
                               |      User Message       |
                               +-----------+-------------+
                                           |
                                           v
                            +-----------------------------+
                            |  master_router              |
                            | (Product ID가 있는가?)      |
                            +--------------+--------------+
                                           |
+----------------------+                   | (No)
| product_info_agent   | <-----------------+
+----------------------+ (Yes)             |
                                           v
                            +-----------------------------+
                            |   intent_classify_node      |
                            | (사용자 의도 분류)          |
                            +--------------+--------------+
                                           |
                                           v
                            +-----------------------------+
                            | route_after_classification  |
                            | (의도에 따른 분기)          |
                            +--------------+--------------+
                                           |
      +------------------------------------+------------------------------------------+
      | (info_qa)                          | (chatbot)                                | (inappropriate)
      v                                    v                                          v
+--------------+                   +-----------------+                      +-------------------------+
| info_qa_node |                   |   chatbot_node  |                      | handle_inappropriate_node |
+--------------+                   +-----------------+                      +-------------------------+
      |                                    |                                          |
      +----------------------------------->| (END) |<----------------------------------+
                                           +-------+

      | (direct_search / search_refinement)
      v
+-----------------------------------------------------------------+
| 정보 수집 또는 업데이트 (information_gathering / information_update) |
+-----------------------------------------------------------------+
      |
      v
+-----------------------------------------------------------------+
| route_after_gathering (정보 수집 완료 시 검색으로)                  |
+-----------------------------------------------------------------+
      |
      v
+-----------------------------------------------------------------+
|                  SEARCH SUBGRAPH (코디 검색)                      |
| (전문가 분석, 벡터 검색, 캐싱, 결과 제공)                         |
+-----------------------------------------------------------------+
      |
      v
+-----------------------------------------------------------------+
|                         Final Response                            |
+-----------------------------------------------------------------+
```

---

## 2. State: 그래프의 공유 메모리

`State`는 그래프의 모든 노드가 데이터를 공유하는 중앙 메모리 저장소입니다.

```python
class State(TypedDict):
    # --- 전체 공유 상태 ---
    messages: Annotated[list[BaseMessage], add_messages]
    user_message: str
    intent: str
    product_id: str
    user_name: str
    is_predefined_template: bool
    is_unclear_fallback: bool

    # --- 정보 수집/업데이트 관련 ---
    cloth_search: ClothSearch
    is_info_gathering_complete: bool
    last_updated_fields: list[str]

    # --- 코디 검색 서브그래프 관련 ---
    cache_cyclable: bool
    experts_to_run: list[str]
    current_expert: str
    expert_opinions: dict[str, str]
    expert_search_cache: dict[str, dict[str, list[str]]]
    expert_offsets: dict[str, int]
    shown_in_product_ids: set[str]
```

- **핵심 상태 설명**:
    - `messages`: 전체 대화 기록.
    - `intent`: `direct_search`, `info_qa` 등 분류된 사용자 의도.
    - `product_id`: 사용자가 특정 상품에 대해 문의할 때 주어지는 상품 ID.
    - `user_name`: 사용자 이름.
    - `is_predefined_template`: 사용자가 미리 정의된 템플릿을 클릭했는지 여부.
    - `is_unclear_fallback`: 의도 분류 실패 시 `chatbot`으로 전환되었는지 나타내는 플래그.
    - `cloth_search`: 검색에 필요한 조건(TPO, 색상, 스타일)을 저장하는 Pydantic 모델.
    - `is_info_gathering_complete`: 검색 조건 수집 완료 여부. `True`가 되어야 검색 서브그래프가 실행됩니다.
    - `last_updated_fields`: `['style']`처럼 조건 변경을 감지하거나, `['__SHOW_CACHED__']`처럼 캐시 사용을 지시하는 플래그.
    - `cache_cyclable`: "다른 코디 보여줘" 요청 시 보여줄 캐시가 있는지 여부.
    - `expert_search_cache`: 전문가별로 검색된 상의(`TOP`), 하의(`BOTTOM`) 상품 ID 리스트를 저장하는 캐시.
    - `expert_offsets`: 각 전문가의 캐시에서 다음에 보여줄 아이템의 인덱스.
    - `shown_in_product_ids`: 중복 추천을 방지하기 위해 이미 보여준 상품 ID를 기록.

---

## 3. Part 1: 사용자 의도 분류 및 정보 수집

시스템의 첫 관문으로, 사용자의 요청을 이해하고 적절한 경로로 안내합니다.

### 3.1. 라우터 (Routers)

- **`master_router`**: 가장 먼저 실행됩니다.
    1. `product_id`가 있으면 → `custom_pre_model_node`를 거쳐 `product_info_agent`로 직접 라우팅합니다. (`custom_pre_model_node`는 `product_id`를 메시지에 포함시키는 역할을 합니다.)
    2. `is_predefined_template`가 `True`이면 → `prepare_template_search_node`로 라우팅하여 템플릿 기반 검색을 준비하고, `information_update_node`를 통해 검색으로 바로 이어집니다.
    3. 둘 다 해당 없으면 → `intent_classify_node`로 보내 일반적인 의도 분석을 시작합니다.

- **`route_after_classification`**: 의도 분류 결과에 따라 작업을 분배합니다.
    - `direct_search` (정보 수집 미완료) → `information_gathering_node` (정보 수집 시작)
    - `search_refinement` (정보 수집 완료) → `information_update_node` (검색 조건 수정)
    - `info_qa` → `info_qa_node` (자연어 질의응답)
    - `chatbot` → `chatbot_node` (일상 대화)
    - `inappropriate_query` → `handle_inappropriate_node` (부적절한 요청 처리)
    - `unclear` → `END` (대기)

- **`route_after_gathering`**: 정보 수집/업데이트 후 실행됩니다.
    - `is_info_gathering_complete`가 `True`이면 → **`search_subgraph`**로 진입하여 실제 검색 시작.
    - `False`이면 → `END`로 이동하여 추가 사용자 입력 대기.

### 3.2. 핵심 노드 (Nodes)

- **`intent_classify_node`**: 사용자의 의도를 6가지 유형 중 하나로 분류합니다.
    1. **1단계 (빠른 분류)**: 최신 메시지만으로 의도 파악.
    2. **2단계 (심층 분류)**: 1단계에서 `unclear`로 판단되면, 이전 대화 기록을 포함하여 재분류.

- **`information_gathering_node`**: 최초 검색 시, 사용자의 메시지에서 검색 조건(TPO, 색상, 스타일)을 추출하여 `cloth_search` 상태를 채웁니다. 만약 정보가 부족하면, 사용자에게 되물을 질문을 생성합니다. 모든 정보가 채워지면 `is_info_gathering_complete`를 `True`로 설정합니다.

- **`information_update_node`**: 이미 검색이 진행된 상태에서 사용자가 "청바지 말고 면바지로"처럼 조건을 변경할 때 호출됩니다. `cloth_search` 상태를 수정한 후, **검색 캐시를 초기화**하여 새로운 조건으로 다시 검색하도록 합니다.

- **기타 노드**:
    - `chatbot_node`: 일상 대화에 응답하며 자연스럽게 의류 검색으로 대화를 유도.
    - `info_qa_node`: 자연어 질의응답 노드.
    - `handle_inappropriate_node`: 부적절한 요청에 대해 정중한 거절 메시지를 반환.
    - `prepare_template_search_node`: 미리 정의된 템플릿 검색을 위해 상태를 준비하는 노드.

---

## 4. Part 2: 코디 검색 서브그래프 (Search Subgraph)

사용자의 의도가 '검색'으로 확정되고 모든 정보가 수집되면, 이 서브그래프가 실행되어 실제 코디 추천을 수행합니다.

### 4.1. 설계 철학: "최초 검색은 깊이 있게, 이후 탐색은 빠르게"

- **깊이 있는 분석**: 첫 검색 시, 여러 전문가(색상, 스타일, 핏)가 각자의 관점에서 사용자의 요청을 해석하고 벡터 검색을 통해 **조화로운 상하의 코디 세트**를 찾습니다.
- **빠른 피드백**: "다른 코디 보여줘"와 같은 후속 요청에는 LLM 호출이나 벡터 검색 없이, 미리 찾아둔 코디 세트 **캐시**를 사용하여 즉각적으로 다음 추천을 제공합니다.

### 4.2. 핵심 노드 (Nodes)

- **`prepare_search_cycle_node`**: **새로운 검색**을 준비합니다.
    - `last_updated_fields`를 확인하여 어떤 조건이 변경되었는지 파악.
    - 변경된 조건에 해당하는 전문가(들)를 `experts_to_run` 리스트에 추가.

- **`prepare_cache_cycle_node`**: **캐시된 결과를 보여주기 전** 준비합니다.
    - 각 전문가의 캐시(`expert_search_cache`)와 이미 보여준 상품 목록(`shown_in_product_ids`)을 비교.
    - 아직 보여주지 않은 새로운 **상하의 코디 세트**가 있는지 확인.
    - 보여줄 코디가 있으면, 해당 위치를 `expert_offsets`에 기록하고 `cache_cyclable`을 `True`로 설정.
    - **모든 전문가가 보여줄 코디 세트가 없으면, `cache_cyclable`이 `False`가 됩니다.**

- **`run_expert_evaluation_node` (전문가 분석)**: `current_expert`의 관점에서 사용자 요청을 분석하여 구체적인 검색 키워드(의견)를 생성하고 `expert_opinions`에 저장합니다.

- **`search_node` (벡터 검색)**: 전문가의 의견을 쿼리로 사용하여 벡터 DB에서 유사 상품을 검색합니다. 결과를 **상의(TOP)와 하의(BOTTOM)로 분리**하여 `expert_search_cache`에 저장합니다.

- **`get_cached_item_node`**: **LLM/벡터 검색 없이** 캐시에서 직접 코디 세트를 가져옵니다. `prepare_cache_cycle_node`에서 결정된 `offset`을 사용하여 상의와 하의 ID를 가져와 사용자에게 보여줄 메시지를 만듭니다.

- **`send_refinement_prompt_node`**: 모든 캐시를 소진했을 때, 사용자에게 더 보여줄 상품이 없음을 알리고 다른 조건을 제안하도록 유도하는 메시지를 보냅니다.

### 4.3. 라우터 (Routers)

- **`route_search_entry`**: 서브그래프의 진입점입니다.
    - `last_updated_fields`에 `__SHOW_CACHED__` 플래그가 있으면 → `prepare_cache_cycle_node`로 (캐시 활용)
    - 없으면 (조건 변경 또는 최초 검색) → `prepare_search_cycle_node`로 (새 검색)

- **`route_after_cache_preparation`**: 캐시 준비 노드 이후 분기합니다.
    - `cache_cyclable`이 `True`이면 → 캐시 순환 루프(`pop_next_expert_node`) 시작.
    - `False`이면 → `send_refinement_prompt_node`로 이동하여 캐시 소진 안내.

- **`decide_work_after_pop`**: 전문가 루프 내에서 작업을 결정합니다.
    - `__SHOW_CACHED__` 플래그가 있으면 → `get_cached_item_node` (캐시에서 가져오기)
    - 없으면 → `run_expert_evaluation_node` (새로운 전문가 분석)

---

## 5. 시나리오별 동작 과정

### 시나리오 1: 최초 검색 요청

> 사용자: "이번 주말 데이트 때 입을 옷 좀 추천해줘."

1.  **의도 분류**: `intent`가 `direct_search`로 분류됩니다.
2.  **정보 수집**: `information_gathering_node`가 '주말 데이트'를 `tpo`로 추출합니다. 색상, 스타일 정보가 부족하므로 "어떤 스타일을 선호하세요?"라고 되묻습니다.
3.  **정보 수집 완료**: 사용자가 "캐주얼한 스타일"이라고 답하면, `cloth_search`가 모두 채워지고 `is_info_gathering_complete`가 `True`가 됩니다.
4.  **검색 서브그래프 진입**: `route_after_gathering`을 통해 검색 서브그래프로 진입합니다. `last_updated_fields`가 비어있으므로 `route_search_entry`는 `prepare_search_cycle_node`를 선택합니다.
5.  **새 검색 준비**: `prepare_search_cycle_node`는 3명의 전문가(`color_expert`, `style_analyst`, `fitting_coordinater`)를 모두 `experts_to_run`에 넣습니다.
6.  **전문가 루프 (x3)**: 각 전문가는 `run_expert_evaluation_node`에서 분석 의견을 만들고, `search_node`에서 벡터 검색을 수행하여 상/하의 코디 세트를 `expert_search_cache`에 저장합니다.
7.  **결과 표시**: 3명의 전문가가 추천한 3개의 코디 세트(총 9개 상품)가 사용자에게 표시됩니다.

### 시나리오 2: "다른 코디 보여줘" (캐시 활용)

> (이전 검색 후) 사용자: "다른 것도 보여줘."

1.  **의도 분류 및 업데이트**: `information_update_node`가 조건 변경이 없음을 감지하고 `last_updated_fields`를 `['__SHOW_CACHED__']`로 설정합니다.
2.  **검색 서브그래프 진입**: `route_search_entry`가 `__SHOW_CACHED__` 플래그를 보고 `prepare_cache_cycle_node`를 선택합니다.
3.  **캐시 준비**: `prepare_cache_cycle_node`는 각 전문가의 캐시에서 아직 보여주지 않은 다음 코디 세트를 찾고, `expert_offsets`를 업데이트합니다. (예: `0` -> `1`)
4.  **캐시 순환 루프 (x3)**: `decide_work_after_pop`이 `get_cached_item_node`를 선택합니다.
5.  **즉각 결과 표시**: `get_cached_item_node`가 **LLM/벡터 검색 없이** 캐시에서 바로 다음 코디 세트를 가져와 사용자에게 보여줍니다. 이 과정은 매우 빠릅니다.

### 시나리오 3: 조건 변경 후 재검색

> (이전 검색 후) 사용자: "좀 더 포멀한 스타일로 바꿔줘."

1.  **의도 분류 및 업데이트**: `information_update_node`가 `style` 필드 변경을 감지하고 `cloth_search`를 업데이트합니다. **가장 중요하게, `expert_search_cache`와 `shown_in_product_ids`를 모두 초기화합니다.** `last_updated_fields`는 `['style']`이 됩니다.
2.  **검색 서브그래프 진입**: `route_search_entry`는 `__SHOW_CACHED__` 플래그가 없으므로 `prepare_search_cycle_node`를 선택합니다.
3.  **부분 재검색 준비**: `prepare_search_cycle_node`는 변경된 `style` 필드에 해당하는 `style_analyst` 전문가만 `experts_to_run`에 추가합니다. (다른 전문가의 캐시는 재사용될 수 있음 - 현재 로직에서는 전체 초기화)
4.  **새 검색 실행**: `style_analyst`가 새로운 '포멀' 스타일에 대한 분석과 벡터 검색을 수행하여 캐시를 업데이트합니다.
5.  **결과 표시**: 새로운 조건에 맞는 코디 세트가 사용자에게 표시됩니다.
