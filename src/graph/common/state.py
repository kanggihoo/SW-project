from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import Field

from graph.model.graph_schemas import ClothSearch


# ======================================================================
# 그래프 전체 state 상태 정의
# ======================================================================
# 여기에서의 Field의 유효성 검사나 default , default_factory는 실제로 동작하지 않음.
class State(TypedDict):
    # ----------------------------------------- 맨 처음 API 요청시 업데이트 되는 state -----------------------------------------
    messages: Annotated[list[BaseMessage], add_messages]
    user_message: str
    is_predefined_template: Annotated[bool, Field(description='미리 정의된 템플릿 클릭 여부. True: 템플릿, False: 직접 입력')]
    product_id: str
    user_name: str

    # ----------------------------------------- 의도 분류 노드에서 업데이트 되는 state -----------------------------------------
    intent: str
    # chatbot fallback 플래그
    is_unclear_fallback: Annotated[bool, Field(description='UNCLEAR 상황에서 chatbot으로 폴백되었는지 여부', default=False)]

    # ----------------------------------------- 정보 수집 노드에서 업데이트 되는 state -----------------------------------------
    cloth_search: ClothSearch
    is_info_gathering_complete: bool

    # ----------------------------------------- 정보 업데이트 노드에서 업데이트 되는 state -----------------------------------------
    last_updated_fields: Annotated[list[str], Field(description='마지막으로 업데이트된 필드')]

    # ----------------------------------------- prepare_search_cycle / prepare_cache_cycle / pop_next_expert 노드에서 업데이트 되는 state -----------------------------------------
    experts_to_run: Annotated[list[str], Field(description='실행할 전문가 목록')]

    # ----------------------------------------- prepare_cache_cycle 노드에서 업데이트 되는 state -----------------------------------------
    cache_cyclable: Annotated[bool, Field(description='캐시 순환 가능 여부')]

    # ----------------------------------------- pop_next_expert 노드에서 업데이트 되는 state -----------------------------------------
    current_expert: Annotated[str, Field(description='현재 실행중인 전문가')]

    # ----------------------------------------- run_expert_evaluation 노드에서 업데이트 되는 state -----------------------------------------
    expert_opinions: Annotated[dict[str, str], Field(description='전문가별 의견 저장. {"expert_name": "expert_opinion"}')]

    # ----------------------------------------- search 노드에서 업데이트 되는 state -----------------------------------------
    # 벡터 검색 결과를 전문가별로 저장할 딕셔너리입니다.
    expert_search_cache: Annotated[
        dict[str, dict[str, list[str]]],
        Field(
            description='전문가별 벡터 검색 결과를 저장하는 캐시. {"expert_name": {"TOP": [product_id1, ...], "BOTTOM": [product_id2, ...]}}',
            default_factory=dict,
        ),
    ]
    # 기존 상태의 역할을 명확히 하여, 캐시의 어느 위치까지 보여줬는지 추적하는 인덱스로 사용합니다.
    expert_offsets: Annotated[
        dict[str, int],
        Field(
            description='전문가별 캐시 결과의 현재 인덱스',
            default_factory=lambda: {
                'color_expert': 0,
                'style_analyst': 0,
                'fitting_coordinater': 0,
            },
        ),
    ]
    # "다른 거 보여줘" 한 사이클 내에서 중복 추천을 방지하기 위한 리스트입니다.
    shown_in_product_ids: Annotated[
        set[str],
        Field(
            description='"다른거 보여줘" 사이클 내에서 이미 보여준 상품 ID 목록',
            default_factory=set,
        ),
    ]
