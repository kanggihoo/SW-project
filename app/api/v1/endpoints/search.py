from fastapi import APIRouter, Body, HTTPException
from typing import Annotated
from app.config.dependencies import SearchServiceDep
from app.model.saarch_api import SearchRequest, SearchResponse, SearchResultItem

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

@router.post("/", response_model=SearchResponse)
async def search_product(
    search_service: SearchServiceDep,
    request: Annotated[SearchRequest, Body()]
):
    """
    사용자 쿼리를 기반으로 상품을 검색합니다.
    - 쿼리 분석 (향후 확장)
    - 임베딩 생성
    - 벡터 검색 수행
    - 결과 반환
    """
    try:
        query = request.messages
        # SearchService를 통해 비동기적으로 검색 수행
        search_result = await search_service.search_by_query(query, limit=10) # limit은 예시
        
        # 결과를 API 응답 모델에 맞게 변환
        response_data = SearchResultItem(
            query=search_result["query"],
            data=search_result["data"],
            total_count=search_result["total_count"],
            message=search_result["message"]
        )
        return SearchResponse(success=True, data=response_data)

    except HTTPException as e:
        # 서비스에서 발생한 HTTPException을 그대로 전달
        raise e
    except Exception as e:
        # 그 외 예상치 못한 예외 처리
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")

