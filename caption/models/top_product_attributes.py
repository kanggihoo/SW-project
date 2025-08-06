"""
상품 상의 속성 관련 Pydantic 모델 정의 모듈
"""

from typing import Annotated
from pydantic import BaseModel, Field
from .base_types import (
    Neckline, SleeveLength,
    TopFitType, StyleTag, TPOTag, TopPatternType, TopClosureType
)


class TopPatternInfo(BaseModel):
    """상의 패턴 정보"""
    type: Annotated[TopPatternType, Field(..., description="상의 주요 패턴 타입 선택", examples=["스트라이프", "체크", "플로럴", "지오메트릭", "솔리드"])]
    description: Annotated[str, Field(..., description="상의 패턴에 대한 상세 설명 (예: 세로 스트라이프, 대형 체크 패턴, 작은 꽃무늬 등)")]


class TopClosureInfo(BaseModel):
    """상의 여밈/장식 정보"""
    type: Annotated[TopClosureType, Field(..., description="여밈/장식 타입 선택", examples=["버튼/단추", "지퍼", "스냅 버튼", "스트링/끈"])]
    description: Annotated[str, Field(..., description="여밈/장식 요소에 대한 상세 설명 (예: 앞면 중앙 버튼 3개, 측면 지퍼, 허리 스트링 등)")] 


class CommonAttributes(BaseModel):
    """
    상의 정면/후면 공통적으로 가지는 속성 정보
    """
    sleeve_length: Annotated[SleeveLength, Field(
        ..., 
        description="상의 소매 길이 타입 선택",
        examples=["민소매", "반소매", "5부/7부", "긴소매"]
    )]
    neckline: Annotated[Neckline, Field(
        ..., 
        description="상의 목부분 디자인 선택",
        examples=["라운드넥", "브이넥", "터틀넥/폴라", "카라", "후드"]
    )]


class TopAttributes(BaseModel):
    """
    상의의 정면 또는 후면에서 나타나는 구체적인 디자인 요소들을 정의합니다.
    패턴과 여밈/장식 요소는 상의의 개성과 기능성을 나타내는 중요한 속성입니다.
    """
    pattern: Annotated[TopPatternInfo, Field(
        ..., 
        description="상의에 적용된 주요 패턴 타입 선택 및 상세 설명"
    )]
    closures_and_embellishments: Annotated[TopClosureInfo, Field(
        ..., 
        description="상의 주요 여밈 방식 타입 선택 및 상세 설명"
    )]

# class BackAttributes(BaseModel):
#     """후면 속성"""
#     closures_and_embellishments: List[ClosureInfo] = Field(
#         default=[], 
#         description="여밈 및 장식 요소들"
#     )


class SubjectiveAttributes(BaseModel):
    """주관적 속성 Tags - 상의의 핏, 스타일, 착용 상황에 대한 주관적 평가 정보"""
    fit: Annotated[TopFitType, Field(
        ..., 
        description="상의의 핏 타입을 하나만 선택",
        examples=["슬림 핏", "레귤러 핏/스탠다드 핏", "오버사이즈 핏"]
    )]
    style_tags: Annotated[list[StyleTag], Field(
        default_factory=list, 
        description="상의의 스타일 태그들을 다중 선택 가능 (모던, 캐주얼, 스트릿, 포멀 등)",
        examples=[["캐주얼", "스트릿"], ["모던", "심플 베이직"]]
    )]
    tpo_tags: Annotated[list[TPOTag], Field(
        default_factory=list, 
        description="상의의 착용 상황(TPO) 태그들을 다중 선택 가능 (데일리, 오피스, 데이트 등)",
        examples=[["데일리", "데이트"], ["오피스", "격식"]]
    )]


class StructuredAttributes(BaseModel):
    """구조화된 속성 전체 - 상의의 모든 속성 정보를 체계적으로 분류하여 저장"""
    common: Annotated[CommonAttributes, Field(
        ...,
        description="상의의 정면과 후면에서 공통적으로 나타나는 속성 (소매 길이, 넥라인 등)"
    )]
    front: Annotated[TopAttributes, Field(
        ...,
        description="상의 정면에서만 나타나는 구체적인 디자인 요소 (패턴, 여밈/장식 등)"
    )]
    back: Annotated[TopAttributes, Field(
        ...,
        description="상의 후면에서만 나타나는 구체적인 디자인 요소 (패턴, 여밈/장식 등)"
    )]
    subjective: Annotated[SubjectiveAttributes, Field(
        ...,
        description="상의의 핏, 스타일, 착용 상황에 대한 주관적 태그 정보"
    )]


class ImageCaptions(BaseModel):
    """이미지 캡션 모음"""
    front_text_specific: Annotated[str, Field(
        ..., 
        description="정면 누끼 이미지 전용 상세 설명문으로 색상, 디자인 요소, 패턴, 여밈 방식 등을 포함"
    )]
    back_text_specific: Annotated[str, Field(
        ..., 
        description="후면 누끼 이미지 전용 상세 설명문으로 색상, 디자인 요소, 패턴, 여밈 방식 등을 포함"
    )]
    design_details_description: Annotated[str, Field(
        ..., 
        description="상의의 모든 디자인 디테일을 종합한 설명문으로 색상, 소재, 장식 요소, 패턴, 여밈 방식 등을 포함"
    )]
    style_description: Annotated[str, Field(
        ..., 
        description="색상 정보를 제외한 주어진 상의에 대한 디테일한 스타일에 대한 설명문"
    )]
    tpo_context_description: Annotated[str, Field(
        ..., 
        description="색상 정보를 제외한 해당 의류를 착용하기 어울리는 상황과 분위기애 대한 설명문"
    )]
    comprehensive_description: Annotated[str, Field(
        ...,
        description="상의의 모든 정보를 종합한 완전한 설명문으로 공통 속성, 색상 정보, 디자인 요소를 모두 포함"
    )]


# class BaseProductInfo(BaseModel):
#     """기본 상품 정보 (딥 캡셔닝 결과)"""
#     structured_attributes: Annotated[StructuredAttributes, Field(
#         description="구조화된 속성들"
#     )]
#     embedding_captions: Annotated[EmbeddingCaptions, Field(
#         description="임베딩용 캡션들"
#     )] 

