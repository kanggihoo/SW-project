# ruff: noqa: E501
import json
import re
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Literal

import httpx
from bs4 import BeautifulSoup


class ErrorType:
    NO_DATA = 'NO_RECOMMENDATION_DATA'
    HTTP_ERROR = 'HTTP_ERROR'
    UNKNOWN = 'UNKNOWN_EXCEPTION'
    NO_OPTIONS = 'NO_SELECTION_OPTIONS'
    API_ERROR = 'API_REQUEST_FAILED'
    REGEX_MATCH_FAILED = 'REGEX_MATCH_FAILED'
    JSON_PARSING_FAILED = 'JSON_PARSING_FAILED'


def handle_api_errors(error_type: str) -> Callable:
    """
    API 메서드의 에러 처리를 위한 데코레이터.

    Args:
        error_type: 에러 타입 (ErrorType 클래스 상수)

    Returns:
        데코레이터 함수
    """

    def decorator(func: Callable[..., Awaitable[dict]]) -> Callable[..., Awaitable[dict]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> dict:
            # 함수의 첫 번째 파라미터(self 제외)를 error_context로 사용
            error_context = {}
            if args and len(args) > 1:  # self + 추가 파라미터
                param_names = list(func.__code__.co_varnames[1 : func.__code__.co_argcount])  # self 제외
                for i, param_name in enumerate(param_names):
                    if i < len(args) - 1:  # self 제외
                        error_context[param_name] = args[i + 1]
                # kwargs도 추가
                error_context.update(kwargs)

            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                # 429 Rate Limit 에러 특별 처리
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get('Retry-After')
                    error_details = {
                        **error_context,
                        'error_type': ErrorType.API_ERROR,
                        'status_code': 429,
                        'retry_after': retry_after,  # 초 단위 또는 날짜 형식
                    }
                    return {
                        'success': False,
                        'data': [],
                        'message': f'제품 정보 조회 중 오류가 발생했습니다: {str(e)}',
                        'error_details': error_details,
                    }
                # 기타 HTTP 에러
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품 정보 조회 중 오류가 발생했습니다: {str(e)}',
                    'error_details': {**error_context, 'error_type': ErrorType.API_ERROR, 'status_code': e.response.status_code},
                }
            except Exception as e:
                return {
                    'success': False,
                    'data': [],
                    'message': f'알 수 없는 오류가 발생했습니다: {str(e)}',
                    'error_details': {**error_context, 'error_type': error_type},
                }

        return wrapper

    return decorator


class MusinsaAPIWrapper:
    """
    무신사 웹사이트에서 상품 정보를 스크레이핑하기 위한 비동기 API 래퍼 클래스입니다.
    httpx.AsyncClient를 사용하여 HTTP 요청을 관리합니다.
    """

    def __init__(self, client: httpx.AsyncClient):
        """
        클래스 초기화 시, 재사용 가능한 httpx.AsyncClient와 공통 헤더를 설정합니다.
        """
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        self.headers = {'User-Agent': self.user_agent, 'accept': 'application/json'}
        self.timeout = 10.0
        self.client = client

    # =============================================== 상품의 핵심 정보 조회 관련 메서드 ===============================================
    # get_brand_and_price : 상품의 브랜드 이름과 가격 정보를 조회합니다.
    # get_product_stats : 상품의 통계 정보를 조회합니다.
    # get_product_like_count : 상품의 좋아요 수를 조회합니다.
    # get_selection_info : 상품의 선택 옵션 정보를 조회합니다.
    # get_other_color_products : 상품의 다른 색상 제품 정보를 조회합니다.
    # =============================================== =============================================== ===============================================
    @handle_api_errors(ErrorType.API_ERROR)
    async def get_product_brand_and_price(
        self,
        product_id: str | int,
    ) -> dict[str, Any]:
        """
        제품의 브랜드 및 가격 정보를 조회합니다.

        제품 페이지를 직접 스크레이핑하여 해당 제품의 브랜드 정보(한글/영문명)와
        가격 정보(정상가, 판매가, 할인율 등)를 반환합니다.

        Args:
            product_id (str | int): 브랜드 및 가격 정보를 조회할 제품의 고유 ID.

        Returns:
            dict[str, Any]: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [
                            {
                                'brand_info': {
                                    'brand_name': str,
                                    'brand_english_name': str
                                },
                                'price_info': {
                                    'sale_price': int,
                                    'original_price': int,
                                    'discount_rate': int,
                                    'is_on_sale': bool
                                }
                            }
                        ],
                        'message': '제품의 브랜드 및 가격 정보를 성공적으로 조회했습니다.'
                    }

                - 실패 시 (페이지 파싱 오류 등):
                    {
                        'success': False,
                        'data': [],
                        'message': '웹 페이지에서 제품 정보를 추출하는데 실패했습니다.',
                        'error_details': {'error_type': 'REGEX_MATCH_FAILED', ...}
                    }
                    또는
                    {
                        'success': False,
                        'data': [],
                        'message': '웹 페이지 내 데이터의 JSON 형식이 올바르지 않습니다.',
                        'error_details': {'error_type': 'JSON_PARSING_FAILED', ...}
                    }
                - 그 외 API 오류 발생 시:
                    {
                        'success': False,
                        'data': [],
                        'message': '제품 정보 조회 중 오류가 발생했습니다: ...',
                        'error_details': {'error_type': 'API_ERROR', ...}
                    }
        """
        product_id_str = str(product_id)
        response = await self.client.get(
            f'https://www.musinsa.com/products/{product_id_str}',
            headers={'User-Agent': self.user_agent, 'accept': 'text/html', **self.headers},
            timeout=15.0,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.select_one('#pdp-data')
        if not script_tag or not script_tag.string:
            raise ValueError('Could not find product data script tag.')
        match = re.search(r'window\.__MSS__\.product\.state\s*=\s*(\{.*?\});', script_tag.string, re.DOTALL)
        if match:
            product_state_str = match.group(1)
            try:
                product_state_dict = json.loads(product_state_str)
                result_data = [
                    {
                        'brand_info': {
                            'brand_name': product_state_dict['brandInfo']['brandName'],
                            'brand_english_name': product_state_dict['brandInfo']['brandEnglishName'].lower(),
                        },
                        'price_info': {
                            'sale_price': product_state_dict['goodsPrice']['salePrice'],
                            'original_price': product_state_dict['goodsPrice']['normalPrice'],
                            'discount_rate': product_state_dict['goodsPrice']['discountRate'],
                            'is_on_sale': product_state_dict['goodsPrice']['isSale'],
                        },
                    }
                ]
                return {'success': True, 'data': result_data, 'message': '제품의 브랜드 및 가격 정보를 성공적으로 조회했습니다.'}
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'data': [],
                    'message': '웹 페이지 내 데이터의 JSON 형식이 올바르지 않습니다.',
                    'error_details': {'product_id': product_id_str, 'error_type': ErrorType.JSON_PARSING_FAILED},
                }
        else:
            return {
                'success': False,
                'data': [],
                'message': '웹 페이지에서 제품 정보를 추출하는데 실패했습니다.',
                'error_details': {'product_id': product_id_str, 'error_type': ErrorType.REGEX_MATCH_FAILED},
            }

    @handle_api_errors(ErrorType.API_ERROR)
    async def get_product_stats(
        self,
        product_id: str | int,
    ) -> dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id_str}
        try:
            response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/stat', headers=self.headers)
            response.raise_for_status()
            raw_data = response.json()
            if raw_data.get('data') and raw_data.get('meta', {}).get('result') == 'SUCCESS':
                data = raw_data['data']
                stats_data = [{'product_view_total': data.get('pageViewTotal'), 'purchase_total': data.get('purchaseTotal')}]
                return {'success': True, 'data': stats_data, 'message': '제품 통계 정보를 성공적으로 조회했습니다.'}
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품(ID: {product_id_str})의 통계 정보가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'제품 통계 정보 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    @handle_api_errors(ErrorType.API_ERROR)
    async def get_product_like_count(
        self,
        product_id: str | int | list[str | int],
    ) -> dict[str, Any]:
        """
        특정 제품 또는 여러 제품의 '좋아요' 수를 조회합니다.

        단일 제품 ID 또는 제품 ID 리스트를 입력받아, 각 제품별 '좋아요' 수를
        리스트 형태로 반환합니다.

        Args:
            client (httpx.AsyncClient): HTTP 요청을 위한 비동기 클라이언트.
            product_id (str | int | list[str | int]): '좋아요' 수를 조회할
                제품의 고유 ID 또는 ID 리스트.

        Returns:
            dict[str, Any]: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [{'product_id': str, 'count': int}, ...],
                        'message': "제품의 '좋아요' 수를 성공적으로 조회했습니다."
                    }
                    'data' 리스트는 각 제품의 ID와 해당 제품의 '좋아요' 수를 포함하는
                    객체들로 구성됩니다.

                - 실패 시 (정보가 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': "제품(ID: ...)의 '좋아요' 정보를 찾을 수 없습니다.",
                        'error_details': {'error_type': 'NO_DATA', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_ids = product_id if isinstance(product_id, list) else [product_id]
        product_ids_str = [str(pid) for pid in product_ids]
        payload = {'relationIds': product_ids_str}
        response = await self.client.post('https://like.musinsa.com/like/api/v2/liketypes/goods/counts', json=payload, headers=self.headers)
        response.raise_for_status()
        raw_data = response.json()
        if raw_data.get('data', {}).get('success', False):
            items = raw_data.get('data', {}).get('contents', {}).get('items', [])
            like_counts = [{'product_id': item.get('relationId'), 'count': item.get('count')} for item in items]
            return {'success': True, 'data': like_counts, 'message': "제품의 '좋아요' 수를 성공적으로 조회했습니다."}
        else:
            error_context = {'product_ids': product_ids}
            return {
                'success': False,
                'data': [],
                'message': f"제품(ID: {product_ids})의 '좋아요' 정보를 찾을 수 없습니다.",
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    @handle_api_errors(ErrorType.API_ERROR)
    async def get_product_other_color(
        self,
        product_id: str | int,
    ) -> dict[str, Any]:
        """
        동일한 스타일의 다른 색상 제품 목록을 조회합니다.

        특정 제품 ID를 기준으로, 스타일은 동일하지만 색상이 다른 제품들의
        정보(제품 ID, 이름, 이미지 URL, 품절 여부)를 리스트로 반환합니다.

        Args:
            product_id (str | int): 다른 색상 제품을 조회할 기준 제품의 고유 ID.

        Returns:
            dict[str, Any]: API 응답을 나타내는 딕셔너리.
                - 성공 시 (다른 색상 제품이 있는 경우):
                    {
                        'success': True,
                        'data': [
                            {
                                'product_id': int,
                                'goods_name': str,
                                'image_url': str,
                                'is_sold_out': bool
                            },
                            ...
                        ],
                        'message': '다른 색상 제품 정보를 성공적으로 조회했습니다.'
                    }
                    'data' 리스트는 다른 색상 제품의 정보를 담고 있습니다.

                - 성공 시 (다른 색상 제품이 없는 경우):
                    {
                        'success': True,
                        'data': [],
                        'message': '제품(ID: ...)의 다른 색상 제품 정보가 없습니다.'
                    }

                - 실패 시 (API 오류 또는 정보를 찾을 수 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': '제품(ID: ...)의 다른 색상 제품 정보가 없습니다.',
                        'error_details': {'error_type': 'NO_DATA', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_id_str = str(product_id)
        response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/curation/other-color', headers=self.headers)
        response.raise_for_status()
        raw_data = response.json()
        other_color_products = []
        if raw_data.get('data', {}).get('curationTabs'):
            for tab in raw_data['data']['curationTabs']:
                if tab.get('curationType') == 'OTHER_COLOR':
                    for item in tab.get('curationGoodsList', []):
                        other_color_products.append(
                            {
                                'product_id': item.get('goodsNo'),
                                'goods_name': item.get('goodsName'),
                                'image_url': item.get('imageUrl'),
                                'is_sold_out': item.get('isSoldOut'),
                            }
                        )
                    break
        if other_color_products:
            if len(other_color_products) == 1 and str(other_color_products[0].get('product_id')) == product_id_str:
                return {'success': True, 'data': [], 'message': f'제품(ID: {product_id_str})의 다른 색상 제품 정보가 없습니다.'}
            return {'success': True, 'data': other_color_products, 'message': '다른 색상 제품 정보를 성공적으로 조회했습니다.'}
        else:
            error_context = {'product_id': product_id_str}
            return {
                'success': False,
                'data': [],
                'message': f'제품(ID: {product_id_str})의 다른 색상 제품 정보가 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    @handle_api_errors(ErrorType.API_ERROR)
    async def get_product_selection_info(
        self,
        product_id: str | int,
    ) -> dict[str, Any]:
        """
        특정 제품의 구매를 위한 선택 옵션 정보를 조회합니다.

        이 메서드는 제품 ID를 받아 해당 제품의 색상, 사이즈 등과 같은
        선택 가능한 옵션 목록을 반환합니다. 옵션은 최대 2개까지 있을 수 있습니다.

        Args:
            product_id (str | int): 조회할 제품의 고유 ID.

        Returns:
            dict[str, Any]: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [
                            {
                                'option_count': int,
                                'first_option_name': str,
                                'secondary_option_name': str,
                                'first_options': [{'item_id': int, 'name': str}, ...],
                                'secondary_options': [{'item_id': int, 'name': str}, ...]
                            }
                        ],
                        'message': '제품 선택 옵션을 성공적으로 조회했습니다.'
                    }
                    'data' 리스트는 제품의 선택 옵션 정보를 담고 있습니다.
                    'option_count'는 옵션의 개수(1 또는 2)를 나타냅니다.
                    'first_options'는 첫 번째 옵션(예: 색상)의 목록이며,
                    'secondary_options'는 두 번째 옵션(예: 사이즈)의 목록입니다.
                    옵션이 하나일 경우 'secondary_options'는 비어 있습니다.

                - 실패 시 (선택 옵션이 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': '제품(ID: ...)에 대한 선택 옵션 정보가 없습니다.',
                        'error_details': {'error_type': 'NO_OPTIONS', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_id_str = str(product_id)
        response = await self.client.get(
            'https://goods.musinsa.com/api2/review/v1/product/detail/filter', params={'goodsNo': product_id_str}, headers=self.headers
        )
        response.raise_for_status()
        raw_data = response.json()
        filter_option = raw_data.get('data', {}).get('filterOption')
        if filter_option and filter_option.get('optionCount', 0) > 0:
            selection_data = [
                {
                    'option_count': filter_option.get('optionCount'),
                    'first_option_name': filter_option.get('firstName'),
                    'secondary_option_name': filter_option.get('secondName'),
                    'first_options': [{'item_id': opt.get('itemNo'), 'name': opt.get('name')} for opt in filter_option.get('firstOptions', [])],
                    'secondary_options': [{'item_id': opt.get('itemNo'), 'name': opt.get('name')} for opt in filter_option.get('secondOptions', [])],
                }
            ]
            return {'success': True, 'data': selection_data, 'message': '제품 선택 옵션을 성공적으로 조회했습니다.'}
        else:
            error_context = {'product_id': product_id}
            return {
                'success': False,
                'data': [],
                'message': f'제품(ID: {product_id})에 대한 선택 옵션 정보가 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_OPTIONS},
            }

    # ============================================== 사이즈 추천 관련 메서드 ===============================================
    # get_size_recommend : 특정 제품에 대해 사용자의 키와 몸무게를 기반으로 사이즈를 추천합니다.
    # get_product_size : 제품의 실측 사이즈 정보를 조회합니다.
    # ============================================== =============================================== ===============================================
    @handle_api_errors(ErrorType.UNKNOWN)
    async def get_size_recommend(
        self,
        product_id: str | int,
        height: str | int,
        weight: str | int,
    ) -> dict:
        """
        특정 제품에 대해 사용자의 키와 몸무게를 기반으로 사이즈를 추천합니다.

        무신사 API를 호출하여, 동일한 제품을 구매한 다른 사용자들의 신체 정보와
        구매 사이즈 통계를 바탕으로 가장 적합한 사이즈를 추천 목록으로 반환합니다.

        Args:
            product_id (str | int): 사이즈 추천을 조회할 제품의 고유 ID.
            height (str | int): 사용자의 키 (cm).
            weight (str | int): 사용자의 몸무게 (kg).

        Returns:
            dict: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [
                            {'size': str, 'count': int, 'percent': int},
                            ...
                        ],
                        'message': '사이즈 추천 정보를 성공적으로 조회했습니다.'
                    }
                    'data' 리스트의 각 요소는 추천 사이즈, 해당 사이즈를 구매한 사람 수,
                    그리고 전체 추천 중 차지하는 비율(percent)을 포함합니다.
                - 실패 시 (추천 데이터가 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': '해당 조건에 맞는 사이즈 추천 데이터가 없습니다.',
                        'error_details': {'error_type': 'NO_RECOMMENDATION_DATA', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_id_str = str(product_id)
        height_str = str(height)
        weight_str = str(weight)
        params = {'height': height_str, 'weight': weight_str}
        response = await self.client.get(
            f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/size-recommend', params=params, headers=self.headers
        )
        response.raise_for_status()
        raw_data = response.json()
        if raw_data.get('data', {}).get('sizeRecommends'):
            size_recommends = [
                {'size': recommend.get('goodsOpt'), 'count': recommend.get('count'), 'percent': recommend.get('percent')}
                for recommend in raw_data['data']['sizeRecommends']
            ]
            return {
                'success': True,
                'data': size_recommends,
                'message': '사이즈 추천 정보를 성공적으로 조회했습니다.',
            }
        else:
            error_context = {'product_id': product_id, 'height': height, 'weight': weight}
            return {
                'success': False,
                'data': [],
                'message': '해당 조건에 맞는 사이즈 추천 데이터가 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    # TODO : 어차피 mongodb에서 크롤링 해서 가져왔을텐데 사이즈 정보 도구 호출이 필요할까??
    @handle_api_errors(ErrorType.API_ERROR)
    async def get_product_size(
        self,
        product_id: str | int,
    ) -> dict:
        """
        제품의 실측 사이즈 정보를 조회합니다.

        제품 ID를 기반으로, 각 사이즈(S, M, L 등)별 상세 치수 정보와
        사이즈 가이드 이미지 URL을 반환합니다.

        Args:
            product_id (str | int): 조회할 제품의 고유 ID.

        Returns:
            dict: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [
                            {
                                'product_id': str,
                                'size_guide_image_url': str,
                                'size_details': [
                                    {
                                        'size_name': str,
                                        'items': [{'name': str, 'value': float}, ...]
                                    },
                                    ...
                                ]
                            }
                        ],
                        'message': '제품 실측 사이즈 정보를 성공적으로 조회했습니다.'
                    }
                    'size_details' 리스트는 사이즈별 상세 정보를 담고 있습니다.
                    각 사이즈('size_name')에는 '총장', '허리단면' 등 상세 치수('items') 목록이 포함됩니다.

                - 실패 시 (사이즈 정보가 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': '제품(ID: ...)의 실측 사이즈 정보가 없습니다.',
                        'error_details': {'error_type': 'NO_DATA', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_id_str = str(product_id)
        response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/actual-size', headers=self.headers)
        response.raise_for_status()
        raw_data = response.json()
        if raw_data.get('data') and raw_data['data'].get('sizes'):
            data = raw_data['data']
            size_details = []
            for size in data.get('sizes', []):
                size_details.append(
                    {
                        'size_name': size.get('name'),
                        'items': [{'name': item.get('name'), 'value': item.get('value')} for item in size.get('items', [])],
                    }
                )
            result_data = [
                {
                    'product_id': product_id_str,
                    'size_guide_image_url': 'https:' + data['webImage'] if data.get('webImage') else '',
                    'size_details': size_details,
                }
            ]
            return {'success': True, 'data': result_data, 'message': '제품 실측 사이즈 정보를 성공적으로 조회했습니다.'}
        else:
            error_context = {'product_id': product_id_str}
            return {
                'success': False,
                'data': [],
                'message': f'제품(ID: {product_id_str})의 실측 사이즈 정보가 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    @handle_api_errors(ErrorType.API_ERROR)
    async def get_product_option_stock(
        self,
        product_id: str | int,
    ) -> dict[str, Any]:
        product_id_str = str(product_id)
        params = {'goodsSaleType': 'SALE', 'optKindCd': 'CLOTHES'}
        response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/options', params=params, headers=self.headers)
        response.raise_for_status()
        raw_data = response.json()
        if raw_data.get('data'):
            data = raw_data['data']
            option_filters = []
            for option_filter in sorted(data.get('basic', []), key=lambda x: x['sequence']):
                option_filters.append(
                    {
                        'name': option_filter.get('name'),
                        'display_type': option_filter.get('displayType'),
                        'values': [
                            {'id': val.get('no'), 'name': val.get('name'), 'code': val.get('code')} for val in option_filter.get('optionValues', [])
                        ],
                    }
                )
            stock_by_options = []
            for item in sorted(data.get('optionItems', []), key=lambda x: x['no']):
                stock_by_options.append(
                    {
                        'option_combination': [val.get('name') for val in item.get('optionValues', [])],
                        'option_ids': [val.get('no') for val in item.get('optionValues', [])],
                        'is_sold_out': item.get('isSoldOut', True),
                        'is_out_of_stock': item.get('outOfStock', True),
                        'is_deleted': item.get('isDeleted', True),
                    }
                )
            result_data = [
                {
                    'product_id': product_id_str,
                    'option_count': len(option_filters),
                    'option_filters': option_filters,
                    'stock_by_options': stock_by_options,
                }
            ]
            return {'success': True, 'data': result_data, 'message': '제품 옵션 및 재고 정보를 성공적으로 조회했습니다.'}
        else:
            error_context = {'product_id': product_id_str}
            return {
                'success': False,
                'data': [],
                'message': f'제품(ID: {product_id_str})의 옵션 정보를 찾을 수 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    # ============================================== 리뷰 관련 메서드 ===============================================
    # get_review_summary : 제품에 대한 리뷰 요약 정보를 조회합니다.
    # get_filtered_review_count : 특정 조건으로 필터링된 리뷰의 개수를 조회합니다.
    # get_review_list : 필터링 및 정렬 조건에 맞는 제품 리뷰 목록을 페이지별로 조회합니다.
    # ============================================== =============================================== ===============================================
    @handle_api_errors(ErrorType.API_ERROR)
    async def get_review_summary(
        self,
        product_id: str | int,
    ) -> dict[str, Any]:
        """
        제품에 대한 리뷰 요약 정보를 조회합니다.

        제품 ID를 사용하여 해당 제품의 전체 리뷰 수, 스타일 리뷰 수,
        월간 리뷰 수, 일반 리뷰 수 및 평균 평점 정보를 반환합니다.

        Args:
            product_id (str | int): 리뷰 요약을 조회할 제품의 고유 ID.

        Returns:
            dict[str, Any]: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [
                            {
                                'product_id': str,
                                'total_review_count': int,
                                'style_review_count': int,
                                'monthly_review_count': int,
                                'general_review_count': int,
                                'average_rating': float
                            }
                        ],
                        'message': '리뷰 요약 정보를 성공적으로 조회했습니다.'
                    }
                    'data' 리스트는 제품의 리뷰 통계 정보를 담고 있습니다.

                - 실패 시 (리뷰 요약 정보가 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': '제품(ID: ...)의 리뷰 요약 정보가 없습니다.',
                        'error_details': {'error_type': 'NO_DATA', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_id_str = str(product_id)
        response = await self.client.get(f'https://goods.musinsa.com/api2/review/v1/goods/{product_id_str}/reviews/summary', headers=self.headers)
        response.raise_for_status()
        raw_data = response.json()
        if raw_data.get('data') and raw_data.get('meta', {}).get('result') == 'SUCCESS':
            data = raw_data['data']
            result_data = [
                {
                    'product_id': product_id_str,
                    'total_review_count': data.get('totalCount', 0),
                    'style_review_count': data.get('styleCount', 0),
                    'monthly_review_count': data.get('monthCount', 0),
                    'general_review_count': data.get('generalCount', 0) + data.get('photoCount', 0) + data.get('goodsCount', 0),
                    'average_rating': data.get('satisfactionScore', 0.0),
                }
            ]
            return {'success': True, 'data': result_data, 'message': '리뷰 요약 정보를 성공적으로 조회했습니다.'}
        else:
            error_context = {'product_id': product_id_str}
            return {
                'success': False,
                'data': [],
                'message': f'제품(ID: {product_id_str})의 리뷰 요약 정보가 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    @handle_api_errors(ErrorType.API_ERROR)
    async def get_filtered_review_count(
        self,
        product_id: str | int,
        has_photo: bool = False,
        option_list: list[str] | None = None,
        sex: Literal['M', 'F'] | None = None,
    ) -> dict[str, Any]:
        """
        특정 조건으로 필터링된 제품 리뷰의 개수를 조회합니다.

        제품 ID와 함께 사진 포함 여부, 제품 옵션(사이즈 등), 작성자 성별 등의
        필터링 조건을 적용하여 해당하는 리뷰의 총 개수를 반환합니다.

        Args:
            product_id (str | int): 리뷰 개수를 조회할 제품의 고유 ID.
            has_photo (bool, optional): 사진이 포함된 리뷰만 필터링할지 여부. Defaults to False.
            option_list (list[str] | None, optional): 필터링할 제품 옵션(예: 'L', 'XL')의 리스트. Defaults to None.
            sex (Literal['M', 'F'] | None, optional): 필터링할 작성자의 성별 ('M' 또는 'F'). Defaults to None.

        Returns:
            dict[str, Any]: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [{'count': int}],
                        'message': '필터링된 리뷰 개수를 성공적으로 조회했습니다.'
                    }
                    'data' 리스트는 필터링된 리뷰의 총 개수를 포함합니다.

                - 실패 시 (리뷰 정보가 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': '제품(ID: ...)의 리뷰 개수 정보가 없습니다.',
                        'error_details': {'error_type': 'NO_DATA', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_id_str = str(product_id)
        params = {'goodsNo': product_id_str, 'hasPhoto': has_photo, 'option1List': option_list, 'sex': sex, 'selectedSimilarNo': product_id_str}
        params = {k: v for k, v in params.items() if v}
        response = await self.client.get('https://goods.musinsa.com/api2/review/v1/view/list/count', params=params, headers=self.headers)
        response.raise_for_status()
        raw_data = response.json()
        if raw_data.get('meta', {}).get('result') == 'SUCCESS' and 'data' in raw_data:
            result_data = [{'count': raw_data['data']}]
            return {'success': True, 'data': result_data, 'message': '필터링된 리뷰 개수를 성공적으로 조회했습니다.'}
        else:
            error_context = {'product_id': product_id, 'has_photo': has_photo, 'option_list': option_list, 'sex': sex}
            return {
                'success': False,
                'data': [],
                'message': f'제품(ID: {product_id_str})의 리뷰 개수 정보가 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    @handle_api_errors(ErrorType.API_ERROR)
    async def get_review_list(
        self,
        product_id: str | int,
        page_size: int = 10,
        page: int = 0,
        sort: Literal['up_cnt_desc', 'new', 'comment_cnt_desc', 'goods_est_desc', 'goods_est_asc'] = 'up_cnt_desc',
        option_list: list[str] | None = None,
        sex: Literal['M', 'F'] | None = None,
        is_experience: bool = False,
        has_photo: bool = False,
    ) -> dict[str, Any]:
        """
        필터링 및 정렬 조건에 맞는 제품 리뷰 목록을 페이지별로 조회합니다. (해당 조건에 맞는 전체 개수보다 page_size*(page+1) 값이 커버리면 반환되는 데이터 없음 )

        다양한 필터(사진 여부, 성별, 제품 옵션 등)와 정렬 조건(추천순, 최신순 등)을
        적용하여 조건에 맞는 리뷰 목록을 가져옵니다. 페이지네이션을 지원합니다.

        Args:
            product_id (str | int): 리뷰를 조회할 제품의 고유 ID.
            page_size (int, optional): 한 페이지에 표시할 리뷰 수. Defaults to 10.
            page (int, optional): 조회할 페이지 번호. Defaults to 1.
            option_list (list[str] | None, optional): 필터링할 제품 옵션(사이즈 등)의 리스트. Defaults to None.
            sex (Literal['M', 'F'] | None, optional): 필터링할 작성자의 성별. Defaults to None.
            sort (Literal[...], optional): 리뷰 정렬 순서.
                - 'up_cnt_desc': 유용한 순
                - 'new': 최신순
                - 'comment_cnt_desc': 댓글 많은 순
                - 'goods_est_desc': 평점 높은 순
                - 'goods_est_asc': 평점 낮은 순
                Defaults to 'up_cnt_desc'.
            is_experience (bool, optional): 체험단 리뷰만 조회할지 여부. Defaults to False.
            has_photo (bool, optional): 사진이 포함된 리뷰만 조회할지 여부. Defaults to False.

        Returns:
            dict[str, Any]: API 응답을 나타내는 딕셔너리.
                - 성공 시:
                    {
                        'success': True,
                        'data': [
                            {
                                'id': int,
                                'content': str,
                                'rating': str,
                                'goods_option': str,
                                'created_at': str,
                                'like_count': int,
                                'user_info': {
                                    'level': int,
                                    'sex': str,
                                    'height_cm': int,
                                    'weight_kg': int
                                }
                            },
                            ...
                        ],
                        'message': '리뷰 목록을 성공적으로 조회했습니다.'
                    }
                    'data'는 조건에 맞는 리뷰 객체의 리스트입니다.

                - 실패 시 (리뷰가 없는 경우):
                    {
                        'success': False,
                        'data': [],
                        'message': '해당 조건에 맞는 리뷰가 없습니다.',
                        'error_details': {'error_type': 'NO_DATA', ...}
                    }
                - 그 외 API 오류 발생 시:
                    handle_api_errors 데코레이터에 의해 처리된 에러 응답 딕셔너리.
        """
        product_id_str = str(product_id)
        params = {
            'goodsNo': product_id_str,
            'selectedSimilarNo': product_id_str,
            'pageSize': page_size,
            'page': page,
            'sort': sort,
            'isExperience': is_experience,
            'option1List': option_list,
            'hasPhoto': has_photo,
            'sex': sex,
        }
        params = {k: v for k, v in params.items() if v}
        response = await self.client.get('https://goods.musinsa.com/api2/review/v1/view/list', params=params, headers=self.headers)
        response.raise_for_status()
        raw_data = response.json()
        if raw_data.get('data', {}).get('list'):
            review_list = []
            for review in raw_data['data']['list']:
                user_profile = review.get('userProfileInfo', {})
                review_list.append(
                    {
                        'id': review.get('no'),
                        'content': review.get('content'),
                        'rating': review.get('grade'),
                        'goods_option': review.get('goodsOption'),
                        'created_at': review.get('createDate'),
                        'like_count': review.get('likeCount'),
                        'user_info': {
                            'level': user_profile.get('userLevel'),
                            'sex': user_profile.get('reviewSex'),
                            'height_cm': user_profile.get('userHeight'),
                            'weight_kg': user_profile.get('userWeight'),
                        },
                    }
                )
            return {'success': True, 'data': review_list, 'message': '리뷰 목록을 성공적으로 조회했습니다.'}
        else:
            error_context = {
                'product_id': product_id,
                'page_size': page_size,
                'page': page,
                'option_list': option_list,
                'sex': sex,
                'sort': sort,
                'is_experience': is_experience,
                'has_photo': False,
            }
            return {
                'success': False,
                'data': [],
                'message': '해당 조건에 맞는 리뷰가 없습니다.',
                'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
            }

    # @handle_api_errors(ErrorType.API_ERROR)
    # async def get_brand_likes_count(
    #     self,
    #     client: httpx.AsyncClient,
    #     brand_name: str | list[str],
    # ) -> dict[str, Any]:
    #     brand_names = [brand_name.lower()] if isinstance(brand_name, str) else [name.lower() for name in brand_name]
    #     payload = {'relationIds': brand_names}
    #     response = await client.post('https://like.musinsa.com/like/api/v2/liketypes/brand/counts', json=payload, headers=self.headers)
    #     response.raise_for_status()
    #     raw_data = response.json()
    #     if raw_data.get('data', {}).get('success', False):
    #         items = raw_data.get('data', {}).get('contents', {}).get('items', [])
    #         like_counts = [{'brand_name': item.get('relationId'), 'count': item.get('count')} for item in items]
    #         return {'success': True, 'data': like_counts, 'message': "브랜드의 '좋아요' 수를 성공적으로 조회했습니다."}
    #     else:
    #         error_context = {'brand_names': brand_names}
    #         return {
    #             'success': False,
    #             'data': [],
    #             'message': f"브랜드(이름: {brand_names})의 '좋아요' 정보를 찾을 수 없습니다.",
    #             'error_details': {**error_context, 'error_type': ErrorType.NO_DATA, 'reason': raw_data.get('error', {}).get('message')},
    #         }

    # @handle_api_errors(ErrorType.API_ERROR)
    # async def get_color_code(
    #     self,
    #     client: httpx.AsyncClient,
    # ) -> dict[str, Any]:
    #     response = await client.get('https://goods-detail.musinsa.com/api2/goods/color-images', headers=self.headers)
    #     response.raise_for_status()
    #     raw_data = response.json()
    #     if raw_data.get('meta', {}).get('result') == 'SUCCESS':
    #         color_list = sorted(
    #             [
    #                 {'color_id': color.get('colorId'), 'color_name': color.get('colorName')}
    #                 for color in raw_data.get('data', {}).get('colorImages', [])
    #             ],
    #             key=lambda x: int(x['color_id']),
    #         )
    #         return {'success': True, 'data': color_list, 'message': '색상 코드 정보를 성공적으로 조회했습니다.'}
    #     else:
    #         return {
    #             'success': False,
    #             'data': [],
    #             'message': 'API에서 색상 코드 데이터를 반환하지 않았습니다.',
    #             'error_details': {'error_type': ErrorType.NO_DATA},
    #         }
