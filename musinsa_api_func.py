import httpx 
import pprint
import json
from typing import Annotated, Literal , Dict , Any , List , Union
import re
from bs4 import BeautifulSoup

user_agent ="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

class ErrorType:
    NO_DATA = "NO_RECOMMENDATION_DATA"
    HTTP_ERROR = "HTTP_ERROR"
    UNKNOWN = "UNKNOWN_EXCEPTION"
    NO_OPTIONS = "NO_SELECTION_OPTIONS"
    API_ERROR = "API_REQUEST_FAILED"
    REGEX_MATCH_FAILED = "REGEX_MATCH_FAILED"
    JSON_PARSING_FAILED = "JSON_PARSING_FAILED"

# CHECK : 사이즈 정보랑 색상 정보가 섞여 있거나 선택가능한 필터 정보가 이상한 제품에 대해서는 어떻게 동작하는지 확인필요 
async def get_size_recommend(product_id: str | int, height: str | int, weight: str | int) -> dict:
    """
    사용자의 신체 정보에 따라 특정 제품의 추천 사이즈를 반환합니다.
    실구매자 데이터를 기반으로 가장 많이 선택된 사이즈와 비율을 제공합니다.

    Args:
        product_id: 사이즈 추천을 원하는 제품의 고유 ID.
        height: 사용자의 키 (cm).
        weight: 사용자의 몸무게 (kg).

    Returns:
        성공 시 추천 사이즈 정보가 담긴 딕셔너리, 실패 시 원인 정보가 포함된
        딕셔너리를 반환합니다. 반환 형식은 최상위 모듈의 설명을 따릅니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {"size": "XL", "count": 10, "percent": 80},
            {"size": "L", "count": 2, "percent": 20}
        ],
        "message": "성공적으로 처리되었습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "해당 제품에 대한 구매 정보가 없습니다.",
        "error_details": {
            "product_id": 12345,
            "height": 180,
            "weight": 75,
            "error_type": "NO_DATA"
        }
    }
    """
    # CHANGE 1: 입력 파라미터의 타입을 문자열로 명시적으로 변환하여 일관성을 확보합니다.
    product_id_str = str(product_id)
    height_str = str(height)
    weight_str = str(weight)

    error_context = {
        "product_id": product_id,
        "height": height,
        "weight": weight,
    }

    async with httpx.AsyncClient() as client:
        params = {"height": height_str, "weight": weight_str}
        try:
            response = await client.get(
                f"https://goods-detail.musinsa.com/api2/goods/{product_id_str}/size-recommend",
                params=params,
                headers={
                    "User-Agent": user_agent,
                    "accept": "application/json",
                },
                timeout=10.0 # 타임아웃 설정 추가
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data", {}).get("sizeRecommends"):
                size_recommends = [
                    {
                        "size": recommend.get("goodsOpt"),
                        "count": recommend.get("count"),
                        "percent": recommend.get("percent")
                    }
                    for recommend in raw_data["data"]["sizeRecommends"]
                ]

                return {
                    "success": True,
                    "data": size_recommends,
                    "message": "사이즈 추천 정보를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": "해당 조건에 맞는 사이즈 추천 데이터가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "data": [],
                "message": f"API 서버 에러 (상태 코드: {e.response.status_code})",
                "error_details": {**error_context, "error_type": ErrorType.HTTP_ERROR, "status_code": e.response.status_code}
            }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"알 수 없는 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.UNKNOWN}
            }
#CHECK : dropdown 형태로 선택하는게 아닌 - + 로 선택하는 제품에 대해서는 어떻게 동작하는지 확인 필요 
async def get_product_selection_info(product_id: str | int) -> Dict[str, Any]:
    """제품 페이지에서 선택 가능한 옵션(사이즈, 색상 등) 정보를 조회합니다.

    Args:
        product_id: 옵션 정보를 조회할 제품의 고유 ID.

    Returns:
        성공 시 선택 가능한 옵션 정보가 담긴 딕셔너리를, 실패 시 원인 정보가
        포함된 딕셔너리를 반환합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "option_count": 1,
                "primary_option_name": "사이즈",
                "secondary_option_name": "",
                "primary_options": [
                    {"item_id": 6831017, "name": "M"},
                    {"item_id": 6831018, "name": "L"}
                ],
                "secondary_options": []
            }
        ],
        "message": "성공적으로 처리되었습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "No selection options are available for the product (ID: 12345).",
        "error_details": {
            "product_id": 12345,
            "error_type": "NO_SELECTION_OPTIONS"
        }
    }
    """
    # CHANGE: 입력값 타입 통일 및 에러 컨텍스트 미리 정의
    product_id_str = str(product_id)
    error_context = {"product_id": product_id}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://goods.musinsa.com/api2/review/v1/product/detail/filter",
                params={"goodsNo": product_id_str},
                headers={
                    "User-Agent": user_agent,
                    "accept": "application/json",
                },
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            # CHANGE: 더 명확한 조건으로 데이터 유효성 검사
            filter_option = raw_data.get("data", {}).get("filterOption")
            if filter_option and filter_option.get("optionCount", 0) > 0:
                
                # CHANGE: LLM이 이해하기 쉽도록 키를 snake_case로 변경하고 구조를 재구성
                #         데이터는 일관성을 위해 리스트로 감싸줍니다.
                selection_data = [{
                    "option_count": filter_option.get("optionCount"),
                    "primary_option_name": filter_option.get("firstName"),
                    "secondary_option_name": filter_option.get("secondName"),
                    "primary_options": [
                        {"item_id": opt.get("itemNo"), "name": opt.get("name")}
                        for opt in filter_option.get("firstOptions", [])
                    ],
                    "secondary_options": [
                        {"item_id": opt.get("itemNo"), "name": opt.get("name")}
                        for opt in filter_option.get("secondOptions", [])
                    ],
                }]

                # CHANGE: 표준 성공 응답 형식으로 반환
                return {
                    "success": True,
                    "data": selection_data,
                    "message": "제품 선택 옵션을 성공적으로 조회했습니다."
                }
            else:
                # CHANGE: 표준 실패 응답 형식으로 반환
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_id})에 대한 선택 옵션 정보가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_OPTIONS}
                }
        except Exception as e:
            # CHANGE: 표준 실패 응답 형식으로 반환
            return {
                "success": False,
                "data": [],
                "message": f"제품 선택 정보 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }

async def get_product_option_stock(product_id: str | int) -> Dict[str, Any]:
    """
    제품의 선택 가능한 옵션과 각 옵션 조합별 재고 상태를 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "product_id": "4637965",
                "option_count": 1,
                "option_filters": [
                    {
                        "name": "사이즈",
                        "display_type": "DROPDOWN",
                        "values": [
                            {"id": 16569117, "name": "M", "code": "M"},
                            {"id": 16569118, "name": "L", "code": "L"}
                        ]
                    }
                ],
                "stock_by_options": [
                    {
                        "option_combination": ["M"],
                        "option_ids": [16569117],
                        "is_sold_out": false,
                        "is_out_of_stock": false,
                        "is_deleted": false
                    }
                ]
            }
        ],
        "message": "제품 옵션 및 재고 정보를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "제품(ID: 4637965)의 옵션 정보를 찾을 수 없습니다.",
        "error_details": {
            "product_id": "4637965",
            "error_type": "NO_DATA"
        }
    }
    """
    product_id_str = str(product_id)
    error_context = {"product_id": product_id_str}
    
    async with httpx.AsyncClient() as client:
        try:
            params = {"goodsSaleType": "SALE", "optKindCd": "CLOTHES"}
            response = await client.get(
                f"https://goods-detail.musinsa.com/api2/goods/{product_id_str}/v2/options",
                params=params,
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data"):
                data = raw_data["data"]
                
                # 1. 옵션 필터 정보 파싱 (snake_case 및 구조 개선)
                option_filters = []
                # API 응답에서 basic 필드가 없을 경우를 대비하여 .get() 사용
                for option_filter in sorted(data.get("basic", []), key=lambda x: x["sequence"]):
                    option_filters.append({
                        "name": option_filter.get("name"),
                        "display_type": option_filter.get("displayType"),
                        "values": [
                            {
                                "id": val.get("no"),
                                "name": val.get("name"),
                                "code": val.get("code")
                            } for val in option_filter.get("optionValues", [])
                        ]
                    })

                # 2. 옵션 조합별 재고 정보 파싱 (snake_case 및 구조 개선)
                stock_by_options = []
                for item in sorted(data.get("optionItems", []), key=lambda x: x["no"]):
                    stock_by_options.append({
                        "option_combination": [val.get("name") for val in item.get("optionValues", [])],
                        "option_ids": [val.get("no") for val in item.get("optionValues", [])],
                        "is_sold_out": item.get("isSoldOut", True),
                        "is_out_of_stock": item.get("outOfStock", True),
                        "is_deleted": item.get("isDeleted", True)
                    })

                # 3. 최종 데이터 구조화 (항상 list로 감싸기)
                result_data = [{
                    "product_id": product_id_str,
                    "option_count": len(option_filters),
                    "option_filters": option_filters,
                    "stock_by_options": stock_by_options
                }]

                return {
                    "success": True,
                    "data": result_data,
                    "message": "제품 옵션 및 재고 정보를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_id_str})의 옵션 정보를 찾을 수 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"옵션 및 재고 정보 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }


async def get_product_size(product_id : str | int) -> dict:
    """
    제품의 옵션별 실측 사이즈 정보와 사이즈 가이드 이미지 URL을 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "product_id": "4447189",
                "size_guide_image_url": "https://image.musinsa.com/images/size_type/detail_img/20231226.png",
                "size_details": [
                    {
                        "size_name": "M",
                        "items": [
                            {"name": "총장", "value": 68.0},
                            {"name": "가슴단면", "value": 62.0}
                        ]
                    },
                    {
                        "size_name": "L",
                        "items": [
                            {"name": "총장", "value": 71.0},
                            {"name": "가슴단면", "value": 64.0}
                        ]
                    }
                ]
            }
        ],
        "message": "제품 실측 사이즈 정보를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "제품(ID: 4447189)의 실측 사이즈 정보가 없습니다.",
        "error_details": {
            "product_id": "4447189",
            "error_type": "NO_DATA"
        }
    }
    """
    product_id_str = str(product_id)
    error_context = {"product_id": product_id_str}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://goods-detail.musinsa.com/api2/goods/{product_id_str}/actual-size",
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data") and raw_data["data"].get("sizes"):
                data = raw_data["data"]
                
                # 사용자가 제안한 유연한 구조를 그대로 사용합니다.
                size_details = []
                for size in data.get("sizes", []):
                    size_details.append({
                        "size_name": size.get("name"),
                        "items": [
                            {"name": item.get("name"), "value": item.get("value")}
                            for item in size.get("items", [])
                        ]
                    })

                # 표준 반환 형식을 위해 최종 데이터를 리스트로 감싸고 키 이름을 수정합니다.
                result_data = [{
                    "product_id": product_id_str,
                    "size_guide_image_url": "https:" + data["webImage"] if data.get("webImage") else "",
                    "size_details": size_details
                }]

                return {
                    "success": True,
                    "data": result_data,
                    "message": "제품 실측 사이즈 정보를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_id_str})의 실측 사이즈 정보가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"실측 사이즈 정보 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }

async def get_review_summary(product_id: str | int) -> Dict[str, Any]:
    """
    제품에 대한 리뷰 요약 정보(총 개수, 유형별 개수, 평균 평점 등)를 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "product_id": "4637965",
                "total_review_count": 24,
                "style_review_count": 5,
                "monthly_review_count": 1,
                "general_review_count": 18,
                "average_rating": 4.8
            }
        ],
        "message": "리뷰 요약 정보를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "제품(ID: 4637965)의 리뷰 요약 정보가 없습니다.",
        "error_details": {
            "product_id": "4637965",
            "error_type": "NO_DATA"
        }
    }
    """
    product_id_str = str(product_id)
    error_context = {"product_id": product_id_str}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://goods.musinsa.com/api2/review/v1/goods/{product_id_str}/reviews/summary",
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data") and raw_data.get("meta", {}).get("result") == "SUCCESS":
                data = raw_data["data"]

                # API 응답이 없을 경우를 대비해 .get()으로 안전하게 접근하고, 키 이름을 더 명확하게 변경합니다.
                result_data = [{
                    "product_id": product_id_str,
                    "total_review_count": data.get("totalCount", 0),
                    "style_review_count": data.get("styleCount", 0),
                    "monthly_review_count": data.get("monthCount", 0),
                    "general_review_count": data.get("generalCount", 0) + data.get("photoCount", 0) + data.get("goodsCount", 0),
                    "average_rating": data.get("satisfactionScore", 0.0) # 'socre' 오타 수정 및 이름 명확화
                }]

                return {
                    "success": True,
                    "data": result_data,
                    "message": "리뷰 요약 정보를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_id_str})의 리뷰 요약 정보가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"리뷰 요약 정보 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }


async def get_filtered_review_count(product_id : str | int,
                           has_photo:bool=False,
                           option_list:Annotated[list[str] , "선택 가능한 옵션"] = [],
                           sex:Annotated[str, Literal["M", "F"] , "남성 또는 여성 , 모든 성별 포함할거면 sex 쿼리 파라미터 없이"] = "",
                        )->Dict[str, Any]:
    """
    지정된 조건(사진 유무, 옵션, 성별)에 맞는 제품 리뷰의 총 개수를 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {"count": 2206}
        ],
        "message": "필터링된 리뷰 개수를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "제품(ID: 12345)의 리뷰 개수 정보가 없습니다.",
        "error_details": {
            "product_id": 12345,
            "has_photo": false,
            "option_list": ["BLACK", "M"],
            "sex": "M",
            "error_type": "NO_DATA"
        }
    }
    """
    product_id_str = str(product_id)
    # 실패 시 입력된 파라미터를 그대로 반환하기 위해 error_context를 구성합니다.
    error_context = {
        "product_id": product_id,
        "has_photo": has_photo,
        "option_list": option_list,
        "sex": sex
    }

    async with httpx.AsyncClient() as client:
        try:
            params = {
                "goodsNo": product_id_str,
                "hasPhoto": has_photo,
                "option1List": option_list,
                "sex": sex
            }
            # 빈 파라미터는 전송하지 않도록 정리합니다.
            params = {k: v for k, v in params.items() if v}

            response = await client.get(
                "https://goods.musinsa.com/api2/review/v1/view/list/count",
                params=params,
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            # API 응답에서 data 필드의 존재 여부를 명확히 확인합니다.
            if raw_data.get("meta", {}).get("result") == "SUCCESS" and "data" in raw_data:
                # 일관성을 위해 숫자 데이터를 딕셔너리를 포함한 리스트로 감싸줍니다.
                result_data = [{"count": raw_data["data"]}]
                return {
                    "success": True,
                    "data": result_data,
                    "message": "필터링된 리뷰 개수를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_id_str})의 리뷰 개수 정보가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"리뷰 개수 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }


#CHECK 여기서 sizes 옵션값이 어떤거지?? 
async def get_review_list(
    product_id: str | int,
    page_size: int = 10,
    page: int = 1,
    option_list: List[str] = [],
    sex: Literal["M", "F", ""] = "",
    sort: Literal["up_cnt_desc", "new", "comment_cnt_desc", "goods_est_desc", "goods_est_asc"] = "up_cnt_desc",
    is_experience: bool = False
) -> Dict[str, Any]:
    """
    지정된 조건(페이지, 옵션, 성별, 정렬 등)에 맞는 제품 리뷰 목록을 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "id": 7980094,
                "content": "정말 무난한 데일리용 입니다...",
                "rating": 5,
                "goods_option": "M",
                "created_at": "2020-01-19T00:15:33.000+09:00",
                "like_count": 10,
                "user_info": 
                    "level": "LV4",
                    "sex": "남성",
                    "height_cm": 178,
                    "weight_kg": 86
                }
            }
        ],
        "message": "리뷰 목록을 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "해당 조건에 맞는 리뷰가 없습니다.",
        "error_details": {
            "product_id": 12345,
            "page_size": 10,
            "page": 1,
            "option_list": [],
            "sex": "M",
            "sort": "new",
            "error_type": "NO_DATA"
        }
    }
    """
    product_id_str = str(product_id)
    error_context = {
        "product_id": product_id, "page_size": page_size, "page": page,
        "option_list": option_list, "sex": sex, "sort": sort, "is_experience": is_experience
    }

    async with httpx.AsyncClient() as client:
        try:
            params = {
                "goodsNo": product_id_str, "pageSize": page_size, "page": page,
                "sort": sort, "isExperience": is_experience, "hasPhoto": False,
            }
            if option_list:
                params["option1List"] = option_list
            if sex:
                params["sex"] = sex

            response = await client.get(
                "https://goods.musinsa.com/api2/review/v1/view/list",
                params=params,
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data", {}).get("list"):
                review_list = []
                for review in raw_data["data"]["list"]:
                    user_profile = review.get("userProfileInfo", {})
                    review_list.append({
                        "id": review.get("no"),
                        "content": review.get("content"),
                        "rating": review.get("grade"),
                        "goods_option": review.get("goodsOption"), # 'godds_option' 오타 수정
                        "created_at": review.get("createDate"), # 키 이름 일관성
                        "like_count": review.get("likeCount"),
                        "user_info": {
                            "level": user_profile.get("userLevel"),
                            "sex": user_profile.get("reviewSex"),
                            "height_cm": user_profile.get("userHeight"),
                            "weight_kg": user_profile.get("userWeight")
                        }
                    })

                return {
                    "success": True,
                    "data": review_list, # data 필드에 리스트를 직접 할당
                    "message": "리뷰 목록을 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": "해당 조건에 맞는 리뷰가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"리뷰 목록 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }
        
async def get_product_like_count(product_id: Union[str, int, List[Union[str, int]]]) -> Dict[str, Any]:
    """
    하나 또는 여러 제품의 '좋아요' 수를 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {"product_id": 4637965, "count": 1500},
            {"product_id": 4637966, "count": 2300}
        ],
        "message": "제품의 '좋아요' 수를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "제품(ID: [4637965])의 '좋아요' 정보를 찾을 수 없습니다.",
        "error_details": {
            "product_ids": [4637965],
            "error_type": "NO_DATA"
        }
    }
    """
    product_ids = product_id if isinstance(product_id, list) else [product_id]
    product_ids_str = [str(pid) for pid in product_ids] # API가 문자열 리스트를 요구할 수 있으므로 변환
    
    error_context = {"product_ids": product_ids}

    async with httpx.AsyncClient() as client:
        try:
            payload = {"relationIds": product_ids_str}
            response = await client.post(
                url="https://like.musinsa.com/like/api/v2/liketypes/goods/counts",
                json=payload,
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data", {}).get("success", False):
                items = raw_data.get("data", {}).get("contents", {}).get("items", [])
                
                like_counts = [
                    {
                        "product_id": item.get("relationId"),
                        "count": item.get("count")
                    } for item in items
                ]

                return {
                    "success": True, # 불리언 타입으로 수정
                    "data": like_counts,
                    "message": "제품의 '좋아요' 수를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_ids})의 '좋아요' 정보를 찾을 수 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"'좋아요' 수 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }
    
async def get_product_stats(product_id: str | int) -> Dict[str, Any]:
    """
    제품의 통계 정보(최근 1달 조회수, 누적 판매수)를 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "product_view_total": 12345,
                "purchase_total": 5678
            }
        ],
        "message": "제품 통계 정보를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "제품(ID: 12345)의 통계 정보가 없습니다.",
        "error_details": {
            "product_id": 12345,
            "error_type": "NO_DATA"
        }
    }
    """
    product_id_str = str(product_id)
    error_context = {"product_id": product_id_str}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://goods-detail.musinsa.com/api2/goods/{product_id_str}/stat",
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data") and raw_data.get("meta", {}).get("result") == "SUCCESS":
                data = raw_data["data"]
                
                # 일관성을 위해 최종 데이터를 리스트로 감싸줍니다.
                stats_data = [{
                    "product_view_total": data.get("pageViewTotal"),
                    "purchase_total": data.get("purchaseTotal"),
                }]

                return {
                    "success": True,
                    "data": stats_data,
                    "message": "제품 통계 정보를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_id_str})의 통계 정보가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"제품 통계 정보 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }
        
async def get_product_other_color(product_id: str | int) -> Dict[str, Any]:
    """
    주어진 제품과 동일한 스타일의 다른 색상 제품 목록을 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "product_id": 3522389,
                "goods_name": "스웨트셔츠 [헤더 베이지]",
                "image_url": "https://image.msscdn.net/images/goods_img/..._500.jpg",
                "is_sold_out": false
            },
            {
                "product_id": 2678375,
                "goods_name": "스웨트셔츠 [그레이]",
                "image_url": "https://image.msscdn.net/images/goods_img/..._500.jpg",
                "is_sold_out": false
            }
        ],
        "message": "다른 색상 제품 정보를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "제품(ID: 12345)의 다른 색상 제품 정보가 없습니다.",
        "error_details": {
            "product_id": 12345,
            "error_type": "NO_DATA"
        }
    }
    """
    product_id_str = str(product_id)
    error_context = {"product_id": product_id_str}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://goods-detail.musinsa.com/api2/goods/{product_id_str}/curation/other-color",
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            other_color_products = []
            # API 응답 구조에 따라 안전하게 데이터에 접근합니다.
            if raw_data.get("data", {}).get("curationTabs"):
                for tab in raw_data["data"]["curationTabs"]:
                    if tab.get("curationType") == "OTHER_COLOR":
                        for item in tab.get("curationGoodsList", []):
                            other_color_products.append({
                                "product_id": item.get("goodsNo"),
                                "goods_name": item.get("goodsName"),
                                "image_url": item.get("imageUrl"),
                                "is_sold_out": item.get("isSoldOut")
                            })
                        break # 다른 색상 탭을 찾았으므로 루프 종료

            if other_color_products:
                return {
                    "success": True,
                    "data": other_color_products, # 데이터 필드에 리스트를 직접 할당
                    "message": "다른 색상 제품 정보를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"제품(ID: {product_id_str})의 다른 색상 제품 정보가 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"다른 색상 제품 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }
        
async def get_product_brand_and_price(product_id: str | int) -> Dict[str, Any]:
    """
    제품의 브랜드 정보와 가격 정보(정가, 할인가, 할인율)를 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {
                "brand_info": {
                    "brand_name": "마크엠",
                    "brand_english_name": "markm"
                },
                "price_info": {
                    "sale_price": 9990,
                    "original_price": 89000,
                    "discount_rate": 89,
                    "is_on_sale": true
                }
            }
        ],
        "message": "제품의 브랜드 및 가격 정보를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "웹 페이지에서 제품 정보를 추출하는데 실패했습니다.",
        "error_details": {
            "product_id": 12345,
            "error_type": "REGEX_MATCH_FAILED"
        }
    }
    """
    product_id_str = str(product_id)
    error_context = {"product_id": product_id_str}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://www.musinsa.com/products/{product_id_str}",
                headers={"User-Agent": user_agent, "accept": "text/html"},
                timeout=15.0 # HTML 파싱은 더 오래 걸릴 수 있으므로 타임아웃을 늘립니다.
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            script_tag = soup.select_one("#pdp-data")
            if not script_tag or not script_tag.string:
                 raise ValueError("Could not find product data script tag.")

            match = re.search(r'window\.__MSS__\.product\.state\s*=\s*(\{.*?\});', script_tag.string, re.DOTALL)
            if match:
                product_state_str = match.group(1)
                try:
                    product_state_dict = json.loads(product_state_str)
                    
                    # 키 이름 명확화 및 데이터 구조화
                    result_data = [{
                        "brand_info": {
                            "brand_name": product_state_dict["brandInfo"]["brandName"],
                            "brand_english_name": product_state_dict["brandInfo"]["brandEnglishName"].lower(),
                        },
                        "price_info": {
                            "sale_price": product_state_dict["goodsPrice"]["salePrice"],
                            "original_price": product_state_dict["goodsPrice"]["normalPrice"],
                            "discount_rate": product_state_dict["goodsPrice"]["discountRate"],
                            "is_on_sale": product_state_dict["goodsPrice"]["isSale"],
                        }
                    }]
                    return {
                        "success": True,
                        "data": result_data,
                        "message": "제품의 브랜드 및 가격 정보를 성공적으로 조회했습니다."
                    }
                except json.JSONDecodeError:
                    # JSON 파싱 실패 시 표준 형식으로 반환
                    return {
                        "success": False, "data": [],
                        "message": "웹 페이지 내 데이터의 JSON 형식이 올바르지 않습니다.",
                        "error_details": {**error_context, "error_type": ErrorType.JSON_PARSING_FAILED}
                    }
            else:
                # 정규식 매칭 실패 시 표준 형식으로 반환
                return {
                    "success": False, "data": [],
                    "message": "웹 페이지에서 제품 정보를 추출하는데 실패했습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.REGEX_MATCH_FAILED}
                }
        except Exception as e:
            # 그 외 모든 예외에 대해 표준 형식으로 반환
            return {
                "success": False, "data": [],
                "message": f"제품 정보 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }
        
async def get_brand_likes_count(brand_name: Union[str, List[str]]) -> Dict[str, Any]:
    """
    하나 또는 여러 브랜드의 '좋아요' 수를 조회합니다. (브랜드 이름은 소문자로 검색)

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {"brand_name": "markm", "count": 12345},
            {"brand_name": "covernat", "count": 54321}
        ],
        "message": "브랜드의 '좋아요' 수를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "브랜드(이름: ['markm'])의 '좋아요' 정보를 찾을 수 없습니다.",
        "error_details": {
            "brand_names": ["markm"],
            "error_type": "NO_DATA"
        }
    }
    """
    brand_names = [brand_name.lower()] if isinstance(brand_name, str) else [name.lower() for name in brand_name]
    error_context = {"brand_names": brand_names}

    async with httpx.AsyncClient() as client:
        try:
            payload = {"relationIds": brand_names}
            response = await client.post(
                url="https://like.musinsa.com/like/api/v2/liketypes/brand/counts",
                json=payload,
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("data", {}).get("success", False):
                items = raw_data.get("data", {}).get("contents", {}).get("items", [])
                
                like_counts = [
                    {
                        "brand_name": item.get("relationId"),
                        "count": item.get("count")
                    } for item in items
                ]
                
                return {
                    "success": True, # 불리언 타입으로 수정
                    "data": like_counts,
                    "message": "브랜드의 '좋아요' 수를 성공적으로 조회했습니다."
                }
            else:
                return {
                    "success": False,
                    "data": [],
                    "message": f"브랜드(이름: {brand_names})의 '좋아요' 정보를 찾을 수 없습니다.",
                    "error_details": {**error_context, "error_type": ErrorType.NO_DATA, "reason": raw_data.get("error", {}).get("message")}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"브랜드 '좋아요' 수 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": {**error_context, "error_type": ErrorType.API_ERROR}
            }
        
async def get_color_code() -> Dict[str, Any]:
    """
    무신사에서 사용하는 모든 색상의 이름과 고유 ID를 조회합니다.

    [성공 시 반환 형식]
    {
        "success": true,
        "data": [
            {"color_id": 1, "color_name": "블랙"},
            {"color_id": 2, "color_name": "화이트"},
            {"color_id": 3, "color_name": "그레이"}
        ],
        "message": "색상 코드 정보를 성공적으로 조회했습니다."
    }

    [실패 시 반환 형식]
    {
        "success": false,
        "data": [],
        "message": "색상 코드 조회 중 오류가 발생했습니다: ...",
        "error_details": {
            "error_type": "API_REQUEST_FAILED"
        }
    }
    """
    error_context = {"error_type": ErrorType.API_ERROR}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://goods-detail.musinsa.com/api2/goods/color-images",
                headers={"User-Agent": user_agent, "accept": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            raw_data = response.json()

            if raw_data.get("meta", {}).get("result") == "SUCCESS":
                color_list = sorted([
                    {
                        "color_id": color.get("colorId"),
                        "color_name": color.get("colorName"),
                    } for color in raw_data.get("data", {}).get("colorImages", [])
                ], key=lambda x: int(x["color_id"]))

                return {
                    "success": True,
                    "data": color_list,
                    "message": "색상 코드 정보를 성공적으로 조회했습니다."
                }
            else:
                # API는 성공했으나 데이터가 없는 경우도 실패로 처리
                return {
                    "success": False,
                    "data": [],
                    "message": "API에서 색상 코드 데이터를 반환하지 않았습니다.",
                    "error_details": {"error_type": "NO_DATA"}
                }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"색상 코드 조회 중 오류가 발생했습니다: {str(e)}",
                "error_details": error_context
            }
        
async def main():

    product_id = "3522389"
    # pprint.pprint(await get_product_selection_info(product_id=product_id))
    # result = await is_sale_and_detail_filter_info(product_id=product_id)
    # pprint.pprint(await get_product_size(product_id=product_id))
    # pprint.pprint(await get_review_info(product_id=product_id))

    # pprint.pprint(await get_review_list(product_id=product_id))
    pprint.pprint(await get_review_list(product_id=product_id))
    # result = await get_review_count(product_id=product_id , option_list=["S"] , sex="M")
    # result =await get_review_list(product_id=product_id , page=0 , page_size=50 )
    # result = await get_product_good_count(product_id=[product_id , 4637965])
    # result = await get_product_stats(product_id=product_id)
    
    # pprint.pprint(await get_brand_likes_count(brand_name="MARKM"))

    # pprint.pprint(await get_product_size(product_id=product_id))
    # pprint.pprint(await get_size_recommend(product_id=product_id , height=170 , weight=60))
    
    
    
    
    
    

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())