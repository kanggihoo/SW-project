"""
상품 속성 관련 Pydantic 모델 정의 모듈
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .base_types import (
    Neckline, SleeveLength, PatternInfo, ClosureInfo, 
    FitType, StyleTag, TPOTag
)


class CommonAttributes(BaseModel):
    """공통 속성"""
    category_l1: str = Field(description="대분류 (예: 상의)")
    category_l2: str = Field(description="중분류 (예: 셔츠)")
    sleeve_length: SleeveLength = Field(description="소매 길이")
    neckline: Neckline = Field(description="넥라인")


class FrontAttributes(BaseModel):
    """정면 속성"""
    pattern: Optional[PatternInfo] = Field(default=None, description="패턴 정보")
    closures_and_embellishments: List[ClosureInfo] = Field(
        default=[], 
        description="여밈 및 장식 요소들"
    )


class BackAttributes(BaseModel):
    """후면 속성"""
    closures_and_embellishments: List[ClosureInfo] = Field(
        default=[], 
        description="여밈 및 장식 요소들"
    )


class SubjectiveAttributes(BaseModel):
    """주관적 속성"""
    fit: FitType = Field(description="핏 타입")
    style_tags: List[StyleTag] = Field(description="스타일 태그")
    mood_tags: List[str] = Field(description="무드 태그 (자유형식)")
    tpo_tags: List[TPOTag] = Field(description="TPO 태그")


class StructuredAttributes(BaseModel):
    """구조화된 속성 전체"""
    common: CommonAttributes = Field(description="공통 속성")
    front: FrontAttributes = Field(description="정면 속성")
    back: BackAttributes = Field(description="후면 속성")
    subjective: SubjectiveAttributes = Field(description="주관적 속성")


class EmbeddingCaptions(BaseModel):
    """임베딩용 캡션들"""
    design_details_description: str = Field(
        description="디자인 디테일 설명 (색상 미포함)"
    )
    style_vibe_description: str = Field(
        description="스타일/무드 설명 (색상 미포함)"
    )
    tpo_context_description: str = Field(
        description="TPO 상황 설명 (색상 미포함)"
    )


class BaseProductInfo(BaseModel):
    """기본 상품 정보 (딥 캡셔닝 결과)"""
    structured_attributes: StructuredAttributes = Field(
        description="구조화된 속성들"
    )
    embedding_captions: EmbeddingCaptions = Field(
        description="임베딩용 캡션들"
    ) 