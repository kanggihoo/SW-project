from pydantic import BaseModel, Field
from typing import Annotated


# ===================================================================
# /search 요청에 대한 request 모델
# ===================================================================
class SearchRequest(BaseModel):
    messages: Annotated[str, Field(..., description='검색 쿼리')]
    limit: Annotated[int, Field(default=1, description='검색 결과 개수')]
    return_image_url: Annotated[bool, Field(default=True, description='이미지 URL 반환 여부')]


# ===================================================================
# /search 요청에 대한 response 모델
# ===================================================================
class BaseResponse(BaseModel):
    success: Annotated[bool, Field(default=True, description='검색 결과 성공 여부')]
    message: Annotated[str, Field(default='Vector Search Success', description='검색 결과 메시지')]


class SearchResultItem(BaseModel):
    query: Annotated[str, Field(..., description='사용자가 입력한 쿼리')]
    rewritten_query_list: Annotated[list[str] | None, Field(description='재작성된 쿼리 리스트')] = None
    pre_filter_list: Annotated[list[dict] | None, Field(description='필터 리스트')] = None
    data: Annotated[list[dict], Field(..., description='검색 결과 데이터')]
    total_count: Annotated[int, Field(..., description='검색 결과 총 개수')]


class SearchResponse(BaseResponse):
    """검색 결과 응답 모델"""

    data: SearchResultItem


class SearchOneProductResponse(BaseResponse):
    """하나의 상품 조회 결과 응답 모델"""

    data: Annotated[dict, Field(..., description='하나의 상품 조회 결과')]
