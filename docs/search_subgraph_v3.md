## LangGraph `search_subgraph` 아키텍처 가이드 (v3)

이 문서는 의류 추천 시스템의 핵심 검색 엔진인 `search_subgraph`의 설계 철학과 전체 동작 과정을 설명합니다.

## 📌 v2 → v3 주요 변경 사항

### 1. 코디네이션 기반 추천 시스템으로 전환
- **v2**: 단일 상품 추천 (상의 또는 하의 각각)
- **v3**: 상하의 세트 추천 (TOP + BOTTOM 코디네이션)
- 전문가들이 상의와 하의를 동시에 고려한 코디를 추천

### 2. 전문가 의견 저장 구조 변경
```python
# v2
expert_opinions: str  # 마지막 전문가 의견만 저장 (덮어쓰기)

# v3
expert_opinions: dict[str, str]  # 모든 전문가 의견 누적 저장
# {
#     "color_expert": "밝은 색상의 데님과 화이트 톤의 상의",
#     "style_analyst": "캐주얼하면서 세련된 데이트룩 스타일",
#     "fitting_coordinater": "슬림핏 상의와 스트레이트 핏 하의"
# }
```

### 3. 캐시 구조 개선
```python
# v2
expert_search_cache: {
    'color_expert': [
        {'product_id': 'P123', 'opinion': '밝은 색상의 데님'}
    ]
}

# v3
expert_search_cache: {
    'color_expert': {
        'TOP': ['P001', 'P002', 'P003'],     # 상의 상품 ID 리스트
        'BOTTOM': ['P101', 'P102', 'P103']   # 하의 상품 ID 리스트
    }
}
```
- TOP과 BOTTOM을 카테고리별로 분리 저장
- 같은 인덱스의 TOP-BOTTOM이 하나의 코디 세트
- product_id만 저장하여 State 크기 최소화 (상세 정보는 MongoDB에서 실시간 조회)

### 4. 캐시 순환 로직 강화
- **v3**: TOP-BOTTOM 쌍 단위로 중복 체크 및 순환
- 코디 세트의 온전성 보장 (상의만 or 하의만 보여주는 상황 방지)
- 전체 중단 구조: 모든 전문가가 보여줄 세트가 있어야 순환 가능

### 5. 캐시 관리 개선
- 조건 변경 시 캐시 및 shown_ids 자동 초기화
- 전문가별 의견 보존으로 캐시 표시 시 컨텍스트 제공 가능

---

## 1. 배경: 왜 이런 구조를 선택했는가? 🤔

좋은 의류 추천 시스템은 두 가지 상반된 요구사항을 만족해야 합니다.

1. **깊이 있는 분석**: 사용자의 모호한 요청(예: "요즘 유행하는 데이트룩")을 색상, 스타일, 핏 등 여러 전문적인 관점에서 해석하여 **조화로운 상하의 코디**를 제공해야 합니다.
2. **빠른 피드백 반응**: 사용자가 "다른 코디 없어?" 또는 "비슷한 스타일 더 보여줘"와 같이 간단한 피드백을 주었을 때, 기다림 없이 즉각적으로 다음 코디를 보여주어야 합니다.

첫 번째 요구사항을 위해서는 강력한 LLM 분석과 비용이 높은 벡터 검색이 필수적입니다. 하지만 두 번째 요구사항에 대해서도 매번 동일한 고비용 작업을 반복하는 것은 매우 비효율적이며 사용자 경험을 저해합니다.

이 문제를 해결하기 위해 **"최초 검색은 깊이 있게, 이후 탐색은 빠르고 효율적으로"**라는 목표 아래, **전문가 시스템(Expert System)**과 **캐싱(Caching) 전략**을 결합한 하이브리드 구조를 설계했습니다. 이 구조는 첫 검색 시에는 여러 전문가가 심도 깊은 분석과 검색을 수행하여 상하의 코디 세트를 '캐시'에 저장하고, 이후 요청 시에는 이 캐시를 재활용하여 LLM 호출이나 벡터 검색 없이 즉각적으로 다음 코디를 제공합니다.

---

## 2. 핵심 구성 요소: 그래프는 무엇으로 이루어져 있는가?

우리 `search_subgraph`는 LangGraph의 세 가지 핵심 요소인 **State, Node, Router**로 구성됩니다.

### 2.1. State: 그래프의 공유 메모리

`State`는 그래프의 모든 노드가 데이터를 읽고 쓸 수 있는 중앙 메모리 저장소입니다.

#### 기본 사용자 입력 및 제어
- `user_message`: 사용자가 입력한 원본 메시지
- `last_updated_fields`: 사용자의 피드백으로 어떤 조건이 변경되었는지 기록. `['__SHOW_CACHED__']` 플래그는 캐시 순환 모드를 활성화하는 특별한 값
- `messages`: 사용자에게 보여줄 최종 메시지(검색 결과 포함)가 담기는 리스트

#### 전문가 시스템 관련
- `experts_to_run`: 실행해야 할 전문가의 목록 (예: `['color_expert', 'style_analyst', 'fitting_coordinater']`). 루프의 실행 여부와 횟수를 제어
- `current_expert`: 현재 루프에서 작업을 수행 중인 전문가의 이름
- `expert_opinions`: **[v3 변경]** 전문가별 분석 의견을 저장하는 딕셔너리
  ```python
  {
      'color_expert': '밝은 톤의 상의와 데님 하의의 조화',
      'style_analyst': '캐주얼한 데이트룩 코디',
      'fitting_coordinater': '슬림핏 상의와 스트레이트 핏 하의'
  }
  ```

#### 캐싱 시스템 (v3 구조)
- `expert_search_cache`: **[v3 핵심 변경]** 전문가별 코디 캐시
  ```python
  {
      'color_expert': {
          'TOP': ['P001', 'P002', 'P003'],      # 상의 상품 ID
          'BOTTOM': ['P101', 'P102', 'P103']    # 하의 상품 ID
      },
      'style_analyst': {...},
      'fitting_coordinater': {...}
  }
  ```
  - 같은 인덱스의 TOP-BOTTOM이 하나의 코디 세트
  - 예: `P001`(상의) + `P101`(하의) = 첫 번째 코디

- `expert_offsets`: 각 전문가의 캐시에서 현재 어느 인덱스까지 보여줬는지 추적
  ```python
  {
      'color_expert': 0,      # 0번 인덱스 코디를 보여줄 차례
      'style_analyst': 1,     # 1번 인덱스 코디를 보여줄 차례
      'fitting_coordinater': 0
  }
  ```

- `shown_in_product_ids`: 이미 보여준 상품 ID를 기록하여 중복 추천 방지
  ```python
  {'P001', 'P101', 'P002', 'P102'}  # set 타입
  ```

---

### 2.2. Nodes: 작업 수행 단위

`Node`는 실제 작업을 수행하는 함수입니다.

#### 초기 진입 및 준비
- **`prepare_search_cycle_node`**: 최초 벡터 검색을 위한 전문가 목록 준비
  - 조건 변경 여부에 따라 실행할 전문가 결정
  - 모든 조건 변경: 3명 전문가 모두 실행
  - 특정 조건만 변경: 해당 전문가만 실행

- **`prepare_cache_cycle_node`**: **[v3 핵심 변경]** 캐시 순환 가능 여부 판단
  - 각 전문가의 캐시에서 TOP-BOTTOM 쌍 찾기
  - 중복되지 않은 코디 세트 확인
  - offset을 보여줄 위치로 설정
  - **전체 중단 구조**: 하나의 전문가라도 세트를 못 찾으면 순환 불가

#### 전문가 실행 루프
- **`pop_next_expert_node`**: `experts_to_run` 리스트에서 다음 전문가를 꺼내 `current_expert`로 설정

- **`external_llm_node`** (run_expert_evaluation):
  - 외부 LLM API를 호출하여 전문가 관점의 분석 수행
  - **[v3 변경]**: 결과를 `expert_opinions[current_expert]`에 저장 (덮어쓰기 아님)

- **`search_node`** (vector_search):
  - **[v3 변경]**: `expert_opinions[current_expert]`의 의견을 쿼리로 사용
  - 벡터 DB에서 유사 상품 검색 (limit=5)
  - **[v3 변경]**: 결과를 TOP/BOTTOM으로 분리하여 저장
  ```python
  # 저장 예시
  cached_results = {
      'TOP': ['P001', 'P002'],
      'BOTTOM': ['P101', 'P102']
  }
  ```

#### 캐시 활용
- **`get_cached_item_node`**: **[v3 변경]** 캐시에서 코디 세트 가져오기
  - `prepare_cache_cycle_node`에서 설정한 offset 위치의 상품 가져오기
  - TOP과 BOTTOM을 함께 반환 (코디 세트)
  - shown_ids에 두 상품 모두 추가
  - **LLM/벡터 검색 없이** 즉각 응답

- **`send_refinement_prompt_node`**: 캐시 소진 시 사용자에게 안내 메시지 전송

---

### 2.3. Routers: 흐름 제어

`Router`는 현재 `State`를 보고 다음에 어떤 `Node`로 가야 할지 결정하는 함수입니다.

#### 진입 라우터
- **`route_search_entry`**: 그래프 진입 시 첫 번째 의사결정
  1. `SHOW_CACHED` 플래그 확인
  2. 있으면 → `prepare_cache_cycle` (캐시 순환 체크)
  3. 없으면 → `prepare_search_cycle` (새로운 검색 준비)

#### 캐시 순환 제어
- **`route_after_cache_preparation`**: 캐시 순환 가능 여부에 따른 분기
  - `cache_cyclable == True` → `go_cached_loop` (캐시 순환 시작)
  - `cache_cyclable == False` → `no_more_items` (안내 메시지)

#### 작업 분기
- **`decide_work_after_pop`**: 전문가를 꺼낸 후 작업 결정
  - `SHOW_CACHED` 플래그 있음 → `get_cached_item` (캐시에서 가져오기)
  - 플래그 없음 → `run_expert_evaluation` (새로운 분석)

#### 루프 제어
- **`route_expert_loop`**: 전문가 루프 계속 여부 결정
  - `experts_to_run`에 전문가 남음 → `continue_loop` (다음 전문가)
  - 모두 완료 → `END` (그래프 종료)

---

## 3. 시나리오별 동작 과정: 그래프는 어떻게 움직이는가?

### 시나리오 1: 최초 검색 요청 (v3)

> 사용자: "이번 주말 데이트 때 입을 옷 좀 추천해줘."

1. **[진입]** `route_search_entry`는 새로운 검색 요청임을 인지하고 **`prepare_search_cycle`** 경로 선택

2. **[검색 준비]** `prepare_search_cycle_node`가 3명의 전문가 설정
   ```python
   experts_to_run = ['color_expert', 'style_analyst', 'fitting_coordinater']
   ```

3. **[전문가 루프 - color_expert]**
   - `pop_next_expert_node`가 `'color_expert'`를 꺼냄
   - `decide_work_after_pop`은 `'run_expert_evaluation'` 선택
   - `external_llm_node`가 "밝은 톤 상의와 청바지 하의의 조화" 분석 생성
   - **[v3]** `expert_opinions['color_expert']`에 저장
   - `search_node`가 벡터 검색 수행
   - **[v3]** 결과를 TOP/BOTTOM으로 분리 저장:
     ```python
     expert_search_cache['color_expert'] = {
         'TOP': ['P001', 'P002', 'P003'],
         'BOTTOM': ['P101', 'P102', 'P103']
     }
     ```
   - 첫 번째 코디: P001(상의) + P101(하의) 사용자에게 표시

4. **[루프 반복]** `style_analyst`, `fitting_coordinater`도 동일하게 진행

5. **[종료]** 3명의 전문가가 각각 추천한 3개의 코디(총 9개 상품) 표시

---

### 시나리오 2: "다른 코디 보여줘" (캐시 활용 - v3)

> 사용자: "음... 다 좋은데 다른 코디도 좀 볼 수 있을까?"

1. **[진입]** `information_update_node`가 조건 변경 없음 감지
   ```python
   last_updated_fields = ['__SHOW_CACHED__']
   ```
   `route_search_entry`는 **`prepare_cache_cycle`** 경로 선택

2. **[캐시 체크]** `prepare_cache_cycle_node` 실행
   - 각 전문가의 캐시 확인:
   ```python
   # color_expert 체크
   current_offset = 0
   top_list = ['P001', 'P002', 'P003']
   bottom_list = ['P101', 'P102', 'P103']
   shown_ids = {'P001', 'P101'}  # 첫 번째 코디 이미 표시
   
   # offset=0: P001, P101 → 이미 shown_ids에 있음 → skip
   # offset=1: P002, P102 → 둘 다 shown_ids에 없음 → 발견!
   updated_offsets['color_expert'] = 1
   ```
   - **[v3]** 모든 전문가가 TOP-BOTTOM 쌍을 찾으면 `cache_cyclable = True`

3. **[캐시 순환 루프]**
   - `pop_next_expert_node`가 `'color_expert'`를 꺼냄
   - `decide_work_after_pop`이 **`get_cached_item`** 선택
   - `get_cached_item_node` 실행:
     ```python
     current_offset = 1  # prepare에서 설정됨
     top_product_id = top_list[1]  # 'P002'
     bottom_product_id = bottom_list[1]  # 'P102'
     # 두 상품을 함께 반환 (코디 세트)
     ```
   - **[v3]** 저장된 전문가 의견도 함께 표시 가능
   - **(LLM, 벡터 검색 없음!)**

4. **[루프 반복]** `style_analyst`, `fitting_coordinater`도 각자의 다음 코디 표시

5. **[종료]** 사용자는 즉각적으로 3개의 새로운 코디 추천 받음

---

### 시나리오 3: 캐시 소진 (v3)

> 사용자: (여러 번 "다른 거 보여줘"를 반복한 후) "더 없어?"

**상황**: 
```python
expert_search_cache['color_expert'] = {
    'TOP': ['P001', 'P002', 'P003'],
    'BOTTOM': ['P101', 'P102', 'P103']
}
expert_offsets['color_expert'] = 3  # 모든 코디 표시 완료
shown_ids = {'P001', 'P101', 'P002', 'P102', 'P003', 'P103'}
```

1. **[진입 및 판단]** `prepare_cache_cycle_node` 실행
   ```python
   current_offset = 3
   len(top_list) = 3, len(bottom_list) = 3
   # offset >= min(len) → 더 이상 보여줄 쌍 없음
   found_pair = False
   can_cycle = False
   ```

2. **[라우팅]** `route_after_cache_preparation`이 **`no_more_items`** 선택

3. **[안내]** `send_refinement_prompt_node` 실행
   > "추천해 드릴 만한 다른 상품을 모두 보여드렸어요. 원하시는 스타일을 더 자세히 알려주시겠어요?"

4. **[종료]** 사용자가 새로운 조건을 입력하면 다시 시나리오 1로

---

### 시나리오 4: 조건 변경 후 재검색 (v3)

> 사용자: "아까 본 거 말고 좀 더 포멀한 스타일로 보여줘."

1. **[조건 분석]** `information_update_node` 실행
   ```python
   # 'style' 필드 변경 감지
   update_data = {'style': '포멀'}
   
   # [v3 변경] 캐시 초기화
   return {
       StateName.CLOTH_SEARCH: updated_search_info,
       StateName.LAST_UPDATED_FIELDS: ['style'],
       StateName.EXPERT_SEARCH_CACHE: {},       # 초기화
       StateName.SHOWN_IN_PRODUCT_IDS: set(),   # 초기화
       StateName.EXPERT_OFFSETS: {              # 리셋
           'color_expert': 0,
           'style_analyst': 0,
           'fitting_coordinater': 0
       }
   }
   ```

2. **[재검색]** 캐시가 초기화되었으므로 시나리오 1과 동일하게 새로운 벡터 검색 수행

3. **[결과]** 포멀 스타일의 새로운 코디 추천

---

## 4. v3의 주요 이점

### 1. 코디 일관성 보장
- TOP-BOTTOM 쌍 단위 관리로 불완전한 코디 방지
- 전문가의 의도가 반영된 조화로운 코디 제공

### 2. 메모리 효율성
- product_id만 캐시에 저장 (상세 정보는 MongoDB 조회)
- LangGraph State 크기 최소화
- 실시간 가격/재고 정보 반영 가능

### 3. 전문가 의견 보존
- 모든 전문가의 분석 결과 누적 저장
- 캐시 표시 시에도 맥락 제공 가능
- 디버깅 및 로깅 용이

### 4. 유연한 캐시 관리
- 조건 변경 시 자동 초기화
- 중복 방지 메커니즘 강화
- 확장 가능한 구조 (부분 순환 전환 가능)

### 5. 사용자 경험 향상
- 첫 검색: 깊이 있는 분석 (LLM + 벡터 검색)
- 이후 요청: 즉각 응답 (캐시 활용)
- 자연스러운 코디 탐색 흐름

---

## 5. 향후 개선 가능성

### 부분 순환 지원
현재는 전체 중단 구조이지만, 필요시 부분 순환으로 전환 가능:
```python
# 전체 중단 (현재)
if not all_experts_have_pair:
    can_cycle = False

# 부분 순환 (옵션)
experts_with_items = [expert for expert in experts if has_pair]
return {
    StateName.EXPERTS_TO_RUN: experts_with_items,  # 가능한 전문가만
    StateName.CACHE_CYCLABLE: len(experts_with_items) > 0
}
```

### 리랭킹 추가
- 벡터 검색 결과에 대한 reranking 적용
- 사용자 선호도 학습 반영

### 캐시 크기 조정
- config 기반 limit 설정
- 전문가별 다른 캐시 크기

### 전문가 선택적 실행
- "색상 전문가 추천만 다시 보기" 같은 세밀한 제어
- 사용자 피드백 기반 전문가 필터링

