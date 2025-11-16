from typing import Annotated

from pydantic import BaseModel, Field


# ===================================================================
# /search 요청에 대한 request 모델
# ===================================================================
class SearchRequest(BaseModel):
    messages: Annotated[
        str,
        Field(
            ...,
            description='검색 쿼리',
            examples=[
                '베이지 베이직 반팔 셔츠에 카키 와이드 슬랙스가 잘 어울려.셔츠 앞부분만 살짝 넣어서 캐주얼하면서도 세련된 분위기를 연출할 수 있어. 브라운 로퍼에 같은 톤의 가죽 벨트로 포인트를 주면 더 완성도 높은 데이트 룩이 될 거야. 셔츠 버튼 1-2개 풀어주고 소매는 자연스럽게 내려서 착용하면 딱 좋아.',
            ],
        ),
    ]
    limit: Annotated[int, Field(default=1, description='검색 결과 개수')]
    verbose: Annotated[bool, Field(default=False, description='임베딩 리스트 반환 여부')] = False


# ===================================================================
# /search 요청에 대한 response 모델
# ===================================================================
class BaseResponse(BaseModel):
    success: Annotated[bool, Field(default=True, description='검색 결과 성공 여부')]
    message: Annotated[str, Field(default='Vector Search Success', description='검색 결과 메시지')]


class SearchResultItem(BaseModel):
    query: Annotated[str, Field(..., description='사용자가 입력한 쿼리')]
    data: Annotated[list[dict], Field(..., description='검색 결과 데이터')]
    total_count: Annotated[int, Field(..., description='검색 결과 총 개수')]
    embeddings: Annotated[list[list[float]] | None, Field(..., description='임베딩 리스트')] = None
    pre_filter_list: Annotated[list[dict] | None, Field(..., description='필터 리스트')] = None


class SearchResponse(BaseResponse):
    """검색 결과 응답 모델"""

    data: SearchResultItem


class SearchOneProductResponse(BaseResponse):
    """하나의 상품 조회 결과 응답 모델"""

    data: Annotated[dict, Field(..., description='하나의 상품 조회 결과')]
