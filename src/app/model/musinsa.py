from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union , Annotated


# =================================================================================================
# Base Models & Common Schemas
# =================================================================================================

class MusinsaResponse(BaseModel):
    """무신사 API 응답의 기본 구조"""
    success: bool = Field(..., description="API 호출 성공 여부", example=True)
    message: str = Field(..., description="API 호출 결과 메시지", example="성공적으로 처리하였습니다.")
    data: List[Any] = Field(..., description="API 결과 데이터 (항상 리스트)", default_factory=list)
    error_details: Optional[dict] = Field(None, description="에러 발생 시 상세 정보")

class ErrorResponse(BaseModel):
    """에러 발생 시 응답 모델"""
    detail: str = Field(..., description="에러 상세 내용")

# =================================================================================================
# 1. 사이즈 추천 (get_size_recommend)
# =================================================================================================

class SizeRecommendData(BaseModel):
    """추천 사이즈 데이터"""
    size: Optional[str] = Field(None, description="추천 사이즈", example="XL")
    count: Optional[int] = Field(None, description="해당 사이즈를 구매한 사용자 수", example=10)
    percent: Optional[int] = Field(None, description="해당 사이즈를 구매한 사용자의 비율", example=80)

class SizeRecommendResponse(MusinsaResponse):
    """사이즈 추천 API 응답 모델"""
    data: List[SizeRecommendData] = Field(..., description="사이즈 추천 목록")

# =================================================================================================
# 2. 상품 선택 정보 (get_product_selection_info)
# =================================================================================================

class OptionItem(BaseModel):
    item_id: Optional[int] = Field(None, description="옵션 아이템 ID", example=6831017)
    name: Optional[str] = Field(None, description="옵션 이름", example="M")

class ProductSelectionInfoData(BaseModel):
    """상품 선택 정보 데이터"""
    option_count: Optional[int] = Field(None, description="옵션 개수", example=1)
    first_option_name: Optional[str] = Field(None, description="첫 번째 옵션 이름", example="사이즈")
    secondary_option_name: Optional[str] = Field(None, description="두 번째 옵션 이름", example="")
    first_options: List[OptionItem] = Field(..., description="첫 번째 옵션 목록", default_factory=list)
    secondary_options: List[OptionItem] = Field(..., description="두 번째 옵션 목록", default_factory=list)

class ProductSelectionInfoResponse(MusinsaResponse):
    """상품 선택 정보 API 응답 모델"""
    data: List[ProductSelectionInfoData] = Field(..., description="상품 선택 정보")

# =================================================================================================
# 3. 상품 옵션 및 재고 (get_product_option_stock)
# =================================================================================================

class OptionValue(BaseModel):
    id: Optional[int] = Field(None, description="옵션 값 ID", example=16569117)
    name: Optional[str] = Field(None, description="옵션 값 이름", example="M")
    code: Optional[str] = Field(None, description="옵션 값 코드", example="M")

class OptionFilter(BaseModel):
    name: Optional[str] = Field(None, description="필터 이름", example="사이즈")
    display_type: Optional[str] = Field(None, description="표시 유형", example="DROPDOWN")
    values: List[OptionValue] = Field(..., description="옵션 값 목록", default_factory=list)

class StockInfo(BaseModel):
    option_combination: List[Optional[str]] = Field(..., description="옵션 값 이름 조합", example=["M"])
    option_ids: List[Optional[int]] = Field(..., description="옵션 값 ID 조합", example=[16569117])
    is_sold_out: bool = Field(..., description="품절 여부", example=False)
    is_out_of_stock: bool = Field(..., description="재고 없음 여부", example=False)
    is_deleted: bool = Field(..., description="삭제 여부", example=False)

class ProductOptionStockData(BaseModel):
    """상품 옵션 및 재고 데이터"""
    product_id: str = Field(..., description="상품 ID", example="4637965")
    option_count: int = Field(..., description="옵션 필터 개수", example=1)
    option_filters: List[OptionFilter] = Field(..., description="옵션 필터 목록")
    stock_by_options: List[StockInfo] = Field(..., description="옵션별 재고 목록")

class ProductOptionStockResponse(MusinsaResponse):
    """상품 옵션 및 재고 API 응답 모델"""
    data: List[ProductOptionStockData] = Field(..., description="상품 옵션 및 재고 정보")

# =================================================================================================
# 4. 상품 실측 사이즈 (get_product_size)
# =================================================================================================

class SizeDetailItem(BaseModel):
    name: Optional[str] = Field(None, description="측정 항목 이름", example="총장")
    value: Optional[float] = Field(None, description="측정 값", example=68.0)

class SizeDetail(BaseModel):
    size_name: Optional[str] = Field(None, description="사이즈 옵션명", example="M")
    items: List[SizeDetailItem] = Field(..., description="실측 항목 목록", default_factory=list)

class ProductSizeData(BaseModel):
    """상품 실측 사이즈 데이터"""
    product_id: str = Field(..., description="상품 ID", example="4447189")
    size_guide_image_url: str = Field(..., description="사이즈 가이드 이미지 URL", example="https://image.musinsa.com/...")
    size_details: List[SizeDetail] = Field(..., description="사이즈별 실측 정보 목록")

class ProductSizeResponse(MusinsaResponse):
    """상품 실측 사이즈 API 응답 모델"""
    data: List[ProductSizeData] = Field(..., description="상품 실측 사이즈 정보")

# =================================================================================================
# 5. 리뷰 요약 정보 (get_review_summary)
# =================================================================================================

class ReviewSummaryData(BaseModel):
    """리뷰 요약 정보 데이터"""
    product_id: str = Field(..., description="상품 ID", example="4637965")
    total_review_count: int = Field(..., description="총 리뷰 수", example=24)
    style_review_count: int = Field(..., description="스타일 리뷰 수", example=5)
    monthly_review_count: int = Field(..., description="한달 사용 리뷰 수", example=1)
    general_review_count: int = Field(..., description="일반, 사진, 상품 리뷰 수 합계", example=18)
    average_rating: float = Field(..., description="리뷰 평점", example=4.8)

class ReviewSummaryResponse(MusinsaResponse):
    """리뷰 요약 정보 API 응답 모델"""
    data: List[ReviewSummaryData] = Field(..., description="리뷰 요약 정보")

# =================================================================================================
# 6. 필터링된 리뷰 개수 (get_filtered_review_count)
# =================================================================================================

class FilteredReviewCountData(BaseModel):
    count: int = Field(..., description="필터링된 조건에 맞는 리뷰 개수", example=2206)

class FilteredReviewCountResponse(MusinsaResponse):
    """필터링된 리뷰 개수 API 응답 모델"""
    data: List[FilteredReviewCountData] = Field(..., description="필터링된 리뷰 개수")

# =================================================================================================
# 7. 리뷰 목록 (get_review_list)
# =================================================================================================

class UserInfo(BaseModel):
    """리뷰 작성자 정보"""
    level: Optional[int] = Field(None, description="사용자 레벨", example="7")
    sex: Optional[str] = Field(None, description="성별", example="남성")
    height_cm: Optional[int] = Field(None, description="키(cm)", example="178")
    weight_kg: Optional[int] = Field(None, description="몸무게(kg)", example="86")

class ReviewData(BaseModel):
    """개별 리뷰 데이터"""
    id: Optional[int] = Field(None, description="리뷰 ID", example=7980094)
    content: Optional[str] = Field(None, description="리뷰 내용", example="정말 무난한 데일리용 입니다...")
    rating: Optional[int] = Field(None, description="평점", example=5)
    goods_option: Optional[str] = Field(None, description="구매한 상품 옵션", example="M")
    created_at: Optional[str] = Field(None, description="작성일", example="2020-01-19T00:15:33.000+09:00")
    like_count: Optional[int] = Field(None, description="좋아요 수", example=10)
    user_info: Optional[UserInfo] = Field(None, description="작성자 정보")

class ReviewListResponse(MusinsaResponse):
    """리뷰 목록 API 응답 모델"""
    data: List[ReviewData] = Field(..., description="리뷰 목록")

# =================================================================================================
# 8. 상품 좋아요 수 (get_product_like_count)
# =================================================================================================
class ProductLikeCountRequest(BaseModel):
    """상품 좋아요 수 요청 모델"""
    relationIds: List[int] | List[str] = Field(..., description="조회할 상품 ID 목록", example=[3522389, 2678375])

class ProductLikeCountData(BaseModel):
    """상품 좋아요 수 데이터"""
    product_id: Optional[Union[str, int]] = Field(None, description="상품 ID", example=4637965)
    count: Optional[int] = Field(None, description="좋아요 수", example=12345)

class ProductLikeCountResponse(MusinsaResponse):
    """상품 좋아요 수 API 응답 모델"""
    data: List[ProductLikeCountData] = Field(..., description="상품 좋아요 목록")

# =================================================================================================
# 9. 상품 통계 (get_product_stats)
# =================================================================================================

class ProductStatsData(BaseModel):
    """상품 통계 데이터"""
    product_view_total: Optional[int] = Field(None, description="최근 1달간 조회수", example=100)
    purchase_total: Optional[int] = Field(None, description="누적 판매 수", example=100)

class ProductStatsResponse(MusinsaResponse):
    """상품 통계 API 응답 모델"""
    data: List[ProductStatsData] = Field(..., description="상품 통계 정보")

# =================================================================================================
# 10. 다른 색상 상품 (get_product_other_color)
# =================================================================================================

class OtherColorProductData(BaseModel):
    """다른 색상 상품 정보"""
    product_id: Optional[int] = Field(None, description="상품 ID", example=3522389)
    goods_name: Optional[str] = Field(None, description="상품명", example="스웨트셔츠 [헤더 베이지]")
    image_url: Optional[str] = Field(None, description="이미지 URL", example="https://image.msscdn.net/...")
    is_sold_out: Optional[bool] = Field(None, description="품절 여부", example=False)

class ProductOtherColorResponse(MusinsaResponse):
    """다른 색상 상품 API 응답 모델"""
    data: List[OtherColorProductData] = Field(..., description="다른 색상 상품 목록")

# =================================================================================================
# 11. 상품 브랜드 및 가격 (get_product_brand_and_price)
# =================================================================================================
class BrandLikesCountRequest(BaseModel):
    """브랜드 좋아요 수 요청 모델"""
    relationIds: List[str] = Field(..., description="조회할 브랜드 ID 목록", example=["markm", "covernat"])

class BrandInfo(BaseModel):
    """브랜드 정보"""
    brand_name: str = Field(..., description="브랜드명 (국문)", example="마크엠")
    brand_english_name: str = Field(..., description="브랜드명 (영문)", example="markm")

class PriceInfo(BaseModel):
    """상품 가격 정보"""
    sale_price: int = Field(..., description="판매가", example=9990)
    original_price: int = Field(..., description="정가", example=89000)
    discount_rate: int = Field(..., description="할인율", example=89)
    is_on_sale: bool = Field(..., description="세일 여부", example=True)

class ProductBrandAndPriceData(BaseModel):
    """상품 브랜드 및 가격 데이터"""
    brand_info: BrandInfo = Field(..., description="브랜드 정보")
    price_info: PriceInfo = Field(..., description="상품 가격 정보")

class ProductBrandAndPriceResponse(MusinsaResponse):
    """상품 브랜드 및 가격 API 응답 모델"""
    data: List[ProductBrandAndPriceData] = Field(..., description="상품 브랜드 및 가격 정보")

# =================================================================================================
# 12. 브랜드 좋아요 수 (get_brand_likes_count)
# =================================================================================================

class BrandLikesCountData(BaseModel):
    """브랜드 좋아요 수 데이터"""
    brand_name: Optional[str] = Field(None, description="브랜드명", example="markm")
    count: Optional[int] = Field(None, description="좋아요 수", example=12345)

class BrandLikesCountResponse(MusinsaResponse):
    """브랜드 좋아요 수 API 응답 모델"""
    data: List[BrandLikesCountData] = Field(..., description="브랜드 좋아요 목록")

# =================================================================================================
# 13. 색상 코드 (get_color_code)
# =================================================================================================

class ColorCodeData(BaseModel):
    """색상 코드 데이터"""
    color_id: Optional[Union[str, int]] = Field(None, description="색상 ID", example=1)
    color_name: Optional[str] = Field(None, description="색상명", example="블랙")

class ColorCodeResponse(MusinsaResponse):
    """색상 코드 API 응답 모델"""
    data: List[ColorCodeData] = Field(..., description="색상 코드 목록")
