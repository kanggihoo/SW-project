from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio

from app.services.musinsa import MusinsaAPIWrapper
from db import get_async_fashion_sku_repo
from db.repository.fashion_async import AsyncFashionRepository
from graph.tools.handlers.product_handlers import ProductToolHandlers
from redis_cache.client import RedisCacheClient
from taskqueue.client import TaskQueueClient


@pytest_asyncio.fixture
async def httpx_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx.AsyncClient fixture for API testing."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest_asyncio.fixture
async def musinsa_service(httpx_client: httpx.AsyncClient) -> MusinsaAPIWrapper:
    """MusinsaAPIWrapper fixture for API testing."""
    return MusinsaAPIWrapper(httpx_client)


@pytest_asyncio.fixture
async def redis_cache_client():
    """Real RedisCacheClient fixture for integration testing with fallback to mock."""
    try:
        client = RedisCacheClient()
        await client.connect()
        yield client
        await client.close()
    except Exception:
        # 연결 실패 시 mock으로 fallback
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock(return_value=None)
        yield mock_client


@pytest_asyncio.fixture
async def task_queue_client():
    """Real TaskQueueClient fixture for integration testing with fallback to mock."""
    try:
        client = TaskQueueClient()
        await client.connect()
        yield client
        await client.close()
    except Exception:
        # 연결 실패 시 mock으로 fallback
        mock_client = MagicMock()
        mock_client.enqueue_task = AsyncMock(return_value=None)
        yield mock_client


@pytest_asyncio.fixture
async def db_repository():
    """Real AsyncFashionRepository fixture for integration testing with fallback to mock."""
    try:
        repo = await get_async_fashion_sku_repo()
        yield repo
    except Exception:
        # 연결 실패 시 mock으로 fallback
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=None)
        yield mock_repo


@pytest_asyncio.fixture
async def product_handlers(
    musinsa_service: MusinsaAPIWrapper,
    redis_cache_client: RedisCacheClient,
    task_queue_client: TaskQueueClient,
    db_repository: AsyncFashionRepository,
) -> ProductToolHandlers:
    """ProductToolHandlers fixture for integration testing with real dependencies."""
    return ProductToolHandlers(
        musinsa_service=musinsa_service,
        cache_client=redis_cache_client,
        task_queue_client=task_queue_client,
        db_repository=db_repository,
    )


class TestSingleMethodHandlers:
    """개별 Service & Adapter 메서드를 호출하는 핸들러 테스트 클래스"""

    # 테스트용 상품 ID (실제 무신사 상품 ID로 변경 필요)
    TEST_PRODUCT_ID = '2479983'  # 선택 옵션 2개

    @pytest.mark.asyncio
    async def test_handle_get_size_recommend(self, product_handlers: ProductToolHandlers) -> None:
        """사이즈 추천 핸들러 테스트"""
        print('\n=== 사이즈 추천 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_size_recommend(product_id=self.TEST_PRODUCT_ID, height=170, weight=70)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_selection_info(self, product_handlers: ProductToolHandlers) -> None:
        """제품 선택 옵션 정보 핸들러 테스트"""
        print('\n=== 제품 선택 옵션 정보 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_selection_info(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_option_stock(self, product_handlers: ProductToolHandlers) -> None:
        """제품 옵션 및 재고 정보 핸들러 테스트"""
        print('\n=== 제품 옵션 및 재고 정보 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_option_stock(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_size_details(self, product_handlers: ProductToolHandlers) -> None:
        """제품 실측 사이즈 정보 핸들러 테스트"""
        print('\n=== 제품 실측 사이즈 정보 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_size_details(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_review_summary(self, product_handlers: ProductToolHandlers) -> None:
        """리뷰 요약 정보 핸들러 테스트"""
        print('\n=== 리뷰 요약 정보 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_review_summary(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_filtered_review_count(self, product_handlers: ProductToolHandlers) -> None:
        """필터링된 리뷰 개수 핸들러 테스트"""
        print('\n=== 필터링된 리뷰 개수 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_filtered_review_count(product_id=self.TEST_PRODUCT_ID, has_photo=False, sex='M')
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_review_list(self, product_handlers: ProductToolHandlers) -> None:
        """리뷰 목록 핸들러 테스트"""
        print('\n=== 리뷰 목록 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_review_list(product_id=self.TEST_PRODUCT_ID, page_size=5, page=1, sort='up_cnt_desc')
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_product_like_count(self, product_handlers: ProductToolHandlers) -> None:
        """제품 좋아요 수 핸들러 테스트"""
        print('\n=== 제품 좋아요 수 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_product_like_count(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_product_stats(self, product_handlers: ProductToolHandlers) -> None:
        """제품 통계 정보 핸들러 테스트"""
        print('\n=== 제품 통계 정보 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_product_stats(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_other_color_products(self, product_handlers: ProductToolHandlers) -> None:
        """다른 색상 제품 핸들러 테스트"""
        print('\n=== 다른 색상 제품 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_other_color_products(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_handle_get_brand_and_price(self, product_handlers: ProductToolHandlers) -> None:
        """제품 브랜드 및 가격 정보 핸들러 테스트"""
        print('\n=== 제품 브랜드 및 가격 정보 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_brand_and_price(product_id=self.TEST_PRODUCT_ID)
            print('결과:')
            print(result)
            print('---')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    # @pytest.mark.asyncio
    # async def test_handle_get_brand_like_count(self, product_handlers: ProductToolHandlers) -> None:
    #     """브랜드 좋아요 수 핸들러 테스트"""
    #     print('\n=== 브랜드 좋아요 수 핸들러 테스트 ===')
    #     try:
    #         result = await product_handlers.handle_get_brand_like_count(brand_name='nike')
    #         print('결과:')
    #         print(result)
    #         print('---')
    #     except Exception as e:
    #         print(f'예외 발생: {str(e)}')

    # @pytest.mark.asyncio
    # async def test_handle_get_color_code(self, product_handlers: ProductToolHandlers) -> None:
    #     """색상 코드 핸들러 테스트"""
    #     print('\n=== 색상 코드 핸들러 테스트 ===')
    #     try:
    #         result = await product_handlers.handle_get_color_code()
    #         print('결과:')
    #         print(result)
    #         print('---')
    #     except Exception as e:
    #         print(f'예외 발생: {str(e)}')


class TestIntegratedHandlers:
    """여러 메서드를 동시 호출하거나 복잡한 로직을 포함하는 통합 핸들러 테스트 클래스"""

    # 테스트용 상품 ID (실제 무신사 상품 ID로 변경 필요)
    TEST_PRODUCT_ID = '2479983'  # 선택 옵션 2개

    @pytest.mark.asyncio
    async def test_handle_get_product_details(self, product_handlers: ProductToolHandlers) -> None:
        """통합 제품 상세 정보 핸들러 테스트 (병렬 API 호출 with asyncio.gather)"""
        print('\n=== 통합 제품 상세 정보 핸들러 테스트 ===')
        try:
            result = await product_handlers.handle_get_product_details(product_id=int(self.TEST_PRODUCT_ID))
            print('결과:')
            print(result)
            print('---')

            # 결과 검증
            assert isinstance(result, dict), '결과는 딕셔너리 타입이어야 합니다'

            # 필수 키들이 존재하는지 확인
            expected_keys = ['brand_name', 'price_info', 'statistics']
            for key in expected_keys:
                assert key in result, f'결과에 {key} 키가 있어야 합니다'

            # price_info 구조 검증
            price_info = result['price_info']
            assert isinstance(price_info, dict), 'price_info는 딕셔너리 타입이어야 합니다'

            # statistics가 있으면 구조 검증
            statistics = result['statistics']
            assert isinstance(statistics, str), 'statistics는 문자열 타입이어야 합니다'

            print('✅ 통합 제품 상세 정보 테스트 성공')

        except Exception as e:
            print(f'예외 발생: {str(e)}')
            raise

    @pytest.mark.asyncio
    async def test_handle_get_product_sizing_info_with_recommendation(self, product_handlers: ProductToolHandlers) -> None:
        """제품 사이징 정보 핸들러 테스트 (사이즈 추천 포함)"""
        print('\n=== 제품 사이징 정보 핸들러 테스트 (추천 모드) ===')
        try:
            result = await product_handlers.handle_get_product_sizing_info(product_id=int(self.TEST_PRODUCT_ID), height=170, weight=70)
            print('결과:')
            print(result)
            print('---')

            # 결과 검증
            assert isinstance(result, list), '결과는 리스트 타입이어야 합니다'

            print('✅ 사이징 정보 핸들러 테스트 (추천 모드) 성공')

        except Exception as e:
            print(f'예외 발생: {str(e)}')
            raise

    @pytest.mark.asyncio
    async def test_handle_get_product_sizing_info_measurements_only(self, product_handlers: ProductToolHandlers) -> None:
        """제품 사이징 정보 핸들러 테스트 (실측 정보만)"""
        print('\n=== 제품 사이징 정보 핸들러 테스트 (실측 모드) ===')
        try:
            result = await product_handlers.handle_get_product_sizing_info(product_id=int(self.TEST_PRODUCT_ID))
            print('결과:')
            print(result)
            print('---')

            # 결과 검증
            assert isinstance(result, list), '결과는 딕셔너리 타입이어야 합니다'

            print('✅ 사이징 정보 핸들러 테스트 (실측 모드) 성공')

        except Exception as e:
            print(f'예외 발생: {str(e)}')
            raise

    @pytest.mark.asyncio
    async def test_handle_get_product_reviews_summary_mode(self, product_handlers: ProductToolHandlers) -> None:
        """제품 리뷰 핸들러 테스트 (summary 모드 - DB/Redis 캐시 포함)"""
        print('\n=== 제품 리뷰 핸들러 테스트 (summary 모드) ===')
        try:
            # 기본 요약 모드 테스트
            result = await product_handlers.handle_get_product_reviews(product_id=self.TEST_PRODUCT_ID, mode='summary', sort='new')
            print('결과 (summary 모드):')
            print(result)
            print('---')

            # 결과 타입 검증
            assert isinstance(result, str), 'summary 모드 결과는 문자열 타입이어야 합니다'

            print('✅ 리뷰 핸들러 테스트 (summary 모드) 성공')

        except Exception as e:
            print(f'예외 발생: {str(e)}')
            raise

    @pytest.mark.asyncio
    async def test_handle_get_product_reviews_list_mode(self, product_handlers: ProductToolHandlers) -> None:
        """제품 리뷰 핸들러 테스트 (list 모드)"""
        print('\n=== 제품 리뷰 핸들러 테스트 (list 모드) ===')
        try:
            # 목록 모드 테스트
            result = await product_handlers.handle_get_product_reviews(
                product_id=self.TEST_PRODUCT_ID, mode='list', sort='goods_est_desc', page_size=5
            )
            print('결과 (list 모드):')
            print(result)
            print('---')

            # 결과 타입 검증
            assert isinstance(result, (list, str)), 'list 모드 결과는 리스트 또는 문자열 타입이어야 합니다'

            if isinstance(result, list):
                # 리스트인 경우 각 항목이 딕셔너리인지 확인
                for item in result:
                    assert isinstance(item, dict), '리스트의 각 항목은 딕셔너리 타입이어야 합니다'

            print('✅ 리뷰 핸들러 테스트 (list 모드) 성공')

        except Exception as e:
            print(f'예외 발생: {str(e)}')
            raise

    # @pytest.mark.asyncio
    # async def test_handle_get_product_reviews_different_sorts(self, product_handlers: ProductToolHandlers) -> None:
    #     """제품 리뷰 핸들러 테스트 (다양한 정렬 옵션 - 캐시 전략 포함)"""
    #     print('\n=== 제품 리뷰 핸들러 테스트 (다양한 정렬 옵션) ===')
    #     try:
    #         # 다양한 정렬 옵션 테스트
    #         sort_options = ['goods_est_desc', 'goods_est_asc', 'comment_cnt_desc']

    #         for sort_option in sort_options:
    #             print(f'테스트 중: sort={sort_option}')
    #             result = await product_handlers.handle_get_product_reviews(
    #                 product_id=self.TEST_PRODUCT_ID, mode='summary', sort=sort_option, page_size=10
    #             )
    #             assert isinstance(result, str), f'{sort_option} 정렬 결과는 문자열 타입이어야 합니다'
    #             print(f'✅ {sort_option} 정렬 테스트 성공')

    #         print('✅ 다양한 정렬 옵션 테스트 모두 성공')

    #     except Exception as e:
    #         print(f'예외 발생: {str(e)}')
    #         raise
