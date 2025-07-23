from fastapi import APIRouter
from fastapi import Body
from typing import Annotated, List, Dict, Any
from pydantic import Field
from app.config.dependencies import RepositoryDep, AWSManagerDep, DynamoDBManagerDep , S3ManagerDep , SearchServiceDep
from pydantic import BaseModel
router = APIRouter(
    prefix="/search",
    tags=["search"],
)

class SearchRequest(BaseModel):
    messages : str = Field(..., description="검색 쿼리")

class SearchResponse(BaseModel):
    success : Annotated[bool , Field(default=True)]
    message : Annotated[str , Field(default="Success")]
    data : Annotated[Dict[str, Any] , Field(default={})]
       
@router.post("/" , response_model=SearchResponse)
async def search_product(
    search_service:SearchServiceDep,
    request: Annotated[SearchRequest , Body()]
):
    try:
        #TODO: 지금 atlas에 저장된 데이터의 representative_image_s3_key 가 이상함.
        # response = repository.find_all({"sub_category":"1005"})
        # data = []
        # for item in response:
        #     url = s3_manager.generate_presigned_url(item["representative_image_s3_key"]) 
        #     item["representative_image_url"] = url
        #     data.append(item)
            # item["representative_image_url"] = url
        query = request.messages
        result = search_service.vector_search(query)
        print(result)
        return SearchResponse(data=result)
    except Exception as e:
        return SearchResponse(success=False, message=str(e))

