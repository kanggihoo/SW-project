from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Annotated, Literal
from app.config.dependencies import MusinsaAPIWrapperDep
from app.model import musinsa as m
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/musinsa', tags=['musinsa'], deprecated=True)


async def process_musinsa_response(response: dict):
    """무신사 API 응답을 처리하고, 실패 시 HTTPException을 발생시킵니다."""
    if not response['success']:
        # error_details를 포함하여 더 자세한 에러 메시지를 반환합니다.
        detail = {'message': response.get('message'), 'error_details': response.get('error_details')}
        # return JSONResponse(status_code=404, detail=detail)
    return response


@router.get(
    '/products/{product_id}/brand-price',
    response_model=m.ProductBrandAndPriceResponse,
    summary='상품 브랜드 및 가격 정보 조회',
    description='상품의 브랜드(국문/영문)와 가격(정가, 판매가, 할인율) 정보를 조회합니다.',
)
async def get_product_brand_and_price(wrapper: MusinsaAPIWrapperDep, product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)]):
    response = await wrapper.get_product_brand_and_price(product_id)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/size-details',
    response_model=m.ProductSizeResponse,
    summary='상품 실측 사이즈 조회',
    description='상품의 옵션별 실측 사이즈 정보와 측정 가이드 이미지 URL을 조회합니다.',
)
async def get_product_size(wrapper: MusinsaAPIWrapperDep, product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)]):
    response = await wrapper.get_product_size(product_id)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/size-recommend',
    response_model=m.SizeRecommendResponse,
    summary='사용자 맞춤 사이즈 추천',
    description='사용자의 키와 몸무게 정보를 기반으로 가장 적합한 사이즈를 추천합니다.',
)
async def get_size_recommend(
    wrapper: MusinsaAPIWrapperDep,
    product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)],
    height: Annotated[int, Query(description='사용자 키(cm)', example=175)],
    weight: Annotated[int, Query(description='사용자 몸무게(kg)', example=70)],
):
    response = await wrapper.get_size_recommend(product_id, height, weight)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/stats',
    response_model=m.ProductStatsResponse,
    summary='상품 통계 정보 조회',
    description='상품의 최근 조회수와 누적 판매량 등 통계 정보를 조회합니다.',
)
async def get_product_stats(wrapper: MusinsaAPIWrapperDep, product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)]):
    response = await wrapper.get_product_stats(product_id)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/other-colors',
    response_model=m.ProductOtherColorResponse,
    summary='다른 색상 상품 조회',
    description='현재 상품과 동일한 스타일의 다른 색상 상품 목록을 조회합니다.',
)
async def get_product_other_color(wrapper: MusinsaAPIWrapperDep, product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)]):
    response = await wrapper.get_product_other_color(product_id)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/selection-info',
    response_model=m.ProductSelectionInfoResponse,
    summary='상품 구매 옵션 정보 조회',
    description='상품 구매 시 선택 가능한 옵션(사이즈, 색상 등) 정보를 조회합니다.',
)
async def get_product_selection_info(wrapper: MusinsaAPIWrapperDep, product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)]):
    response = await wrapper.get_product_selection_info(product_id)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/option-stock',
    response_model=m.ProductOptionStockResponse,
    summary='상품 옵션별 재고 상태 조회',
    description='상품의 각 옵션 조합별 재고 및 판매 가능 여부를 상세히 조회합니다.',
)
async def get_product_option_stock(wrapper: MusinsaAPIWrapperDep, product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)]):
    response = await wrapper.get_product_option_stock(product_id)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/reviews/summary',
    response_model=m.ReviewSummaryResponse,
    summary='리뷰 요약 정보 조회',
    description='상품의 전체 리뷰 수, 평점, 종류별 리뷰 개수 등 요약 정보를 조회합니다.',
)
async def get_review_summary(wrapper: MusinsaAPIWrapperDep, product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)]):
    response = await wrapper.get_review_summary(product_id)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/reviews/count',
    response_model=m.FilteredReviewCountResponse,
    summary='조건부 리뷰 개수 조회',
    description='사진 유무, 옵션, 성별 등 특정 조건에 맞는 리뷰의 총 개수를 조회합니다.',
)
async def get_filtered_review_count(
    wrapper: MusinsaAPIWrapperDep,
    product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)],
    has_photo: Annotated[bool, Query(description='사진 리뷰만 필터링할지 여부')] = False,
    option_list: Annotated[Optional[List[str]], Query(description='필터링할 상품 옵션 목록', example=['M', 'L'])] = None,
    sex: Annotated[Optional[Literal['M', 'F']], Query(description="필터링할 성별 ('M' 또는 'F')")] = None,
):
    print(option_list, sex, has_photo)
    response = await wrapper.get_filtered_review_count(product_id, has_photo, option_list, sex)
    return await process_musinsa_response(response)


@router.get(
    '/products/{product_id}/reviews',
    response_model=m.ReviewListResponse,
    summary='리뷰 목록 조회',
    description='다양한 필터링 및 정렬 조건에 따라 상품 리뷰 목록을 상세히 조회합니다.',
)
async def get_review_list(
    wrapper: MusinsaAPIWrapperDep,
    product_id: Annotated[int, Path(description='조회할 상품 ID', example=3522389)],
    page: Annotated[int, Query(description='페이지 번호', ge=0)] = 0,
    page_size: Annotated[int, Query(description='페이지 당 리뷰 수', ge=1, le=100)] = 10,
    sort: Annotated[
        Literal['up_cnt_desc', 'new', 'comment_cnt_desc', 'goods_est_desc', 'goods_est_asc'],
        Query(description='정렬 순서: 유용도순, 최신순, 댓글순, 평점높은순, 평점낮은순'),
    ] = 'up_cnt_desc',
    option_list: Annotated[Optional[List[str]], Query(description='필터링할 상품 옵션 목록', example=['M'])] = None,
    sex: Annotated[Optional[Literal['M', 'F']], Query(description='필터링할 성별')] = None,
    has_photo: Annotated[bool, Query(description='사진 리뷰만 필터링할지 여부')] = False,
    is_experience: Annotated[bool, Query(description='한달 사용기 필터링 여부')] = False,
):
    response = await wrapper.get_review_list(product_id, page_size, page, option_list, sex, sort, is_experience, has_photo)
    return await process_musinsa_response(response)


@router.post(
    '/products/likes',
    response_model=m.ProductLikeCountResponse,
    summary='여러 상품의 좋아요 수 조회',
    description='상품 ID 목록을 받아 각 상품의 좋아요 수를 한 번에 조회합니다.',
)
async def get_product_like_count(wrapper: MusinsaAPIWrapperDep, payload: Annotated[m.ProductLikeCountRequest, Body()]):
    product_ids = payload.relationIds
    response = await wrapper.get_product_like_count(product_ids)
    return await process_musinsa_response(response)


@router.post(
    '/brands/likes',
    response_model=m.BrandLikesCountResponse,
    summary='여러 브랜드의 좋아요 수 조회',
    description='브랜드 이름 목록을 받아 각 브랜드의 좋아요 수를 한 번에 조회합니다.',
)
async def get_brand_likes_count(wrapper: MusinsaAPIWrapperDep, payload: Annotated[m.BrandLikesCountRequest, Body()]):
    brand_names = payload.relationIds
    response = await wrapper.get_brand_likes_count(brand_names)
    return await process_musinsa_response(response)


@router.get(
    '/meta/colors',
    response_model=m.ColorCodeResponse,
    summary='무신사 색상 코드 전체 조회',
    description='무신사에서 사용하는 모든 색상의 이름과 ID를 조회합니다.',
)
async def get_color_code(wrapper: MusinsaAPIWrapperDep):
    response = await wrapper.get_color_code()
    return await process_musinsa_response(response)
