# ruff: noqa: E501
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

from caption.models.base_types import (
    BottomFitType,
    BottomLengthType,
    BottomPatternType,
    PrimaryColor,
    SleeveLength,
    StyleTag,
    TopFitType,
    TopPatternType,
    TPOTag,
)


# --- Enums for Fashion Attributes ---
# TODO : 여기는 caption 모듈에서 정의해도 될듯?
class MainCategory(str, Enum):
    """주요 카테고리"""

    TOP = '상의'
    BOTTOM = '하의'


# class TopSubCategory(str, Enum):
#     """상의 하위 카테고리"""

#     SHORT_SLEEVE_SHIRT = '반소매'
#     SHIRT_BLOUSE = '셔츠-블라우스'
#     PIQUE_COLLAR_T_SHIRT = '피케-카라티셔츠'
#     HOODIE = '후드티셔츠'
#     SWEATSHIRT = '맨투맨-스웨트'
#     LONG_SLEEVE_SHIRT = '긴소매-티셔츠'
#     SLEEVELESS_SHIRT = ('민소매-티셔츠',)


# class BottomSubCategory(str, Enum):
#     """하의 하위 카테고리"""

#     DENIM_PANTS = '데님팬츠'
#     TRAINING_JOGGER_PANTS = '트레이닝-조거팬츠'
#     LEGGINGS = '레깅스'
#     OTHER_BOTTOMS = '기타하의'
#     SUIT_SLACKS = '슈트팬츠-슬랙스'
#     SHORT_PANTS = '숏팬츠'
#     JUMPSUIT_OVERALL = '점프슈트-오버울'


class TopFilter(BaseModel):
    """
    사용자 쿼리에서 상의와 관련된 속성을 추출하여 구조화된 필터로 변환합니다.
    주의: 쿼리에 명시적으로 언급된 정보만 추출하며, 유추는 절대 금지됩니다.
    """

    # sub_category: Annotated[
    #     TopSubCategory,
    #     Field(
    #         description="""사용자 쿼리에서 언급된 상의 하위 카테고리.
    #                - 가능한 값: '반소매', '셔츠-블라우스', '후드티셔츠', '맨투맨-스웨트', '민소매-티셔츠'.
    #                - 쿼리에 해당 정보가 없으면 None으로 설정."""
    #     ),
    # ]
    color: Annotated[
        PrimaryColor,
        Field(
            description="""사용자 쿼리에서 언급된 색상.
                   - 가능한 값: '화이트', '그레이', '블랙', '레드', '핑크', '옐로우', '오렌지', '그린', '블루', '퍼플', '브라운', '베이지', '데님', '메탈릭', '멀티컬러'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    style_tags: Annotated[
        list[StyleTag],
        Field(
            description="""사용자 쿼리에서 명시적으로 언급된 스타일 태그.
                   - 가능한 값: '모던', '심플 베이직', '캐주얼', '스트릿', '포멀', '스포티', '아웃도어', '레트로', '유니크'.
                   - '편한', '멋진'과 같은 모호한 표현은 매칭하지 않습니다. 쿼리에 해당 정보가 없으면 빈 리스트 []로 설정."""
        ),
    ]
    tpo_tags: Annotated[
        list[TPOTag],
        Field(
            description="""사용자 쿼리에서 명시적으로 언급된 TPO(시간, 장소, 상황) 태그.
                   - 가능한 값: '데일리', '오피스', '격식', '데이트', '여행', '파티', '운동', '홈웨어'.
                   - 쿼리에 해당 정보가 없으면 빈 리스트 []로 설정."""
        ),
    ]
    fit: Annotated[
        TopFitType,
        Field(
            description="""사용자 쿼리에서 언급된 핏 타입.
                   - 가능한 값: '슬림 핏', '레귤러 핏/스탠다드 핏', '오버사이즈 핏'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    pattern_type: Annotated[
        TopPatternType,
        Field(
            description="""사용자 쿼리에서 언급된 패턴 타입.
                   - 가능한 값: '무지/솔리드', '스트라이프', '체크', '도트', '플로럴', '애니멀 프린트', '페이즐리', '아가일', '기하학', '타이포그래피/레터링', '기타'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    length: Annotated[
        SleeveLength,
        Field(
            description="""사용자 쿼리에서 언급된 소매 기장.
                   - 가능한 값: '민소매', '반소매', '5부/7부', '긴소매'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    rewritten_query: Annotated[
        str, Field(description="""추출된 필터 값과 사용자의 원래 쿼리 내용을 조합하여 자연스러운 문장 형태로 재작성된 쿼리.""")
    ]


# 하의 전용 모델
class BottomFilter(BaseModel):
    """
    사용자 쿼리에서 하의와 관련된 속성을 추출하여 구조화된 필터로 변환합니다.
    주의: 쿼리에 명시적으로 언급된 정보만 추출하며, 유추는 절대 금지됩니다.
    """

    # sub_category: Annotated[
    #     BottomSubCategory,
    #     Field(
    #         description="""사용자 쿼리에서 언급된 하의 하위 카테고리.
    #                - 가능한 값: '데님팬츠', '트레이닝-조거팬츠', '레깅스', '기타하의', '슈트팬츠-슬랙스', '숏팬츠', '점프슈트-오버울'.
    #                - 쿼리에 해당 정보가 없으면 None으로 설정."""
    #     ),
    # ]
    color: Annotated[
        PrimaryColor,
        Field(
            description="""사용자 쿼리에서 언급된 색상.
                   - 가능한 값: '블랙', '그레이', '레드', '핑크', '옐로우', '오렌지', '그린', '블루', '퍼플', '브라운', '베이지', '데님', '메탈릭', '멀티컬러'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    style_tags: Annotated[
        list[StyleTag],
        Field(
            description="""사용자 쿼리에서 명시적으로 언급된 스타일 태그.
                   - 가능한 값: '모던', '심플 베이직', '캐주얼', '스트릿', '포멀', '스포티', '아웃도어', '레트로', '유니크'.
                   - '편한', '멋진'과 같은 모호한 표현은 매칭하지 않습니다. 쿼리에 해당 정보가 없으면 빈 리스트 []로 설정."""
        ),
    ]
    tpo_tags: Annotated[
        list[TPOTag],
        Field(
            description="""사용자 쿼리에서 명시적으로 언급된 TPO(시간, 장소, 상황) 태그.
                   - 가능한 값: '데일리', '오피스', '격식', '데이트', '여행', '파티', '운동', '홈웨어'.
                   - 쿼리에 해당 정보가 없으면 빈 리스트 []로 설정."""
        ),
    ]
    fit: Annotated[
        BottomFitType,
        Field(
            description="""사용자 쿼리에서 언급된 핏 타입.
                   - 가능한 값: '스트레이트 핏', '슬림 핏', '테이퍼드 핏', '와이드 핏', '부츠컷 핏', '배기 핏', '조거 핏'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    pattern_type: Annotated[
        BottomPatternType,
        Field(
            description="""사용자 쿼리에서 언급된 패턴 타입.
                   - 가능한 값: '무지', '스트라이프', '체크', '카모플라쥬', '워싱 (데님 전용)', '기타 패턴'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    length: Annotated[
        BottomLengthType,
        Field(
            description="""사용자 쿼리에서 언급된 기장.
                   - 가능한 값: '숏 바지', '크롭 바지', '롱 바지'.
                   - 쿼리에 해당 정보가 없으면 None으로 설정."""
        ),
    ]
    rewritten_query: Annotated[
        str, Field(description="""추출된 필터 값과 사용자의 원래 쿼리 내용을 조합하여 자연스러운 문장 형태로 재작성된 쿼리.""")
    ]


# ⭐️ 한 번의 호출로 모든 결과를 담을 최상위 Pydantic 모델
class SingleCallAnalysisResult(BaseModel):
    """사용자 쿼리 한 번에 대한 전체 분석 결과"""

    analyzed_items: list[TopFilter | BottomFilter] = Field(..., description='사용자 쿼리에서 식별된 모든 의류 아이템의 분석 결과 리스트')


# =====================================
# Two Step Query Analysis Models
# =====================================
class IdentifiedItem(BaseModel):
    item_type: Annotated[MainCategory, Field(description="분석된 아이템 타입 (예: '상의', '하의')")]
    raw_query: Annotated[str, Field(description='해당 아이템에 대한 원본 쿼리 내용')]


class InitialAnalysis(BaseModel):
    items: Annotated[list[IdentifiedItem], Field(description='분석된 아이템 리스트')]
    common_context: Annotated[str, Field(description='모든 아이템에 공통으로 적용되는 TPO, 분위기 등의 문맥 정보')]
