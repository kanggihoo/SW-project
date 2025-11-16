"""
Product Handler: Service와 Adapter를 연결하여 LLM 도구 호출을 처리

LLM 에이전트의 도구 호출 요청을 받아,
Service(MusinsaAPIWrapper)를 통해 데이터를 가져오고,
Adapter(ProductAdapter)를 통해 LLM 친화적 형태로 변환한 후 반환합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.musinsa import MusinsaAPIWrapper
    from db.repository.fashion_async import AsyncFashionRepository
    from redis_cache.client import RedisCacheClient
    from taskqueue.client import TaskQueueClient
import asyncio
from typing import Any, Literal

from loguru import logger

from graph.task.review_summarizer import ReviewSummarizer
from graph.tools.adapters.product_adapter import ProductAdapter

from ...utils.time import get_current_utc_timestamp

# --- (추가) 설정값 상수화 ---
DEFAULT_SUMMARY_REFRESH_DAYS = 7
DEFAULT_SUMMARY_REFRESH_COUNT = 20
KEY_SUMMARY_CACHE_TTL_SECONDS = 3600 * 24 * 12  # 12일
KEY_SUMMARY_WHITELIST = ['new', 'goods_est_desc', 'comment_cnt_desc']
REVIEW_SUMMARY_TASK_NAME = 'update_review_summary_in_db_task'
TOOL_CACHE_TASK_NAME = 'update_tool_cache_task'


class ProductToolHandlers:
    """
    LLM 도구 호출을 처리하는 핸들러 클래스.
    Service와 Adapter를 조율하여 최종 결과를 생성합니다.
    """

    # TODO : 여기서 추가 모듈을 초기화 시에 제공받아서 사용할 수 있도록??
    def __init__(
        self,
        musinsa_service: MusinsaAPIWrapper,  # src.app.services.musinsa.MusinsaAPIWrapper
        cache_client: RedisCacheClient,  # src.cache.RedisCacheClient
        task_queue_client: TaskQueueClient,  # src.task_queue.TaskQueueClient
        db_repository: AsyncFashionRepository,  # mongodb repository # src.db.repository.fashion_async.AsyncFashionRepository
    ):
        """
        Args:
            musinsa_service: 의존성 주입된 MusinsaAPIWrapper 인스턴스
        """
        self.service = musinsa_service
        self.cache_client = cache_client
        self.task_queue_client = task_queue_client
        self.db_repository = db_repository
        self.review_summarizer = ReviewSummarizer(model_str='google/gemini-2.5-flash')

    async def handle_get_brand_and_price(self, product_id: int | str) -> str:
        """상품의 브랜드 이름과 가격 정보를 조회합니다.

        Args:
            product_id: 상품 고유 ID

        Returns:
            str: 브랜드 및 가격 정보 문자열
        """
        raw_data = await self.service.get_product_brand_and_price(product_id)
        adapted_result = ProductAdapter.adapt_brand_and_price(raw_data)

        # 어댑터가 구조화된 dict를 반환하는 경우, summary 텍스트를 꺼내서 반환
        if isinstance(adapted_result, dict):
            summary = adapted_result.get('summary')
            if isinstance(summary, str):
                return summary
            # summary가 없으면 브랜드/가격 정보를 간단한 문자열로 직렬화
            brand_name = adapted_result.get('brand_name', '')
            price_info = adapted_result.get('price_info', {})
            return f'Brand: {brand_name}, Price info: {price_info}'

        # 에러 메시지 등 문자열 그대로인 경우는 그대로 반환
        if isinstance(adapted_result, str):
            return adapted_result

        # 방어적 코드: 예상치 못한 타입이면 문자열로 캐스팅
        return str(adapted_result)

    async def handle_get_size_recommend(self, product_id: int | str, height: int | str, weight: int | str) -> str:
        """사용자의 키와 몸무게를 기반으로 상품의 사이즈를 추천합니다.

        Args:
            product_id: 상품 고유 ID
            height: 사용자 키(cm)
            weight: 사용자 몸무게(kg)

        Returns:
            str: LLM이 이해하기 쉬운 사이즈 추천 문자열
        """
        # 1. Service에 데이터 요청
        raw_data = await self.service.get_size_recommend(product_id, height, weight)

        # 2. Adapter로 변환
        adapted_result = ProductAdapter.adapt_size_recommend(raw_data)

        # 3. 최종 결과 반환
        return adapted_result

    async def handle_get_selection_info(self, product_id: int | str) -> str | dict[str, Any]:
        """상품의 구매 옵션(선택 가능한 색상, 사이즈 등)을 조회합니다.
        옵션 종류가 하나면 옵션명과 값들을 문자열로, 여러 개면 각 옵션의 종류와
        선택 가능한 값들을 담은 딕셔너리로 반환

        Args:
            product_id: 상품 고유 ID

        Returns:
            str | dict: 옵션 정보 (옵션이 여러 개인 경우 dict, 단일 옵션인 경우 str)
        """
        raw_data = await self.service.get_product_selection_info(product_id)
        adapted_result = ProductAdapter.adapt_selection_info(raw_data)
        return adapted_result

    # async def handle_get_option_stock(self, product_id: int | str) -> dict[str, Any] | str:
    #     """상품의 각 옵션별 재고 상태를 조회합니다.

    #     Args:
    #         product_id: 상품 고유 ID

    #     Returns:
    #         dict | str: 옵션 종류 + 재고 상태 맵
    #     """
    #     raw_data = await self.service.get_product_option_stock(product_id)
    #     adapted_result = ProductAdapter.adapt_option_stock(raw_data)
    #     return adapted_result

    async def handle_get_size_details(self, product_id: int | str) -> list[dict[str, Any]] | str:
        """상품의 사이즈별 상세 실측 정보(총장, 어깨너비 등)를 조회합니다. 각 사이즈 이름과 측정치 딕셔너리를 포함하는 객체 리스트 형태로 반환

        Args:
            product_id: 상품 고유 ID

        Returns:
            list[dict] | str: 사이즈별 실측 정보 리스트
        """
        raw_data = await self.service.get_product_size(product_id)
        adapted_result = ProductAdapter.adapt_size_details(raw_data)
        return adapted_result

    async def handle_get_review_summary(self, product_id: int | str) -> str:
        """상품의 전체 리뷰 요약 정보(평점, 리뷰 개수 등)를 조회합니다.

        Args:
            product_id: 상품 고유 ID

        Returns:
            str: 리뷰 요약 문자열
        """
        raw_data = await self.service.get_review_summary(product_id)
        adapted_result = ProductAdapter.adapt_review_summary(raw_data)
        return adapted_result

    async def handle_get_filtered_review_count(
        self, product_id: int | str, has_photo: bool = False, option_list: list[str] | None = None, sex: Literal['M', 'F'] | None = None
    ) -> str:
        """조건(사진 유무, 옵션, 성별)에 따라 필터링된 리뷰 개수를 조회합니다.

        Args:
            product_id: 상품 고유 ID
            has_photo: 사진 포함 여부 (기본값: False)
            option_list: 특정 옵션 리스트 (예: ["블랙", "M"])
            sex: 성별 필터 ("M" 또는 "F")

        Returns:
            str: 필터링된 리뷰 개수 설명 문자열
        """
        raw_data = await self.service.get_filtered_review_count(product_id, has_photo, option_list, sex)
        adapted_result = ProductAdapter.adapt_filtered_review_count(raw_data, has_photo, option_list, sex)
        return adapted_result

    async def handle_get_review_list(
        self,
        product_id: int | str,
        page_size: int = 10,
        page: int = 1,
        option_list: list[str] | None = None,
        sex: Literal['M', 'F'] | None = None,
        sort: Literal['up_cnt_desc', 'new', 'comment_cnt_desc', 'goods_est_desc', 'goods_est_asc'] = 'up_cnt_desc',
        is_experience: bool = False,
        has_photo: bool = False,
    ) -> list[dict[str, Any]] | str:
        """조건에 따라 필터링 및 정렬된 상세 리뷰 목록을 조회합니다.

        Args:
            product_id: 상품 고유 ID
            page_size: 페이지당 리뷰 개수 (기본값: 10)
            page: 페이지 번호 (기본값: 1)
            option_list: 특정 옵션 리스트 (예: ["블랙", "M"])
            sex: 성별 필터 ("M" 또는 "F")
            sort: 정렬 기준 (기본값: 'up_cnt_desc' - 도움이 되는 순)
            is_experience: 한달 사용 리뷰만 조회 (기본값: False)
            has_photo: 사진 포함 리뷰만 조회 (기본값: False)

        Returns:
            list[dict] | str: 간결한 리뷰 정보 리스트
        """
        raw_data = await self.service.get_review_list(product_id, page_size, page, option_list, sex, sort, is_experience, has_photo)
        adapted_result = ProductAdapter.adapt_review_list(raw_data)
        return adapted_result

    async def handle_get_product_like_count(self, product_id: int | str | list[int | str]) -> str:
        """상품의 '좋아요' 수를 조회합니다. 여러 상품을 한 번에 조회할 수도 있습니다.

        Args:
            product_id: 상품 고유 ID 또는 ID 리스트

        Returns:
            str: 좋아요 수 설명 문자열
        """
        raw_data = await self.service.get_product_like_count(product_id)
        adapted_result = ProductAdapter.adapt_product_like_count(raw_data)
        return adapted_result

    async def handle_get_product_stats(self, product_id: int | str) -> str:
        """상품의 조회수 및 누적 판매량 통계를 조회합니다.

        Args:
            product_id: 상품 고유 ID

        Returns:
            str: 통계 정보 문자열
        """
        raw_data = await self.service.get_product_stats(product_id)
        adapted_result = ProductAdapter.adapt_product_stats(raw_data)
        return adapted_result

    async def handle_get_other_color_products(self, product_id: int | str) -> list[dict[str, Any]] | str:
        """현재 상품과 동일한 디자인의 다른 색상 제품 목록을 조회합니다.

        Args:
            product_id: 상품 고유 ID

        Returns:
            list[dict] | str: 다른 색상 제품 정보 리스트
        """
        raw_data = await self.service.get_product_other_color(product_id)
        adapted_result = ProductAdapter.adapt_other_color_products(raw_data)
        return adapted_result

    # async def handle_get_brand_like_count(self, brand_name: str | list[str]) -> str:
    #     """브랜드의 '좋아요(팬)' 수를 조회합니다.

    #     Args:
    #         brand_name: 브랜드 영문 이름 (소문자) 또는 이름 리스트

    #     Returns:
    #         str: 브랜드 좋아요 수 문자열
    #     """
    #     raw_data = await self.service.get_brand_likes_count(self.service.client, brand_name)
    #     adapted_result = ProductAdapter.adapt_brand_like_count(raw_data)
    #     return adapted_result

    # async def handle_get_color_code(self) -> list[dict[str, Any]] | str:
    #     """무신사에서 사용하는 색상 코드 목록을 조회합니다.

    #     Returns:
    #         list[dict] | str: 색상 ID + 이름 리스트
    #     """
    #     raw_data = await self.service.get_color_code(self.service.client)
    #     adapted_result = ProductAdapter.adapt_color_code(raw_data)
    #     return adapted_result

    # ===== 신규 통합 도구 핸들러 메서드들 =====
    async def handle_get_product_details(self, product_id: int) -> dict[str, Any]:
        """특정 상품 하나에 대한 기본 정보(브랜드/가격, 판매·조회 통계, 좋아요, 옵션, 다른 색상, 설명)를 한 번에 조회하는 도구입니다.

        언제 사용해야 하는지:
            - 한 상품의 전반적인 프로필을 한 번에 파악해야 할 때 사용합니다.

        파라미터:
            - product_id (int): 정보를 조회할 상품의 고유 ID입니다.

        반환값:
            - dict[str, Any]: 브랜드/가격, 통계, 좋아요 수, 선택 옵션, 다른 색상 상품, 설명 등 핵심 정보를 포함한 구조화된 상품 상세 정보입니다.
        """
        cache_key = f'tool-cache:{product_id}:details'

        # 1. 함수 시작 시 캐시 확인
        cached_result = await self.cache_client.json_get(cache_key)
        if cached_result:
            logger.info(f'[{product_id}] "details" 최종 결과 캐시 히트')
            return cached_result

        # 2. Cache Miss 시, 기존 로직 수행
        logger.info(f'[{product_id}] "details" 최종 결과 캐시 미스. 데이터 생성.')

        # 여러 Service 메서드를 병렬로 동시에 호출합니다.
        results = await asyncio.gather(
            self.service.get_product_brand_and_price(product_id),
            self.service.get_product_stats(product_id),
            self.service.get_product_like_count(product_id),
            self.service.get_product_selection_info(product_id),
            self.service.get_product_other_color(product_id),
            self.db_repository.get_product_description_info(str(product_id)),
            # 리뷰 개수, 리뷰 평점 정보도 같이
            return_exceptions=True,  # 특정 API가 실패해도 전체가 중단되지 않도록 설정
        )

        # gather의 결과를 이름과 매핑하여 Adapter에 전달하기 쉽게 만듭니다.
        raw_data_map = {
            'brand_and_price': results[0] if not isinstance(results[0], Exception) else None,
            'stats': results[1] if not isinstance(results[1], Exception) else None,
            'like_count': results[2] if not isinstance(results[2], Exception) else None,
            'selection_info': results[3] if not isinstance(results[3], Exception) else None,
            'other_colors': results[4] if not isinstance(results[4], Exception) else None,
            'description_info': results[5] if not isinstance(results[5], Exception) else None,
        }

        # 병렬 호출로 얻은 '원본 데이터 묶음'을 Adapter에 넘겨 변환을 요청합니다.
        final_llm_response = ProductAdapter.adapt_product_details(raw_data_map)

        # 3. Task Queue를 통해 백그라운드에서 캐시 업데이트
        await self.task_queue_client.enqueue_task(
            TOOL_CACHE_TASK_NAME,
            cache_key=cache_key,
            cache_value=final_llm_response,
        )
        logger.info(f'[{product_id}] "details" 캐시 저장을 백그라운드 작업으로 위임')

        # 4. 캐시 저장을 기다리지 않고 즉시 결과 반환
        return final_llm_response

    async def handle_get_product_sizing_info(
        self, product_id: int, height: int | None = None, weight: int | None = None
    ) -> dict[str, Any] | list[dict[str, Any]] | str:
        """상품의 상세 실측 사이즈를 조회하거나, 사용자의 키·몸무게를 기반으로 사이즈를 추천받는 도구입니다.

        언제 사용해야 하는지:
            - 옷의 실제 치수(총장, 어깨너비 등)를 알고 싶을 때 → height/weight 없이 호출합니다.
            - 사용자의 키/몸무게 기준으로 어떤 사이즈를 입어야 할지 알고 싶을 때 → height와 weight를 모두 채워서 호출합니다.

        파라미터:
            - product_id (int): 사이즈 정보를 조회할 상품의 고유 ID입니다.
            - height (int | None): 사용자의 키(cm). height 또는 weight 중 하나라도 None이면 실측 정보만 반환됩니다.
            - weight (int | None): 사용자의 몸무게(kg). height 또는 weight 중 하나라도 None이면 실측 정보만 반환됩니다.

        반환값:
            - height/weight를 주지 않은 경우:
                - dict[str, Any]: {"type": "measurements", "data": [...]} 형식으로, 각 사이즈별 실측 정보 리스트를 포함합니다.
            - height/weight를 모두 준 경우:
                - list[dict[str, Any]]: [{"type": "recommendation", "data": ...}, {"type": "measurements", "data": ...}] 형식으로
                  추천 결과와 실측 정보가 함께 담깁니다.
            - str: 오류 등으로 문자열 메시지를 반환하는 경우 이 값이 그대로 전달될 수 있습니다.
        """

        # height 또는 weight가 None이면 실측 사이즈 정보만 반환, 그렇지 않으면 두 가지 정보를 모두 동시 호출
        cache_key = f'tool-cache:{product_id}:measurements'
        if height is None or weight is None:
            # 1. 분기문 내에서 캐시 확인
            cached_data = await self.cache_client.json_get(cache_key)

            if cached_data:
                logger.info(f'[{product_id}] "measurements" 데이터 캐시 히트')
                return cached_data
            else:
                # 2. Cache Miss 시, 서비스 호출
                logger.info(f'[{product_id}] "measurements" 데이터 캐시 미스. API 호출.')
                raw_data = await self.service.get_product_size(product_id)
                adapted_result = ProductAdapter.adapt_size_details(raw_data)

                # 3. Task Queue를 통해 백그라운드에서 캐시 업데이트
                await self.task_queue_client.enqueue_task(
                    TOOL_CACHE_TASK_NAME,
                    cache_key=cache_key,
                    cache_value=adapted_result,
                )
                logger.info(f'[{product_id}] "measurements" 캐시 저장을 백그라운드 작업으로 위임')

                return adapted_result
        else:
            # 사이즈 추천과 실측 사이즈 정보를 모두 동시 호출

            cached_data = await self.cache_client.json_get(cache_key)
            if cached_data:
                logger.info(f'[{product_id}] "measurements" 데이터 캐시 히트')
                recommend_raw = await self.service.get_size_recommend(product_id, height, weight)
                recommend_result = ProductAdapter.adapt_size_recommend(recommend_raw)
                return [{'type': 'recommendation', 'data': recommend_result}, {'type': 'measurements', 'data': cached_data}]
            else:
                recommend_task = self.service.get_size_recommend(product_id, height, weight)
                size_task = self.service.get_product_size(product_id)

                recommend_raw, size_raw = await asyncio.gather(recommend_task, size_task)

                recommend_result = ProductAdapter.adapt_size_recommend(recommend_raw)
                size_result = ProductAdapter.adapt_size_details(size_raw)

                return [{'type': 'recommendation', 'data': recommend_result}, {'type': 'measurements', 'data': size_result}]

    # # --- (신규) 리뷰 요약을 위한 내부 헬퍼 메서드 ---
    async def _summarize_reviews_with_llm(self, reviews: list[dict]) -> str:
        """(가상) LLM을 호출하여 리뷰 목록을 요약하는 내부 메서드"""
        if not reviews:
            return '요약할 리뷰가 없습니다.'

        # 실제 구현:
        summary = await self.review_summarizer.summarize(reviews)
        return summary

    # --- (신규) 통합된 리뷰 조회 및 요약 핸들러 ---
    async def handle_get_product_reviews(
        self,
        product_id: int | str,
        sort: Literal['up_cnt_desc', 'new', 'comment_cnt_desc', 'goods_est_desc', 'goods_est_asc'] = 'up_cnt_desc',
        page_size: int = 20,  # 요약을 위해 충분한 리뷰를 가져오도록 기본값 조정
        mode: Literal['summary', 'list'] = 'summary',
    ) -> str | list[dict[str, Any]]:
        """상품 리뷰를 요약해서 문자열로 받거나, 조건에 맞는 실제 리뷰 목록을 리스트로 받는 도구입니다.

        언제 사용해야 하는지:
            - 상품 전반에 대한 리뷰 경향을 간단히 알고 싶을 때 → mode='summary'로 호출합니다.
            - 실제 리뷰 예시나 세부 내용을 직접 보고 싶을 때 → mode='list'로 호출합니다.

        파라미터:
            - product_id (int | str): 리뷰를 조회할 상품의 고유 ID입니다.
            - sort (Literal[...]): 리뷰 정렬 기준입니다. 기본값은 'up_cnt_desc'(도움이 되는 순)입니다.
            - page_size (int): 사용할 리뷰 개수입니다. 요약 모드 기본값은 20이며, 리스트 모드에서는 내부적으로 최대 10개까지 사용됩니다.
            - mode (Literal['summary', 'list']): 'summary'는 요약 문자열을, 'list'는 리뷰 리스트를 반환합니다.

        반환값:
            - mode='summary'일 때:
                - str: 리뷰 전반의 인상·장단점·사이즈/핏 특성 등을 요약한 문자열입니다.
            - mode='list'일 때:
                - list[dict[str, Any]]: 정제된 리뷰 항목 리스트로, 각 항목에 리뷰 내용과 주요 메타 정보가 포함됩니다.
            - 잘못된 mode가 들어오면:
                - str: 사용 가능한 모드를 안내하는 에러 메시지를 반환합니다.
        """
        product_id = str(product_id)

        # --- 1. 요약(summary) 모드: 모든 요약 관련 로직은 이 블록 안에 위치합니다. ---
        if mode == 'summary':
            logger.info(f'[{product_id}] 리뷰 "요약" 모드 실행 (sort={sort})')
            # --- 1-A. 기본 요약: 'up_cnt_desc'는 DB에서 영구 관리합니다. ---
            if sort == 'up_cnt_desc':  # 기본 요약은 필터가 없을 때만 해당
                # 현재 총 리뷰 개수 확인
                logger.info(f'[{product_id}] 기본 요약(DB) 로직 실행')
                summary_res = await self.service.get_review_summary(product_id)
                current_total_count = summary_res.get('data', [{}])[0].get('total_review_count', 0)

                # DB에서 저장된 요약 조회
                db_summary = await self.db_repository.find_by_id('review_' + product_id)

                # 갱신 필요 여부 판단
                needs_refresh = False
                if db_summary is None or current_total_count > db_summary.get('summarized_review_count', 0) + DEFAULT_SUMMARY_REFRESH_COUNT:
                    needs_refresh = True

                if not needs_refresh:
                    logger.info(f'[{product_id}] DB 캐시 히트. 저장된 요약 반환.')
                    return db_summary['summary']

                # 갱신 로직 실행
                logger.info(f'[{product_id}] DB 요약 갱신 필요.새로운 요약 생성.')
                reviews_res = await self.service.get_review_list(product_id, sort=sort, page_size=page_size)
                new_summary = await self._summarize_reviews_with_llm(reviews_res.get('data', []))

                # Task Queue로 DB 업데이트 작업 예약
                summary_data_for_db = {
                    '_id': 'review_' + product_id,
                    'doc_type': 'review_summary',
                    'product_id': product_id,
                    'summary': new_summary,
                    'summarized_review_count': current_total_count,
                    'updated_at': get_current_utc_timestamp().isoformat(),
                }
                await self.task_queue_client.enqueue_task(REVIEW_SUMMARY_TASK_NAME, summary_data_for_db)

                return new_summary

            # --- 1-B. 특정 조건 요약: 그 외 주요 sort는 Redis에서 단기 캐시합니다. ---
            else:
                should_cache = sort in KEY_SUMMARY_WHITELIST
                redis_key = f'tool-cache:{product_id}:reviews:sort_{sort}' if should_cache else None

                if should_cache:
                    cached_summary = await self.cache_client.get(redis_key)
                    if cached_summary:
                        logger.info(f'[{product_id}] 특정 조건 요약(Redis) 캐시 히트')
                        return cached_summary

                # 캐시 없으면 생성
                logger.info(f'[{product_id}] 특정 조건 요약(Redis) 캐시 미스. API 호출.')
                reviews_res = await self.service.get_review_list(product_id, sort=sort, page_size=page_size)
                specific_summary = await self._summarize_reviews_with_llm(reviews_res.get('data', []))

                if should_cache:
                    logger.info(f'[{product_id}] 특정 조건 요약(Redis) 캐시 저장을 백그라운드 작업으로 위임')
                    await self.task_queue_client.enqueue_task(TOOL_CACHE_TASK_NAME, cache_key=redis_key, cache_value=specific_summary)

                return specific_summary

        # --- 2. 목록(list) 모드: 요약 없이 실제 리뷰 목록만 반환합니다. ---
        elif mode == 'list':
            # 안전장치: 과도한 API 호출 및 토큰 사용 방지
            page_size = min(page_size, 10)

            # Service를 통해 실제 리뷰 데이터 가져오기
            reviews_res = await self.service.get_review_list(product_id, sort=sort, page_size=page_size)

            # (중요) 요약 LLM을 호출하지 않고, 단순히 목록을 가공하는 어댑터만 사용합니다.
            review_list = ProductAdapter.adapt_review_list(reviews_res)

            if not review_list or not isinstance(review_list, list):
                return '해당 조건에 맞는 리뷰가 없습니다.'

            return review_list

        # --- 3. 예외 처리 ---
        else:
            return f"잘못된 'mode'({mode})가 지정되었습니다. 'summary' 또는 'list'를 사용해주세요."
