"""
상품 상의 속성 관련 Pydantic 모델 정의 모듈
"""
from typing import Annotated
from pydantic import BaseModel, Field
from .base_types import (
    BottomFitType, BottomClosureType, BottomLengthType, BottomPatternType, StyleTag, TPOTag
)


class BottomPatternInfo(BaseModel):
    """하의 패턴 정보"""
    type: Annotated[BottomPatternType, Field(..., description="하의 주요 패턴 타입 선택", examples=["무지" ,"스트라이프" , "체크" , "카모플라쥬" , "워싱" , "기타 패턴"])]
    description: Annotated[str, Field(..., description="하의 패턴에 대한 상세 설명 )")]


class BottomClosureInfo(BaseModel):
    """하의 여밈/장식 정보"""
    type: Annotated[BottomClosureType, Field(..., description="여밈/장식 타입 선택", examples=["여밈 없음", "버튼", "지퍼", "스트링", "후크"])]
    description: Annotated[str, Field(..., description="여밈/장식 요소에 대한 상세 설명 )")] 


class CommonAttributes(BaseModel):
    """
    하의 정면/후면 공통적으로 가지는 속성 정보
    # """
    bottom_length: Annotated[BottomLengthType, Field(
        ..., 
        description="하의 기장 타입 선택",
        examples=["숏 바지", "크롭 바지", "롱 바지"]
    )]



class BottomAttributes(BaseModel):
    """
    하의의 정면 또는 후면에서 나타나는 구체적인 디자인 요소들을 정의합니다.
    패턴과 여밈/장식 요소는 하의의 개성과 기능성을 나타내는 중요한 속성입니다.
    """
    pattern: Annotated[BottomPatternInfo, Field(
        ..., 
        description="하의에 적용된 주요 패턴 타입 선택 및 상세 설명"
    )]
    closures_and_embellishments: Annotated[BottomClosureInfo, Field(
        ..., 
        description="하의 주요 여밈 방식 타입 선택 및 상세 설명"
    )]


class SubjectiveAttributes(BaseModel):
    """주관적 속성 Tags - 하의의 핏, 스타일, 착용 상황에 대한 주관적 평가 정보"""
    fit: Annotated[BottomFitType, Field(
        ..., 
        description="하의의 핏 타입을 하나만 선택",
        examples=["스트레이트 핏", "슬림 핏", "테이퍼드 핏", "와이드 핏", "부츠컷 핏", "배기 핏", "조거 핏"]
    )]
    style_tags: Annotated[list[StyleTag], Field(
        default_factory=list, 
        description="하의의 스타일 태그들을 다중 선택 가능 (모던, 캐주얼, 스트릿, 포멀 등)",
        examples=[["캐주얼", "스트릿"], ["모던", "심플 베이직"]]
    )]
    tpo_tags: Annotated[list[TPOTag], Field(
        default_factory=list, 
        description="하의의 착용 상황(TPO) 태그들을 다중 선택 가능 (데일리, 오피스, 데이트 등)",
        examples=[["데일리", "데이트"], ["오피스", "격식"]]
    )]


class StructuredAttributes(BaseModel):
    """구조화된 속성 전체 - 하의의 모든 속성 정보를 체계적으로 분류하여 저장"""
    common: Annotated[CommonAttributes, Field(
        ...,
        description="하의의 정면과 후면에서 공통적으로 나타나는 속성 (기장 길이)"
    )]
    front: Annotated[BottomAttributes, Field(
        ...,
        description="하의 정면에서만 나타나는 구체적인 디자인 요소"
    )]
    back: Annotated[BottomAttributes, Field(
        ...,
        description="하의 후면에서만 나타나는 구체적인 디자인 요소"
    )]
    subjective: Annotated[SubjectiveAttributes, Field(
        ...,
        description="하의의 핏, 스타일, 착용 상황에 대한 주관적 태그 정보"
    )]


class ImageCaptions(BaseModel):
    """하의 이미지 캡션 모음"""
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
        description="하의의 모든 디자인 디테일을 종합한 설명문으로 색상, 소재, 장식 요소, 패턴, 여밈 방식 등을 포함"
    )]
    style_description: Annotated[str, Field(
        ..., 
        description="색상 정보를 제외한 주어진 하의에 대한 디테일한 스타일에 대한 설명문"
    )]
    tpo_context_description: Annotated[str, Field(
        ..., 
        description="색상 정보를 제외한 해당 의류를 착용하기 어울리는 상황과 분위기애 대한 설명문"
    )]
    comprehensive_description: Annotated[str, Field(
        ...,
        description="하의의 모든 정보를 종합한 완전한 설명문으로 공통 속성, 색상 정보, 디자인 요소를 모두 포함"
    )]




