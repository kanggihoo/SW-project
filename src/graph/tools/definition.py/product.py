from pydantic import BaseModel, Field


class SizeRecommendInput(BaseModel):
    product_id: int = Field(description='사이즈 추천을 원하는 상품의 고유 ID.')
    height: int = Field(description='사용자의 키 (cm).')
    weight: int = Field(description='사용자의 몸무게 (kg).')


class ProductIDInput(BaseModel):
    product_id: int = Field(description='조회할 상품의 고유 ID.')


class ProductSelectionInfoInput(ProductIDInput):
    has_photo: bool = Field(description='사진이 포함된 상품만 조회할지 여부.', default=False)
    """
 Args:
            product_id (int): 리뷰 개수를 조회할 상품의 고유 ID.
            has_photo (bool, optional): 사진이 포함된 리뷰만 필터링할지 여부. Defaults to False.
            option_list (List[str], optional): 특정 옵션(예: '블랙', 'L')을 선택한 리뷰만 필터링. Defaults to None.
            sex (Literal["M", "F"], optional): 작성자의 성별을 기준으로 필터링. Defaults to None.
    """


class ProductReviewListInput(ProductIDInput):
    """
    Args:
           product_id (int): 리뷰를 조회할 상품의 고유 ID.
           page_size (int, optional): 한 페이지에 가져올 리뷰 수. Defaults to 5.
           page (int, optional): 조회할 페이지 번호 (0부터 시작). Defaults to 0.
           option_list (List[str], optional): 특정 옵션을 선택한 리뷰만 필터링. Defaults to None.
           sex (Literal["M", "F"], optional): 작성자 성별로 필터링. Defaults to None.
           sort (Literal[...], optional): 정렬 기준 ('up_cnt_desc': 도움순, 'new': 최신순 등). Defaults to "up_cnt_desc".
           is_experience (bool, optional): 한달 사용 리뷰만 필터링할지 여부. Defaults to False.
           has_photo (bool, optional): 사진 리뷰만 필터링할지 여부. Defaults to False.
    """


class BrandLikesCountInput(BaseModel):
    brand_name: str = Field(description='좋아요 수를 조회할 브랜드의 이름.')


TOOL_DEFINITION = [
    {
        'name': 'get_size_recommend',
        'args_schema': SizeRecommendInput,
    },
    {
        'name': 'get_product_selection_info',
        'args_schema': SizeRecommendInput,
    },
    {
        'name': 'get_product_option_stock',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_product_size_details',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_review_summary',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_filtered_review_count',
        'args_schema': ProductSelectionInfoInput,
    },
    {
        'name': 'get_review_list',
        'args_schema': ProductReviewListInput,
    },
    {
        'name': 'get_product_like_count',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_product_stats',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_product_other_color',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_product_price',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_brand_name',
        'args_schema': ProductIDInput,
    },
    {
        'name': 'get_brand_likes_count',
        'args_schema': BrandLikesCountInput,
    },
]
