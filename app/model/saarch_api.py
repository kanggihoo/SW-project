from pydantic import BaseModel , Field
from typing import Annotated


#===================================================================
# /search 요청에 대한 request 모델
#===================================================================
class SearchRequest(BaseModel):
    messages : Annotated[str , Field(..., description="검색 쿼리")]
    limit : Annotated[int , Field(default=1, description="검색 결과 개수")]



#===================================================================
# /search 요청에 대한 response 모델
#===================================================================
class BaseResponse(BaseModel):
    success : Annotated[bool , Field(default=True , description="검색 결과 성공 여부")]
    message : Annotated[str , Field(default="Vector Search Success" , description="검색 결과 메시지")]

class SearchResultItem(BaseModel):
    query : Annotated[str , Field(..., description="사용자가 입력한 쿼리")]
    data : Annotated[list[dict] , Field(..., description="검색 결과 데이터")]
    total_count : Annotated[int , Field(..., description="검색 결과 총 개수")]

class SearchResponse(BaseResponse):
    """검색 결과 응답 모델"""
    data : SearchResultItem