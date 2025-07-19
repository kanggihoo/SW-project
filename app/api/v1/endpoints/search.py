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
        #TODO: 지금 atlas에 저장된 데이터의 representative_image_s3_key 가 이상함.
        # response = repository.find_all({"sub_category":"1005"})
        # data = []
        # for item in response:
        #     url = s3_manager.generate_presigned_url(item["representative_image_s3_key"]) 
        #     item["representative_image_url"] = url
        #     data.append(item)
            # item["representative_image_url"] = url

        data = []
        s3_key = ["TOP/1002/1006161/segment/0_0.jpg" , "BOTTOM/3002/1014964/segment/0_0.jpg"]
        for key in s3_key:
            url = s3_manager.generate_presigned_url(key)
            data.append({"representative_image_url":url})

        return SearchResponse(data=data)
    except Exception as e:
        return SearchResponse(success=False, message=str(e))

