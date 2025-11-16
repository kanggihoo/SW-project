from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SizeRecommendInput(BaseModel):
    product_id: int = Field(description='사이즈 추천을 원하는 상품의 고유 ID.')
    height: int = Field(description='사용자의 키 (cm).')
    weight: int = Field(description='사용자의 몸무게 (kg).')


class ProductIDInput(BaseModel):
    product_id: int = Field(description='조회할 상품의 고유 ID.')


class ProductSelectionInfoInput(ProductIDInput):
    has_photo: bool = Field(description='사진이 포함된 상품만 조회할지 여부.', default=False)


# TODO : 여기의 각 항목들 중 포함할 것과 포함하지 않을 것을 선택해서 , 여기서 전체 개수를 반드시 알아야 page_size , page 를 정할 수 있긴 한데
class ProductReviewListInput(ProductIDInput):
    page_size: int = Field(default=5, description='한 페이지에 가져올 리뷰 수')
    page: int = Field(default=1, description='조회할 페이지 번호 (1부터 시작)')
    option_list: list[str] | None = Field(default=None, description='특정 옵션 필터')
    sex: Literal['M', 'F'] | None = Field(default=None, description='작성자 성별 필터')
    sort: Literal['up_cnt_desc', 'new', 'comment_cnt_desc', 'goods_est_desc', 'goods_est_asc'] = Field(default='up_cnt_desc', description='정렬 기준')
    # is_experience: bool = Field(default=False, description='한달 사용 리뷰만 필터링 여부')
    has_photo: bool = Field(default=False, description='사진 리뷰만 필터링 여부')


class BrandLikesCountInput(BaseModel):
    brand_name: str = Field(description='좋아요 수를 조회할 브랜드의 이름.')


# 신규 통합 도구용 Input 모델들
class GetProductDetailsInput(BaseModel):
    product_id: int = Field(description='제품의 핵심 정보를 조회할 상품의 고유 ID.')


class GetProductReviewsInput(ProductIDInput):
    sort: Literal[
        'up_cnt_desc',
        'new',
        'comment_cnt_desc',
        'goods_est_desc',
    ] = Field(
        default='up_cnt_desc',
        description="리뷰 정렬 기준입니다. 'up_cnt_desc'(도움이 되는 순), 'new'(최신순), 'comment_cnt_desc'(댓글 수 순), 'goods_est_desc'(평점 높은 순)",
    )
    page_size: int = Field(
        default=20,
        description='사용할 리뷰 개수입니다. 요약 모드 기본값은 20이며, 리스트 모드에서는 내부적으로 최대 10개까지 사용됩니다.',
    )
    mode: Literal['summary', 'list'] = Field(
        default='summary',
        description="리뷰를 요약 문자열('summary')로 받을지, 실제 리뷰 목록('list')으로 받을지 선택합니다.",
    )


class GetProductSizingInfoInput(BaseModel):
    product_id: int = Field(description='사이즈 정보를 조회할 상품의 고유 ID.')
    height: int | None = Field(default=None, description='사용자의 키 (cm). 제공하지 않으면 상세 실측 사이즈 정보만 반환합니다.')
    weight: int | None = Field(default=None, description='사용자의 몸무게 (kg). 제공하지 않으면 상세 실측 사이즈 정보만 반환합니다.')


TOOL_DEFINITION = [
    # 기존 세분화된 도구들 (통합으로 대체됨)
    # {'name': 'get_size_recommend', 'args_schema': SizeRecommendInput},
    # {'name': 'get_selection_info', 'args_schema': ProductSelectionInfoInput},
    # {'name': 'get_product_option_stock', 'args_schema': ProductIDInput},
    # {'name': 'get_size_details', 'args_schema': ProductIDInput},
    # {'name': 'get_review_summary', 'args_schema': ProductIDInput},
    # {'name': 'get_filtered_review_count', 'args_schema': ProductSelectionInfoInput},
    # {'name': 'get_review_list', 'args_schema': ProductReviewListInput},
    # {'name': 'get_product_like_count', 'args_schema': ProductIDInput},
    # {'name': 'get_product_stats', 'args_schema': ProductIDInput},
    # {'name': 'get_other_color_products', 'args_schema': ProductIDInput},
    # {'name': 'get_brand_and_price', 'args_schema': ProductIDInput},
    # {'name': 'get_brand_likes_count', 'args_schema': BrandLikesCountInput},
    # 신규 통합 도구들
    {'name': 'get_product_details', 'args_schema': GetProductDetailsInput},
    {'name': 'get_product_reviews', 'args_schema': GetProductReviewsInput},
    {'name': 'get_product_sizing_info', 'args_schema': GetProductSizingInfoInput},
]
