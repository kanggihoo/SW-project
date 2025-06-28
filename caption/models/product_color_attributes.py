from typing import Annotated
from pydantic import BaseModel, Field
from .base_types import (
    PrimaryColor, Brightness, Saturation
)


class ColorAttribute(BaseModel):
    """색상 채도/명도 타입"""
    brightness: Annotated[Brightness, Field(
        ..., 
        description="색상의 명도 특성을 선택",
        examples=["아주 밝음", "밝음", "중간 밝기", "어두움", "아주 어두움"]
    )]
    saturation: Annotated[Saturation, Field(
        ..., 
        description="색상의 채도 특성을 선택",
        examples=["아주 낮음", "낮음", "중간 채도", "높음", "아주 높음"]
    )]

class ColorInfo(BaseModel):
    """의류 색상 정보"""
    name: Annotated[PrimaryColor, Field(
        ..., 
        description="의류의 주요 색상타입 선택",
        examples=["블루", "핑크", "블랙", "화이트", "그레이", "레드", "그린", "옐로우", "오렌지", "퍼플", "브라운", "베이지", "데님", "메탈릭", "멀티컬러"]
    )]
    hex: Annotated[str, Field(
        ..., 
        description="의류의 주요 색상에 대한 HEX 코드 (6자리 16진수)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        examples=["#4A90E2", "#FFC0CB", "#000000", "#FFFFFF", "#808080", "#FF0000"]
    )]
    attributes: Annotated[ColorAttribute, Field(..., description="의류의 주요 색상에 대한 채도,명도 특성을 나타내는 속성 태그들")]

