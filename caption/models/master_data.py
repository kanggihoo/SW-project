"""
마스터 데이터 및 VLM 출력 모델 정의 모듈
"""

from typing import Annotated
from pydantic import BaseModel, Field
from .top_product_attributes import  StructuredAttributes , ImageCaptions
from .product_color_attributes import ColorInfo
from .text_image_attributes import MultiSizeInfo

# class ProductMasterData(BaseModel):
#     """상품 마스터 데이터 (전체 구조)"""
#     product_group_id: Annotated[str, Field(..., description="상품 그룹 식별자")]
#     vlm_extraction_date: Annotated[datetime, Field(
#         default_factory=datetime.now,
#         description="VLM 추출 날짜"
#     )]
#     base_product_info: Annotated[BaseProductInfo, Field(
#         description="기본 상품 정보 (딥 캡셔닝 결과)"
#     )]
#     variants: Annotated[list[ProductVariant], Field(
#         description="상품 변형들 (색상별)"
#     )]

#     class Config:
#         """Pydantic 설정"""
#         json_encoders = {
#             datetime: lambda v: v.isoformat()
#         }


# VLM 단계별 출력 모델들
class DeepCaptioningTopOutput(BaseModel):
    """상의의 모든 구조화된 속성과 이미지 캡션을 포함한 종합 분석 결과"""
    structured_attributes: Annotated[StructuredAttributes, Field(
        description="상의의 모든 구조화된 속성 정보. 공통 속성(소매길이, 넥라인), 정면/후면별 디자인 요소(패턴, 여밈), 주관적 속성(핏, 스타일, TPO)을 체계적으로 분류하여 저장"
    )]
    image_captions: Annotated[ImageCaptions, Field(
        description="상의의 다양한 용도별 이미지 캡션 모음. 정면/후면 전용 설명, 디자인 디테일, 스타일 분위기, TPO 상황, 종합 설명 등 6가지 관점의 상세한 텍스트 캡션"
    )]


class SimpleAttributeOutput(BaseModel):
    """단순 속성 추출 단계 출력 - 주어진 의류의 색상 정보만을 전문적으로 분석한 결과"""
    color_info: Annotated[list[ColorInfo], Field(
        description="의류의 색상 분석 결과. 대표 색상명, 정확한 HEX 코드, 색상 속성 태그(채도/명도)를 포함한 완전한 색상 정보"
    )]

class TextImageOCROutput(BaseModel):
    """텍스트 이미지에서 추출된 의류 정보 종합"""
    material_info: Annotated[str|None, Field(
        default=None,
        description="의류의 소재 구성 정보 (예: '면 100%', '울 80%, 나일론 20%', '폴리에스터 65%, 레이온 30%, 스판덱스 5%')"
    )]
    size_info: Annotated[MultiSizeInfo, Field(
        ...,
        description="상세 사이즈 정보 (실측)"
    )]
    care_info: Annotated[str|None, Field(
        default=None,
        description="의류 세탁 및 관리 방법"
    )]
    product_description: Annotated[str|None, Field(
        default=None,
        description="의류의 소개 문구, 주요특징을 종합하여 요약한 상품 설명"
    )]


# class CombinedVLMOutput(BaseModel):
#     """결합된 VLM 출력 (전체)"""
#     product_group_id: str = Field(description="상품 그룹 식별자")
#     deep_captioning_result: DeepCaptioningTopOutput = Field(
#         description="딥 캡셔닝 결과"
#     )
#     simple_attribute_result: SimpleAttributeOutput = Field(
#         description="단순 속성 추출 결과"
#     )

#     def to_master_data(self) -> ProductMasterData:
#         """마스터 데이터 형태로 변환"""
#         return ProductMasterData(
#             product_group_id=self.product_group_id,
#             base_product_info=self.deep_captioning_result.base_product_info,
#             variants=self.simple_attribute_result.variants
#         ) 