from fastapi import APIRouter
from fastapi import Body
from typing import Annotated, List, Dict, Any
from pydantic import Field
from app.config.dependencies import RepositoryDep, AWSManagerDep, DynamoDBManagerDep , S3ManagerDep
from pydantic import BaseModel
router = APIRouter(
    prefix="/search",
    tags=["search"],
)

class SearchRequest(BaseModel):
    messages : List[str]

class SearchResponse(BaseModel):
    success : Annotated[bool , Field(default=True)]
    message : Annotated[str , Field(default="Success")]
    data : Annotated[List[Dict[str, Any]] , Field(default_factory=list)]
       
@router.post("/" , response_model=SearchResponse)
async def search_product(
    repository: RepositoryDep,
    s3_manager: S3ManagerDep,
    request: Annotated[SearchRequest , Body()]
):
    try:
        response = repository.find_all({"sub_category":1005})
        for item in response:
            url = s3_manager.generate_presigned_url(item["representative_image_s3_key"]) 
            item["representative_image_url"] = url
        print(list(response))
        return SearchResponse(data=response)
    except Exception as e:
        return SearchResponse(success=False, message=str(e))

