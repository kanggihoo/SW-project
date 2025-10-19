## LangGraph `search_subgraph` 아키텍처 가이드

이 문서는 의류 추천 시스템의 핵심 검색 엔진인 `search_subgraph`의 설계 철학과 전체 동작 과정을 설명합니다.

### 1. 배경: 왜 이런 구조를 선택했는가? 🤔

좋은 의류 추천 시스템은 두 가지 상반된 요구사항을 만족해야 합니다.

1. **깊이 있는 분석**: 사용자의 모호한 요청(예: "요즘 유행하는 바지")을 색상, 스타일, 핏 등 여러 전문적인 관점에서 해석하여 풍부하고 적절한 결과를 제공해야 합니다.
2. **빠른 피드백 반응**: 사용자가 "다른 건 없어?" 또는 "비슷한 거 더 보여줘"와 같이 간단한 피드백을 주었을 때, 기다림 없이 즉각적으로 다음 결과를 보여주어야 합니다.

첫 번째 요구사항을 위해서는 강력한 LLM 분석과 비용이 높은 벡터 검색이 필수적입니다. 하지만 두 번째 요구사항에 대해서도 매번 동일한 고비용 작업을 반복하는 것은 매우 비효율적이며 사용자 경험을 저해합니다.

이 문제를 해결하기 위해 **"최초 검색은 깊이 있게, 이후 탐색은 빠르고 효율적으로"**라는 목표 아래, **전문가 시스템(Expert System)**과 **캐싱(Caching) 전략**을 결합한 하이브리드 구조를 설계했습니다. 이 구조는 첫 검색 시에는 여러 전문가가 심도 깊은 분석과 검색을 수행하여 결과를 '캐시'에 저장하고, 이후 요청 시에는 이 캐시를 재활용하여 LLM 호출이나 벡터 검색 없이 즉각적으로 다음 결과를 제공합니다.

### 2. 핵심 구성 요소: 그래프는 무엇으로 이루어져 있는가?

우리 `search_subgraph`는 LangGraph의 세 가지 핵심 요소인 **State, Node, Router**로 구성됩니다.

### 2.1. State: 그래프의 공유 메모리

`State`는 그래프의 모든 노드가 데이터를 읽고 쓸 수 있는 중앙 메모리 저장소입니다.

-   `user_message`: 사용자가 입력한 원본 메시지.
-   `last_updated_fields`: 사용자의 피드백으로 어떤 조건이 변경되었는지 기록합니다. `['__SHOW_CACHED__']` 플래그는 캐시 순환 모드를 활성화하는 특별한 값입니다.
-   `experts_to_run`: 실행해야 할 전문가의 목록. (예: `['color_expert', 'style_analyst', 'fitting_coordinater']`) ,  루프의 실행 여부와 횟수를 제어합니다.
-   `current_expert`: 현재 루프에서 작업을 수행 중인 전문가의 이름입니다.
-   `expert_opinions`: `current_expert`가 생성한 분석 의견. 이 의견이 벡터 검색의 쿼리로 사용됩니다.
-   `messages`: 사용자에게 보여줄 최종 메시지(검색 결과 포함)가 담기는 리스트.
-   `search_result_offset`: "다른거 보여줘"와 같은 요청 시, 다음 검색 결과를 가져오기 위한 오프셋 값.
- `expert_search_cache`: **(캐싱의 핵심)** 전문가의 이름(`str`)을 Key로, 해당 전문가가 벡터 검색으로 찾은 상품 정보(`list`)를 Value로 갖는 딕셔너리입니다. `{'color_expert': [{'product_id': 'P123', 'opinion': '밝은 색상의 데님'}]}` 와 같은 구조를 가집니다.
- `expert_offsets`: 각 전문가의 캐시 목록에서 몇 번째 상품까지 보여줬는지를 기록하는 인덱스입니다.
- `shown_in_current_cycle`: "다른거 보여줘" 한 번의 사이클 동안 이미 보여준 상품 ID를 기록하여, 다른 전문가가 동일한 상품을 중복 추천하는 것을 방지합니다.

### 2.2. Nodes:

`Node`는 실제 작업을 수행하는 함수입니다.

-   `pop_next_expert_node`:
    -   `experts_to_run` 리스트에서 다음으로 실행할 전문가를 하나 꺼내(`pop`) `current_expert` 상태를 업데이트합니다.
-   `run_expert_evaluation` (`external_llm_node`):
    -   `current_expert`와 `user_message`를 기반으로 외부 LLM API를 호출합니다.
    -   LLM은 전문가의 관점에서 사용자 요청을 분석하고, 그 결과를 `expert_opinions` 상태에 저장합니다.
- `vector_search`:
    -  `expert_opinions`를 쿼리로 사용하여 벡터 데이터베이스에서 유사한 상품을 검색합니다.
    -  `run_expert_evaluation`이 생성한 검색어로 벡터 DB를 검색합니다. **검색이 성공하면 그 결과를 `expert_search_cache`에 저장하는 중요한 역할**을 합니다.
- `get_next_cached_item_node`: **(빠른 반응의 핵심)** LLM이나 벡터 검색 없이, `expert_search_cache`와 `expert_offsets`를 이용해 다음으로 보여줄 상품을 즉시 찾아냅니다.
- `send_refinement_prompt_node`: 모든 캐시가 소진되었을 때, 사용자에게 더 이상 보여줄 상품이 없음을 알리고 새로운 검색을 유도하는 메시지를 생성합니다.

### 2.3. Routers:

`Router`는 현재 `State`를 보고 다음에 어떤 `Node`로 가야 할지 결정하는 함수입니다.

- `route_search_logic` (통합 진입 라우터): 그래프의 첫 관문으로, 가장 중요한 의사결정을 합니다.
    1. 사용자 요청에 **새로운 조건**이 있으면, 벡터 검색을 수행하는 **`start_expert_loop`** 경로를 선택합니다.
    2. "다른거 보여줘"와 같이 **조건 변경이 없으면 (`__SHOW_CACHED__`)**, 캐시를 확인합니다. 보여줄 아이템이 남아있으면 캐시를 순환하는 **`continue_cached_loop`** 경로를, 모두 소진되었으면 **`no_more_items`** 경로를 선택합니다.
- `decide_work_after_pop`: `pop_next_expert_node` 직후 실행되는 작은 결정 함수입니다. `last_updated_fields` 상태를 보고, **새로운 분석(`run_expert_evaluation`)**을 할지 **캐시 조회(`get_next_cached_item`)**를 할지 결정하여 두 개의 다른 작업 흐름을 분기합니다.
- `route_expert_loop`: `vector_search` 또는 `get_next_cached_item` 작업이 끝난 후 호출됩니다. `experts_to_run` 목록에 아직 전문가가 남아있는지 확인하여, 루프를 계속할지(`continue_loop`) 아니면 그래프를 종료할지(`end_loop`) 결정합니다.

---

### 3. 시나리오별 동작 과정: 그래프는 어떻게 움직이는가?

### 시나리오 1: 최초 검색 요청

> 사용자: "이번 주말 데이트 때 입을 청바지 좀 찾아줘."
> 
1. **[진입]** `route_search_logic`은 새로운 검색 요청임을 인지하고, `experts_to_run`에 `['color_expert', 'style_analyst', 'fitting_coordinater']`를 채우고 **`start_expert_loop`** 경로를 반환합니다.
2. **[전문가 루프 시작]**
    - `pop_next_expert_node`가 `'color_expert'`를 꺼냅니다.
    - `decide_work_after_pop`은 캐시 플래그가 없으므로 `'run_expert_evaluation'` 경로를 선택합니다.
    - `run_expert_evaluation` 노드가 "데이트에 어울리는 화사한 색감의 데님" 같은 검색어를 생성합니다.
    - `vector_search` 노드가 이 검색어로 DB를 검색하고, **결과를 `expert_search_cache['color_expert']`에 저장**합니다.
3. **[루프 반복]** `route_expert_loop`는 아직 남은 전문가(`style_analyst`, `fitting_coordinater`)가 있으므로 루프의 처음(`pop_next_expert_node`)으로 돌아갑니다. `style`, `fit` 전문가에 대해서도 2번 과정을 반복하며 각각의 검색 결과를 캐시에 저장합니다.
4. **[종료]** 모든 전문가의 작업이 끝나면 `route_expert_loop`가 루프를 종료하고, 3명의 전문가가 찾은 다양한 결과가 사용자에게 표시됩니다.

### 시나리오 2: "다른 거 없어?" (캐시 활용)

> 사용자: "음... 다 좋은데 다른 것도 좀 볼 수 있을까?"
> 
1. **[진입]** (그래프 외부의 `information_update_node`가 조건 변경이 없다고 판단하여 `last_updated_fields`를 `['__SHOW_CACHED__']`로 설정) `route_search_logic`은 이 플래그를 보고 캐시를 확인합니다. 캐시에 데이터가 충분하므로 **`continue_cached_loop`** 경로를 반환합니다.
2. **[캐시 순환 루프 시작]**
    - `pop_next_expert_node`가 다시 `'color_expert'`를 꺼냅니다.
    - `decide_work_after_pop`은 `__SHOW_CACHED__` 플래그를 보고 이번에는 **`'get_cached_item'`** 경로를 선택합니다.
    - `get_next_cached_item_node`는 `expert_search_cache['color_expert']` 목록에서 다음 순서(예: 2번째)의 상품을 즉시 꺼내 사용자에게 보여주고, `expert_offsets['color_expert']`를 1 증가시킵니다. **(LLM, 벡터 검색 없음!)**
3. **[루프 반복]** `style`, `fit` 전문가에 대해서도 2번 과정을 반복하여, 각 전문가가 이전에 찾아두었던 다음 상품들을 빠르게 보여줍니다.
4. **[종료]** 모든 전문가가 다음 상품을 하나씩 보여주고 나면 루프가 종료됩니다. 사용자는 거의 즉각적으로 3개의 새로운 추천을 받게 됩니다.

### 시나리오 3: 캐시 소진

> 사용자: (여러 번 "다른 거 보여줘"를 반복한 후) "더 없어?"
> 
1. **[진입 및 판단]** `route_search_logic`은 `__SHOW_CACHED__` 플래그를 보고 다시 캐시를 확인합니다. 하지만 `expert_offsets`를 보니 모든 전문가가 저장된 결과를 전부 보여준 상태입니다. 더 이상 보여줄 상품이 없다고 판단하고 **`no_more_items`** 경로를 반환합니다.
2. **[안내 및 종료]** 그래프는 `send_refinement_prompt_node`로 이동하여 "추천해 드릴 만한 다른 상품을 모두 보여드렸어요. 원하시는 스타일을 더 자세히 알려주시겠어요?" 라는 메시지를 생성하고 사용자에게 전달한 뒤, 그래프를 평화롭게 종료합니다.