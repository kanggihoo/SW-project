"""
마스터 데이터 및 VLM 출력 모델 정의 모듈
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from .product_attributes import BaseProductInfo
from .variant_models import ProductVariant


class ProductMasterData(BaseModel):
    """상품 마스터 데이터 (전체 구조)"""
    product_group_id: str = Field(description="상품 그룹 식별자")
    vlm_extraction_date: datetime = Field(
        default_factory=datetime.now,
        description="VLM 추출 날짜"
    )
    base_product_info: BaseProductInfo = Field(
        description="기본 상품 정보 (딥 캡셔닝 결과)"
    )
    variants: List[ProductVariant] = Field(
        description="상품 변형들 (색상별)"
    )

    class Config:
        """Pydantic 설정"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# VLM 단계별 출력 모델들

class DeepCaptioningOutput(BaseModel):
    """딥 캡셔닝 단계 출력 (공통 정보만)"""
    base_product_info: BaseProductInfo = Field(
        description="기본 상품 정보 (색상 제외한 모든 공통 정보)"
    )


class SimpleAttributeOutput(BaseModel):
    """단순 속성 추출 단계 출력 (색상 정보만)"""
    variants: List[ProductVariant] = Field(
        description="개별 SKU별 색상 정보"
    )


class CombinedVLMOutput(BaseModel):
    """결합된 VLM 출력 (전체)"""
    product_group_id: str = Field(description="상품 그룹 식별자")
    deep_captioning_result: DeepCaptioningOutput = Field(
        description="딥 캡셔닝 결과"
    )
    simple_attribute_result: SimpleAttributeOutput = Field(
        description="단순 속성 추출 결과"
    )

    def to_master_data(self) -> ProductMasterData:
        """마스터 데이터 형태로 변환"""
        return ProductMasterData(
            product_group_id=self.product_group_id,
            base_product_info=self.deep_captioning_result.base_product_info,
            variants=self.simple_attribute_result.variants
        ) 