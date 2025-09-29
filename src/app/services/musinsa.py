import httpx
import json
import re
from typing import Annotated, Literal, Dict, Any, List, Union
from bs4 import BeautifulSoup


class ErrorType:
    NO_DATA = 'NO_RECOMMENDATION_DATA'
    HTTP_ERROR = 'HTTP_ERROR'
    UNKNOWN = 'UNKNOWN_EXCEPTION'
    NO_OPTIONS = 'NO_SELECTION_OPTIONS'
    API_ERROR = 'API_REQUEST_FAILED'
    REGEX_MATCH_FAILED = 'REGEX_MATCH_FAILED'
    JSON_PARSING_FAILED = 'JSON_PARSING_FAILED'


class MusinsaAPIWrapper:
    """
    무신사 웹사이트에서 상품 정보를 스크레이핑하기 위한 비동기 API 래퍼 클래스입니다.
    httpx.AsyncClient를 사용하여 HTTP 요청을 관리합니다.
    """

    def __init__(self):
        """
        클래스 초기화 시, 재사용 가능한 httpx.AsyncClient와 공통 헤더를 설정합니다.
        """
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        self.client = httpx.AsyncClient(headers={'User-Agent': self.user_agent, 'accept': 'application/json'}, timeout=10.0)

    async def close(self):
        """
        애플리케이션 종료 시, httpx.AsyncClient 리소스를 안전하게 닫습니다.
        """
        await self.client.aclose()

    async def get_size_recommend(self, product_id: str | int, height: str | int, weight: str | int) -> dict:
        product_id_str = str(product_id)
        height_str = str(height)
        weight_str = str(weight)
        error_context = {'product_id': product_id, 'height': height, 'weight': weight}
        params = {'height': height_str, 'weight': weight_str}
        try:
            response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/size-recommend', params=params)
            response.raise_for_status()
            raw_data = response.json()
            if raw_data.get('data', {}).get('sizeRecommends'):
                size_recommends = [
                    {'size': recommend.get('goodsOpt'), 'count': recommend.get('count'), 'percent': recommend.get('percent')}
                    for recommend in raw_data['data']['sizeRecommends']
                ]
                return {'success': True, 'data': size_recommends, 'message': '사이즈 추천 정보를 성공적으로 조회했습니다.'}
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': '해당 조건에 맞는 사이즈 추천 데이터가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except httpx.HTTPStatusError as e:
            return {
                'success': False,
                'data': [],
                'message': f'API 서버 에러 (상태 코드: {e.response.status_code})',
                'error_details': {**error_context, 'error_type': ErrorType.HTTP_ERROR, 'status_code': e.response.status_code},
            }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'알 수 없는 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.UNKNOWN},
            }

    async def get_product_selection_info(self, product_id: str | int) -> Dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id}
        try:
            response = await self.client.get('https://goods.musinsa.com/api2/review/v1/product/detail/filter', params={'goodsNo': product_id_str})
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
                        'secondary_options': [
                            {'item_id': opt.get('itemNo'), 'name': opt.get('name')} for opt in filter_option.get('secondOptions', [])
                        ],
                    }
                ]
                return {'success': True, 'data': selection_data, 'message': '제품 선택 옵션을 성공적으로 조회했습니다.'}
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품(ID: {product_id})에 대한 선택 옵션 정보가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_OPTIONS},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'제품 선택 정보 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_product_option_stock(self, product_id: str | int) -> Dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id_str}
        try:
            params = {'goodsSaleType': 'SALE', 'optKindCd': 'CLOTHES'}
            response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/v2/options', params=params)
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
                                {'id': val.get('no'), 'name': val.get('name'), 'code': val.get('code')}
                                for val in option_filter.get('optionValues', [])
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
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품(ID: {product_id_str})의 옵션 정보를 찾을 수 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'옵션 및 재고 정보 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_product_size(self, product_id: str | int) -> dict:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id_str}
        try:
            response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/actual-size')
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
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품(ID: {product_id_str})의 실측 사이즈 정보가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'실측 사이즈 정보 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_review_summary(self, product_id: str | int) -> Dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id_str}
        try:
            response = await self.client.get(f'https://goods.musinsa.com/api2/review/v1/goods/{product_id_str}/reviews/summary')
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
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품(ID: {product_id_str})의 리뷰 요약 정보가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'리뷰 요약 정보 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_filtered_review_count(
        self, product_id: str | int, has_photo: bool = False, option_list: List[str] | None = None, sex: Literal['M', 'F'] | None = None
    ) -> Dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id, 'has_photo': has_photo, 'option_list': option_list, 'sex': sex}
        params = {'goodsNo': product_id_str, 'hasPhoto': has_photo, 'option1List': option_list, 'sex': sex, 'selectedSimilarNo': product_id_str}
        params = {k: v for k, v in params.items() if v}
        try:
            response = await self.client.get('https://goods.musinsa.com/api2/review/v1/view/list/count', params=params)
            response.raise_for_status()
            raw_data = response.json()
            if raw_data.get('meta', {}).get('result') == 'SUCCESS' and 'data' in raw_data:
                result_data = [{'count': raw_data['data']}]
                return {'success': True, 'data': result_data, 'message': '필터링된 리뷰 개수를 성공적으로 조회했습니다.'}
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품(ID: {product_id_str})의 리뷰 개수 정보가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'리뷰 개수 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_review_list(
        self,
        product_id: str | int,
        page_size: int = 10,
        page: int = 1,
        option_list: List[str] | None = None,
        sex: Literal['M', 'F'] | None = None,
        sort: Literal['up_cnt_desc', 'new', 'comment_cnt_desc', 'goods_est_desc', 'goods_est_asc'] = 'up_cnt_desc',
        is_experience: bool = False,
        has_photo: bool = False,
    ) -> Dict[str, Any]:
        product_id_str = str(product_id)
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

        try:
            response = await self.client.get('https://goods.musinsa.com/api2/review/v1/view/list', params=params)
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
                return {
                    'success': False,
                    'data': [],
                    'message': '해당 조건에 맞는 리뷰가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'리뷰 목록 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_product_like_count(self, product_id: Union[str, int, List[Union[str, int]]]) -> Dict[str, Any]:
        product_ids = product_id if isinstance(product_id, list) else [product_id]
        product_ids_str = [str(pid) for pid in product_ids]
        error_context = {'product_ids': product_ids}
        payload = {'relationIds': product_ids_str}
        try:
            response = await self.client.post('https://like.musinsa.com/like/api/v2/liketypes/goods/counts', json=payload)
            response.raise_for_status()
            raw_data = response.json()
            if raw_data.get('data', {}).get('success', False):
                items = raw_data.get('data', {}).get('contents', {}).get('items', [])
                like_counts = [{'product_id': item.get('relationId'), 'count': item.get('count')} for item in items]
                return {'success': True, 'data': like_counts, 'message': "제품의 '좋아요' 수를 성공적으로 조회했습니다."}
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': f"제품(ID: {product_ids})의 '좋아요' 정보를 찾을 수 없습니다.",
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f"'좋아요' 수 조회 중 오류가 발생했습니다: {str(e)}",
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_product_stats(self, product_id: str | int) -> Dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id_str}
        try:
            response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/stat')
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

    async def get_product_other_color(self, product_id: str | int) -> Dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id_str}
        try:
            response = await self.client.get(f'https://goods-detail.musinsa.com/api2/goods/{product_id_str}/curation/other-color')
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
                return {
                    'success': False,
                    'data': [],
                    'message': f'제품(ID: {product_id_str})의 다른 색상 제품 정보가 없습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'다른 색상 제품 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_product_brand_and_price(self, product_id: str | int) -> Dict[str, Any]:
        product_id_str = str(product_id)
        error_context = {'product_id': product_id_str}
        try:
            response = await self.client.get(
                f'https://www.musinsa.com/products/{product_id_str}', headers={'User-Agent': self.user_agent, 'accept': 'text/html'}, timeout=15.0
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
                        'error_details': {**error_context, 'error_type': ErrorType.JSON_PARSING_FAILED},
                    }
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': '웹 페이지에서 제품 정보를 추출하는데 실패했습니다.',
                    'error_details': {**error_context, 'error_type': ErrorType.REGEX_MATCH_FAILED},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f'제품 정보 조회 중 오류가 발생했습니다: {str(e)}',
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_brand_likes_count(self, brand_name: Union[str, List[str]]) -> Dict[str, Any]:
        brand_names = [brand_name.lower()] if isinstance(brand_name, str) else [name.lower() for name in brand_name]
        error_context = {'brand_names': brand_names}
        payload = {'relationIds': brand_names}
        try:
            response = await self.client.post('https://like.musinsa.com/like/api/v2/liketypes/brand/counts', json=payload)
            response.raise_for_status()
            raw_data = response.json()
            if raw_data.get('data', {}).get('success', False):
                items = raw_data.get('data', {}).get('contents', {}).get('items', [])
                like_counts = [{'brand_name': item.get('relationId'), 'count': item.get('count')} for item in items]
                return {'success': True, 'data': like_counts, 'message': "브랜드의 '좋아요' 수를 성공적으로 조회했습니다."}
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': f"브랜드(이름: {brand_names})의 '좋아요' 정보를 찾을 수 없습니다.",
                    'error_details': {**error_context, 'error_type': ErrorType.NO_DATA, 'reason': raw_data.get('error', {}).get('message')},
                }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f"브랜드 '좋아요' 수 조회 중 오류가 발생했습니다: {str(e)}",
                'error_details': {**error_context, 'error_type': ErrorType.API_ERROR},
            }

    async def get_color_code(self) -> Dict[str, Any]:
        error_context = {'error_type': ErrorType.API_ERROR}
        try:
            response = await self.client.get('https://goods-detail.musinsa.com/api2/goods/color-images')
            response.raise_for_status()
            raw_data = response.json()
            if raw_data.get('meta', {}).get('result') == 'SUCCESS':
                color_list = sorted(
                    [
                        {'color_id': color.get('colorId'), 'color_name': color.get('colorName')}
                        for color in raw_data.get('data', {}).get('colorImages', [])
                    ],
                    key=lambda x: int(x['color_id']),
                )
                return {'success': True, 'data': color_list, 'message': '색상 코드 정보를 성공적으로 조회했습니다.'}
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': 'API에서 색상 코드 데이터를 반환하지 않았습니다.',
                    'error_details': {'error_type': ErrorType.NO_DATA},
                }
        except Exception as e:
            return {'success': False, 'data': [], 'message': f'색상 코드 조회 중 오류가 발생했습니다: {str(e)}', 'error_details': error_context}
