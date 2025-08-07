from pydantic import BaseModel , Field
from typing import Annotated


#===================================================================
# /search 요청에 대한 request 모델
#===================================================================
class SearchRequest(BaseModel):
    messages : str = Field(..., description="검색 쿼리")
    limit : int = Field(default=1, description="검색 결과 개수")



#===================================================================
# /search 요청에 대한 response 모델
#===================================================================
class BaseResponse(BaseModel):
    success : Annotated[bool , Field(default=True)]
    message : Annotated[str , Field(default="Success")]

class SearchResultItem(BaseModel):
    query : str
    data : list[dict]
    total_count : int
    message : str

class SearchResponse(BaseResponse):
    """검색 결과 응답 모델"""
    data : SearchResultItem