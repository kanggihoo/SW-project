import asyncio
import time
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path
from loguru import logger
from pydantic import BaseModel, Field

from app.config.dependencies import (
    MusinsaAPIWrapperDep,
    RedisClientDep,
    RepositoryDep,
    S3ManagerDep,
    SearchServiceDep,
    TaskQueueClientDep,
)
from app.model.search_api import (
    SearchOneProductResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

router = APIRouter(
    prefix='/search',
)


# 여기는 s3랑 , mongodb 만 필요 이제는
# @router.post('/', response_model=SearchResponse, deprecated=True)
# async def search_product(
#     search_service: SearchServiceTestDep,
#     request: Annotated[SearchRequest, Body()],
# ):
#     """
#     사용자 쿼리를 기반으로 상품을 검색합니다.
#     - 쿼리 분석 (향후 확장)
#     - 임베딩 생성
#     - 벡터 검색 수행
#     - 결과 반환
#     """
#     try:
#         start_time = time.time()
#         query = request.messages
#         limit = request.limit
#         return_image_url = request.return_image_url
#         # SearchService를 통해 비동기적으로 검색 수행
#         search_result = await search_service.search_by_query(query, limit=limit, return_image_url=return_image_url)  # limit은 예시

#         # 결과를 API 응답 모델에 맞게 변환
#         response_data = SearchResultItem(
#             query=search_result['query'],
#             rewritten_query_list=search_result.get('rewritten_query_list', None),
#             pre_filter_list=search_result.get('pre_filter_list', None),
#             data=search_result['data'],
#             total_count=search_result['total_count'],
#             message=search_result['message'],
#         )
#         logger.info(f'search_api_response_time: {time.time() - start_time}')
#         return SearchResponse(success=True, data=response_data)

#     except HTTPException as e:
#         # 서비스에서 발생한 HTTPException을 그대로 전달
#         raise e
#     except Exception as e:
#         # 그 외 예상치 못한 예외 처리
#         raise HTTPException(status_code=500, detail=f'An unexpected server error occurred: {e}')

PRODUCT_ID_REGEX = r'^[0-9]+_[가-힣]+$'


@router.get('/{product_id}', response_model=SearchOneProductResponse, tags=['search'])
async def search_product(
    s3_manager: S3ManagerDep,
    repository: RepositoryDep,
    musinsa_api_wrapper: MusinsaAPIWrapperDep,
    redis_client: RedisClientDep,
    taskqueue_client: TaskQueueClientDep,
    product_id: Annotated[
        str,
        Path(description='조회할 상품 sku_id', examples=['4149670_데님'], pattern=PRODUCT_ID_REGEX),
    ],
):
    """
    상품 정보를 조회합니다.

    처리 흐름:
    1. Redis 캐시 확인
       - Cache Hit: 캐시된 데이터 + 새로운 Presigned URL 생성 → 즉시 반환
       - Cache Miss: DB + Musinsa API 병렬 조회
    2. Cache Miss 시:
       - Musinsa API 성공: 최신 가격 정보 사용 + TaskQueue 작업 예약 → 즉시 반환
       - Musinsa API 실패: DB의 기존 가격 정보 사용 → 즉시 반환 (TaskQueue 작업 예약 없음)
    """
    logger.info(f'[API] Searching product: {product_id}')
    product_sku_id = product_id
    splited_product_id = product_id.split('_')[0]

    # ========================================================================
    # 1단계: Redis 캐시 조회
    # ========================================================================
    cache_key = f'cache:{product_sku_id}'
    cached_data = await redis_client.json_get(cache_key)

    if cached_data:
        # ====================================================================
        # Cache Hit: 캐시된 데이터로 즉시 응답
        # ====================================================================
        logger.info(f'[API] Cache HIT for product: {product_sku_id}')

        try:
            # 캐시된 데이터에서 S3 URL 재생성 (기존 URL은 만료되었을 수 있음)
            main_category = cached_data.get('main_category')
            sub_category = cached_data.get('sub_category')
            product_id_from_cache = cached_data.get('product_id')
            image_urls = cached_data.get('image_urls', [])

            if image_urls:
                s3_key = s3_manager.get_s3_object_key(main_category, sub_category, product_id_from_cache, image_urls[0])
                s3_url = s3_manager.generate_presigned_url(s3_key)
                # 캐시된 데이터의 image_url을 새로 생성한 URL로 업데이트
                cached_data['image_url'] = s3_url

            logger.info(f'[API] Returning cached data for product: {product_sku_id}')
            return SearchOneProductResponse(success=True, data=cached_data, message='상품 조회 성공 (캐시)')

        except Exception as e:
            logger.error(f'[API] Error processing cached data for {product_sku_id}: {e}')
            # 캐시 데이터 처리 실패 시 Cache Miss로 처리
            logger.info(f'[API] Falling back to Cache MISS flow for product: {product_sku_id}')

    # ========================================================================
    # 2단계: Cache Miss - DB와 Musinsa API 병렬 조회
    # ========================================================================
    logger.info(f'[API] Cache MISS for product: {product_sku_id}')

    projection = {
        '_id': 1,
        'products.product_id': 1,
        'products.product_name': 1,
        'products.brand_name': 1,
        'products.current_price': 1,
        'products.original_price': 1,
        'products.discount_rate': 1,
        'products.is_on_sale': 1,
        'products.captions.comprehensive_description': 1,
        'product_skus.size_detail_info': 1,
        'product_skus.image_urls': 1,
        'product_skus.main_category': 1,
        'product_skus.sub_category': 1,
        'product_skus.style_tags': 1,
        'product_skus.tpo_tags': 1,
        'product_skus.fit': 1,
    }

    try:
        # DB 조회와 Musinsa API 호출 병렬 실행
        tasks = [
            repository.find_by_id(product_sku_id, projection),
            musinsa_api_wrapper.get_product_brand_and_price(splited_product_id),
        ]
        docs, brand_and_price = await asyncio.gather(*tasks)

        if not docs:
            raise HTTPException(status_code=404, detail=f'Product {product_sku_id} not found in database')

        # DB에서 가져온 기본 정보
        main_category = docs.get('product_skus', {}).get('main_category')
        sub_category = docs.get('product_skus', {}).get('sub_category')
        product_id_from_db = docs.get('products', {}).get('product_id')
        image_urls = docs.get('product_skus', {}).get('image_urls', [])

        # S3 Presigned URL 생성
        s3_url = None
        if image_urls:
            s3_key = s3_manager.get_s3_object_key(main_category, sub_category, product_id_from_db, image_urls[0])
            s3_url = s3_manager.generate_presigned_url(s3_key)

        # DB의 기존 가격 정보
        current_price = docs.get('products', {}).get('current_price')
        original_price = docs.get('products', {}).get('original_price')
        discount_rate = docs.get('products', {}).get('discount_rate')
        is_on_sale = docs.get('products', {}).get('is_on_sale')

        # ====================================================================
        # 3단계: Musinsa API 결과에 따른 분기 처리
        # ====================================================================
        api_success = brand_and_price.get('success', False)

        if api_success:
            # ================================================================
            # 시나리오 B-1: Musinsa API 호출 성공
            # ================================================================
            logger.info(f'[API] Musinsa API call succeeded for product: {splited_product_id}')

            # 최신 가격 정보로 업데이트
            price_info = brand_and_price.get('data', [{}])[0].get('price_info', {})
            current_price = price_info.get('sale_price', current_price)
            original_price = price_info.get('original_price', original_price)
            discount_rate = price_info.get('discount_rate', discount_rate)
            is_on_sale = price_info.get('is_on_sale', is_on_sale)

            # 최종 데이터 조합
            data = {
                'product_sku_id': docs.get('_id'),
                'product_id': product_id_from_db,
                'product_name': docs.get('products', {}).get('product_name'),
                'brand_name': docs.get('products', {}).get('brand_name'),
                'current_price': current_price,
                'original_price': original_price,
                'discount_rate': discount_rate,
                'is_on_sale': is_on_sale,
                'comprehensive_description': docs.get('products', {}).get('captions', {}).get('comprehensive_description'),
                'image_urls': image_urls,
                'main_category': main_category,
                'sub_category': sub_category,
                'style_tags': docs.get('product_skus', {}).get('style_tags'),
                'tpo_tags': docs.get('product_skus', {}).get('tpo_tags'),
                'fit': docs.get('product_skus', {}).get('fit'),
            }

            # 백그라운드 TaskQueue 작업 예약 (캐시 저장 + DB 업데이트)
            try:
                job = await taskqueue_client.enqueue_task('update_cache_and_db_task', cache_key, product_sku_id, data)
                logger.info(f'[API] TaskQueue job enqueued: {job.job_id} for product: {product_sku_id}')
            except Exception as task_error:
                logger.error(f'[API] Failed to enqueue TaskQueue job for {product_sku_id}: {task_error}')
                # TaskQueue 실패해도 응답은 정상적으로 반환

            logger.info(f'[API] Returning data with latest price for product: {product_sku_id}')
            return SearchOneProductResponse(success=True, data=data, message='상품 조회 성공')

        else:
            # ================================================================
            # 시나리오 B-2: Musinsa API 호출 실패 (폴백)
            # ================================================================
            error_details = brand_and_price.get('error_details', {})
            status_code = error_details.get('status_code')

            if status_code == 429:
                retry_after = error_details.get('retry_after')
                if retry_after:
                    logger.warning(
                        f'[API] Musinsa API rate limit reached for product {splited_product_id}. Retry after: {retry_after} seconds. Using DB data.'
                    )
                else:
                    logger.warning(f'[API] Musinsa API rate limit reached for product {splited_product_id}. No Retry-After header. Using DB data.')
            else:
                logger.warning(f'[API] Musinsa API call failed for product {splited_product_id}: {brand_and_price}')

            # DB의 기존 가격 정보로 폴백 데이터 조합
            data = {
                'product_sku_id': docs.get('_id'),
                'product_id': product_id_from_db,
                'product_name': docs.get('products', {}).get('product_name'),
                'brand_name': docs.get('products', {}).get('brand_name'),
                'current_price': current_price,
                'original_price': original_price,
                'discount_rate': discount_rate,
                'is_on_sale': is_on_sale,
                'comprehensive_description': docs.get('products', {}).get('captions', {}).get('comprehensive_description'),
                'image_url': s3_url,
                'image_urls': image_urls,
                'main_category': main_category,
                'sub_category': sub_category,
                'style_tags': docs.get('product_skus', {}).get('style_tags'),
                'tpo_tags': docs.get('product_skus', {}).get('tpo_tags'),
                'fit': docs.get('product_skus', {}).get('fit'),
            }

            # TaskQueue 작업 예약 없음 (새로운 정보가 없으므로)
            logger.info(f'[API] Returning fallback DB data for product: {product_sku_id}')
            return SearchOneProductResponse(success=True, data=data, message='상품 조회 성공 (DB 데이터)')

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f'[API] Unexpected error for product {product_sku_id}: {e}')
        raise HTTPException(status_code=500, detail=f'An unexpected server error occurred: {e}') from e


@router.post('/test/vector_search_pipeline', response_model=SearchResponse, tags=['test'])
async def test_vector_search_pipeline(
    search_service: SearchServiceDep,
    request: Annotated[SearchRequest, Body()],
):
    """
    사용자 쿼리를 기반으로 상품을 검색합니다.
    - 쿼리 분석 (향후 확장)
    - 임베딩 생성
    - 벡터 검색 수행
    - 결과 반환
    """
    try:
        start_time = time.perf_counter()
        query = request.messages
        limit = request.limit
        verbose = request.verbose
        # SearchService를 통해 비동기적으로 검색 수행
        search_result = await search_service.search_by_query(query, limit=limit)  # limit은 예시

        # 결과를 API 응답 모델에 맞게 변환
        response_data = SearchResultItem(
            query=search_result['query'],
            data=search_result['data'],
            total_count=search_result['total_count'],
        )
        if verbose:
            response_data.embeddings = search_result['embeddings']
            response_data.pre_filter_list = search_result['pre_filter_list']
        logger.info(f'search_api_response_time: {time.perf_counter() - start_time}')
        return SearchResponse(success=True, data=response_data, message='Search completed successfully')

    except HTTPException as e:
        # 서비스에서 발생한 HTTPException을 그대로 전달
        raise e
    except Exception as e:
        # 그 외 예상치 못한 예외 처리
        raise HTTPException(status_code=500, detail=f'An unexpected server error occurred: {e}') from e


class VectorSearchRequest(BaseModel):
    messages: Annotated[str, Field(..., description='검색 쿼리')]
    limit: Annotated[int, Field(default=1, description='검색 결과 개수')]
    filter: Annotated[dict, Field(default_factory=dict, description='필터', examples=[{'main_category': '하의', 'color': '그린'}])]


@router.post('/test/single_vector_search', response_model=SearchResponse, tags=['test'], summary='single_vector_search, skip query analysis')
async def test_vector_search(
    search_service: SearchServiceDep,
    request: Annotated[VectorSearchRequest, Body()],
):
    try:
        start_time = time.perf_counter()
        query = request.messages
        limit = request.limit
        filter = request.filter
        search_result = await search_service.search_by_single_query_skip_query_analysis(query, limit, filter)
        logger.info(f'search_api_response_time: {time.perf_counter() - start_time}')
        return SearchResponse(success=True, data=search_result, message='Search completed successfully')
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An unexpected server error occurred: {e}') from e


class RelaxedFilterSearchRequest(BaseModel):
    embeddings: Annotated[list[list[float]], Field(..., description='이전 검색에서 사용한 임베딩 리스트')]
    pre_filters: Annotated[list[dict | None], Field(..., description='이전 검색에서 사용한 필터 리스트')]
    limit: Annotated[int, Field(default=1, description='검색 결과 개수')]


@router.post('/test/relaxed_filter_search', response_model=SearchResponse, tags=['test'], summary='Reuse embeddings with relaxed filters')
async def test_relaxed_filter_search(
    search_service: SearchServiceDep,
    request: Annotated[RelaxedFilterSearchRequest, Body()],
):
    """
    이전 검색의 임베딩과 필터를 재사용하여 완화된 필터로 재검색합니다.
    - 임베딩 재생성 없이 기존 임베딩 재사용
    - 필터는 main_category만 유지하여 완화
    - 결과 반환
    """
    try:
        start_time = time.perf_counter()
        embeddings = request.embeddings
        pre_filters = request.pre_filters
        limit = request.limit

        search_result = await search_service.search_by_previous_embeddings_with_relaxed_filters(
            embeddings=embeddings, pre_filters=pre_filters, limit=limit
        )

        logger.info(f'relaxed_filter_search_api_response_time: {time.perf_counter() - start_time}')
        return SearchResponse(success=True, data=search_result, message='Relaxed filter search completed successfully')
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An unexpected server error occurred: {e}') from e
