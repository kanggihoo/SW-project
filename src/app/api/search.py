from fastapi import APIRouter, Body, HTTPException, Path
from typing import Annotated
from app.config.dependencies import SearchServiceTestDep, S3ManagerDep, RepositoryDep, HTTPClientDep
from app.model.saarch_api import SearchRequest, SearchResponse, SearchResultItem, SearchOneProductResponse
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/search',
    tags=['search'],
)


# 여기는 s3랑 , mongodb 만 필요 이제는
@router.post('/', response_model=SearchResponse, deprecated=True)
async def search_product(search_service: SearchServiceTestDep, request: Annotated[SearchRequest, Body()]):
    """
    사용자 쿼리를 기반으로 상품을 검색합니다.
    - 쿼리 분석 (향후 확장)
    - 임베딩 생성
    - 벡터 검색 수행
    - 결과 반환
    """
    try:
        start_time = time.time()
        query = request.messages
        limit = request.limit
        return_image_url = request.return_image_url
        # SearchService를 통해 비동기적으로 검색 수행
        search_result = await search_service.search_by_query(query, limit=limit, return_image_url=return_image_url)  # limit은 예시

        # 결과를 API 응답 모델에 맞게 변환
        response_data = SearchResultItem(
            query=search_result['query'],
            rewritten_query_list=search_result.get('rewritten_query_list', None),
            pre_filter_list=search_result.get('pre_filter_list', None),
            data=search_result['data'],
            total_count=search_result['total_count'],
            message=search_result['message'],
        )
        logger.info(f'search_api_response_time: {time.time() - start_time}')
        return SearchResponse(success=True, data=response_data)

    except HTTPException as e:
        # 서비스에서 발생한 HTTPException을 그대로 전달
        raise e
    except Exception as e:
        # 그 외 예상치 못한 예외 처리
        raise HTTPException(status_code=500, detail=f'An unexpected server error occurred: {e}')


# TODO : 무신사api로 부터 실시간 정보 업데이트 해서 가져오기 (만약에 판매중인 상품이 아니면??)
@router.get('/{product_id}', response_model=SearchOneProductResponse)
async def search_product(
    s3_manager: S3ManagerDep,
    repository: RepositoryDep,
    http_client: HTTPClientDep,
    product_id: Annotated[str, Path(description='조회할 상품 sku_id', example='89731_블루')],
):
    # TODO : 해당 제품이 없는 경우 에러처리
    logger.info(f'product_id: {product_id}')
    try:
        projection = {
            '_id': 1,
            'products.product_id': 1,
            'products.product_name': 1,
            'products.brand_name': 1,
            'products.current_price': 1,
            'products.original_price': 1,
            'products.description_info': 1,
            # "product_skus.size_detail_info": 1,
            'product_skus.image_urls': 1,
            'product_skus.main_category': 1,
            'product_skus.sub_category': 1,
            'product_skus.style_tags': 1,
            'product_skus.tpo_tags': 1,
            'product_skus.fit': 1,
        }
        docs = await repository.find_by_id(product_id, projection)
        main_category = docs.get('product_skus').get('main_category')
        sub_category = docs.get('product_skus').get('sub_category')
        product_id = docs.get('products').get('product_id')
        image_urls = docs.get('product_skus').get('image_urls')[0]
        s3_key = s3_manager.get_s3_object_key(main_category, sub_category, product_id, image_urls)
        s3_url = s3_manager.generate_presigned_url(s3_key)

        data = {
            'product_sku_id': docs.get('_id'),
            'product_id': docs.get('products').get('product_id'),
            'product_name': docs.get('products').get('product_name'),
            'brand_name': docs.get('products').get('brand_name'),
            'current_price': docs.get('products').get('current_price'),
            'original_price': docs.get('products').get('original_price'),
            # "description_info": docs.get("products").get("description_info"),
            'image_url': s3_url,
            'product_size_info': docs.get('product_skus').get('size_detail_info'),
            'image_urls': docs.get('product_skus').get('image_urls'),
            'main_category': docs.get('product_skus').get('main_category'),
            'sub_category': docs.get('product_skus').get('sub_category'),
            'style_tags': docs.get('product_skus').get('style_tags'),
            'tpo_tags': docs.get('product_skus').get('tpo_tags'),
            'fit': docs.get('product_skus').get('fit'),
        }

        return SearchOneProductResponse(success=True, data=data, message='상품 조회 성공')
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An unexpected server error occurred: {e}')
