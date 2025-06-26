"""
상품 변형(색상별) 모델 정의 모듈
"""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
from .base_types import ColorInfo


class ColorDetail(BaseModel):
    """상세 색상 정보"""
    primary: ColorInfo = Field(description="주 색상")
    secondary: List[ColorInfo] = Field(default=[], description="부 색상들")
    all_colors: List[str] = Field(description="모든 색상명 목록")
    all_color_attributes: List[str] = Field(description="모든 색상 속성 목록")


class VariantEmbeddingCaptions(BaseModel):
    """변형별 임베딩 캡션"""
    front_text_specific: Optional[str] = Field(
        default=None,
        description="정면 이미지 전용 텍스트 (색상 포함)"
    )
    back_text_specific: Optional[str] = Field(
        default=None,
        description="후면 이미지 전용 텍스트 (색상 포함)"
    )
    comprehensive_description: Optional[str] = Field(
        default=None,
        description="종합 설명 (공통정보 + 색상정보 결합)"
    )


class ProductVariant(BaseModel):
    """상품 변형 (개별 SKU)"""
    sku_id: str = Field(description="SKU 식별자")
    is_representative: bool = Field(
        default=False,
        description="대표 이미지 여부"
    )
    product_image_url: HttpUrl = Field(description="상품 이미지 URL")
    color: ColorDetail = Field(description="색상 상세 정보")
    embedding_captions: VariantEmbeddingCaptions = Field(
        description="변형별 임베딩 캡션"
    ) 