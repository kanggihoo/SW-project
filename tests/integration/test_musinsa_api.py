from pprint import pprint

import httpx
import pytest

from app.services.musinsa import MusinsaAPIWrapper


@pytest.fixture
def api_wrapper(httpx_client: httpx.AsyncClient) -> MusinsaAPIWrapper:
    """MusinsaAPIWrapper fixture for API testing."""
    return MusinsaAPIWrapper(httpx_client)


class TestMusinsaAPI:
    """Musinsa API 실제 동작 테스트 클래스"""

    # 테스트용 상품 ID (실제 무신사 상품 ID로 변경 필요)
    # TEST_PRODUCT_ID = '4026789'  # 선택 옵션 1개
    TEST_PRODUCT_ID = '5543992'  # 선택 옵션 2개
    # TEST_PRODUCT_ID = '3522389'  # 동일한 스타일의 다른 색상 아이템

    @pytest.mark.asyncio
    async def test_size_recommend(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """사이즈 추천 정보 조회 테스트"""
        print('\n=== 사이즈 추천 정보 조회 테스트 ===')
        try:
            result = await api_wrapper.get_size_recommend(product_id=self.TEST_PRODUCT_ID, height=170, weight=70)
            print(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    print(f'샘플 데이터: {result["data"][0]}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_product_selection_info(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """제품 선택 옵션 정보 조회 테스트"""
        print('\n=== 제품 선택 옵션 정보 조회 테스트 ===')
        try:
            result = await api_wrapper.get_product_selection_info(product_id=self.TEST_PRODUCT_ID)
            print(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    data = result['data'][0]
                    print(f'첫 번째 옵션명: {data.get("first_option_name")}')
                    print(f'두 번째 옵션명: {data.get("secondary_option_name")}')
                    print(f'첫 번째 옵션 개수: {len(data.get("first_options", []))}')
                    print(f'두 번째 옵션 개수: {len(data.get("secondary_options", []))}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    # @pytest.mark.asyncio
    # async def test_product_option_stock(self, api_wrapper: MusinsaAPIWrapper) -> None:
    #     """제품 옵션 및 재고 정보 조회 테스트"""
    #     print('\n=== 제품 옵션 및 재고 정보 조회 테스트 ===')
    #     try:
    #         result = await api_wrapper.get_product_option_stock(product_id=self.TEST_PRODUCT_ID)
    #         pprint(result)
    #         print(f'결과: {"성공" if result["success"] else "실패"}')
    #         print(f'메시지: {result["message"]}')
    #         if result['success']:
    #             print(f'데이터 개수: {len(result["data"])}')
    #             if result['data']:
    #                 data = result['data'][0]
    #                 print(f'옵션 필터 개수: {data.get("option_count")}')
    #                 print(f'재고 옵션 개수: {len(data.get("stock_by_options", []))}')
    #                 if data.get('stock_by_options'):
    #                     sample_stock = data['stock_by_options'][0]
    #                     print(f'샘플 재고 옵션: {sample_stock.get("option_combination")}')
    #                     print(f'품절 여부: {sample_stock.get("is_sold_out")}')
    #         else:
    #             print(f'오류 상세: {result.get("error_details", {})}')
    #     except Exception as e:
    #         print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_product_size(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """제품 실측 사이즈 정보 조회 테스트"""
        print('\n=== 제품 실측 사이즈 정보 조회 테스트 ===')
        try:
            result = await api_wrapper.get_product_size(product_id=self.TEST_PRODUCT_ID)
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    data = result['data'][0]
                    print(f'사이즈 가이드 이미지: {data.get("size_guide_image_url")}')
                    print(f'사이즈 상세 개수: {len(data.get("size_details", []))}')
                    if data.get('size_details'):
                        sample_size = data['size_details'][0]
                        print(f'샘플 사이즈명: {sample_size.get("size_name")}')
                        print(f'측정 항목 개수: {len(sample_size.get("items", []))}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_review_summary(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """리뷰 요약 정보 조회 테스트"""
        print('\n=== 리뷰 요약 정보 조회 테스트 ===')
        try:
            result = await api_wrapper.get_review_summary(product_id=self.TEST_PRODUCT_ID)
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    data = result['data'][0]
                    print(f'총 리뷰 수: {data.get("total_review_count")}')
                    print(f'평균 평점: {data.get("average_rating")}')
                    print(f'일반 리뷰 수: {data.get("general_review_count")}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_filtered_review_count(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """필터링된 리뷰 개수 조회 테스트"""
        print('\n=== 필터링된 리뷰 개수 조회 테스트 ===')
        try:
            result = await api_wrapper.get_filtered_review_count(
                product_id=self.TEST_PRODUCT_ID,
                has_photo=False,
                sex='M',
            )
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    print(f'필터링된 리뷰 개수: {result["data"][0].get("count")}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_review_list(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """리뷰 목록 조회 테스트"""
        print('\n=== 리뷰 목록 조회 테스트 ===')
        try:
            result = await api_wrapper.get_review_list(
                product_id=self.TEST_PRODUCT_ID,
                page_size=5,
                page=0,
                sort='up_cnt_desc',
            )
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'리뷰 개수: {len(result["data"])}')
                if result['data']:
                    sample_review = result['data'][0]
                    print(f'샘플 리뷰 ID: {sample_review.get("id")}')
                    print(f'샘플 리뷰 평점: {sample_review.get("rating")}')
                    print(f'샘플 리뷰 내용 길이: {len(sample_review.get("content", ""))}')
                    user_info = sample_review.get('user_info', {})
                    print(f'사용자 키: {user_info.get("height_cm")}cm')
                    print(f'사용자 몸무게: {user_info.get("weight_kg")}kg')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_product_like_count(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """제품 좋아요 수 조회 테스트"""
        print('\n=== 제품 좋아요 수 조회 테스트 ===')
        try:
            result = await api_wrapper.get_product_like_count(product_id=self.TEST_PRODUCT_ID)
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    print(f'좋아요 수: {result["data"][0].get("count")}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_product_stats(self, api_wrapper: MusinsaAPIWrapper) -> None:
        """제품 통계 정보 조회 테스트"""
        print('\n=== 제품 통계 정보 조회 테스트 ===')
        try:
            result = await api_wrapper.get_product_stats(product_id=self.TEST_PRODUCT_ID)
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    data = result['data'][0]
                    print(f'총 조회수: {data.get("product_view_total")}')
                    print(f'총 구매수: {data.get("purchase_total")}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_product_other_color(
        self,
        api_wrapper: MusinsaAPIWrapper,
    ) -> None:
        """다른 색상 제품 조회 테스트"""
        print('\n=== 다른 색상 제품 조회 테스트 ===')
        try:
            result = await api_wrapper.get_product_other_color(product_id=self.TEST_PRODUCT_ID)
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'다른 색상 제품 개수: {len(result["data"])}')
                if result['data']:
                    sample_color = result['data'][0]
                    print(f'샘플 색상 제품명: {sample_color.get("goods_name")}')
                    print(f'샘플 색상 품절 여부: {sample_color.get("is_sold_out")}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    @pytest.mark.asyncio
    async def test_product_brand_and_price(
        self,
        api_wrapper: MusinsaAPIWrapper,
    ) -> None:
        """제품 브랜드 및 가격 정보 조회 테스트"""
        print('\n=== 제품 브랜드 및 가격 정보 조회 테스트 ===')
        try:
            result = await api_wrapper.get_product_brand_and_price(product_id=self.TEST_PRODUCT_ID)
            pprint(result)
            print(f'결과: {"성공" if result["success"] else "실패"}')
            print(f'메시지: {result["message"]}')
            if result['success']:
                print(f'데이터 개수: {len(result["data"])}')
                if result['data']:
                    data = result['data'][0]
                    brand_info = data.get('brand_info', {})
                    price_info = data.get('price_info', {})
                    print(f'브랜드명: {brand_info.get("brand_name")}')
                    print(f'브랜드 영문명: {brand_info.get("brand_english_name")}')
                    print(f'판매가: {price_info.get("sale_price")}')
                    print(f'정가가: {price_info.get("original_price")}')
                    print(f'할인율: {price_info.get("discount_rate")}%')
                    print(f'세일 여부: {price_info.get("is_on_sale")}')
            else:
                print(f'오류 상세: {result.get("error_details", {})}')
        except Exception as e:
            print(f'예외 발생: {str(e)}')

    # @pytest.mark.asyncio
    # async def test_brand_likes_count(self, api_wrapper: MusinsaAPIWrapper, httpx_client: httpx.AsyncClient) -> None:
    #     """브랜드 좋아요 수 조회 테스트"""
    #     print('\n=== 브랜드 좋아요 수 조회 테스트 ===')
    #     try:
    #         # 테스트를 위해 미리 정의된 브랜드명 사용 (실제로는 위의 테스트 결과를 사용할 수 있음)
    #         brand_name = 'nike'  # 실제 브랜드명으로 변경 필요

    #         result = await api_wrapper.get_brand_likes_count(client=httpx_client, brand_name=brand_name)
    #         print(f'결과: {"성공" if result["success"] else "실패"}')
    #         print(f'메시지: {result["message"]}')
    #         if result['success']:
    #             print(f'데이터 개수: {len(result["data"])}')
    #             if result['data']:
    #                 print(f'브랜드 좋아요 수: {result["data"][0].get("count")}')
    #         else:
    #             print(f'오류 상세: {result.get("error_details", {})}')
    #     except Exception as e:
    #         print(f'예외 발생: {str(e)}')

    # @pytest.mark.asyncio
    # async def test_color_code(self, api_wrapper: MusinsaAPIWrapper, httpx_client: httpx.AsyncClient) -> None:
    #     """색상 코드 조회 테스트"""
    #     print('\n=== 색상 코드 조회 테스트 ===')
    #     try:
    #         result = await api_wrapper.get_color_code(client=httpx_client)
    #         pprint(result)
    #         print(f'결과: {"성공" if result["success"] else "실패"}')
    #         print(f'메시지: {result["message"]}')
    #         if result['success']:
    #             print(f'색상 코드 개수: {len(result["data"])}')
    #             if result['data']:
    #                 # 처음 5개 색상만 출력
    #                 for i, color in enumerate(result['data'][:5]):
    #                     print(f'색상 {i + 1}: ID={color.get("color_id")}, 이름={color.get("color_name")}')
    #                 if len(result['data']) > 5:
    #                     print(f'... 외 {len(result["data"]) - 5}개 색상')
    #         else:
    #             print(f'오류 상세: {result.get("error_details", {})}')
    #     except Exception as e:
    #         print(f'예외 발생: {str(e)}')
