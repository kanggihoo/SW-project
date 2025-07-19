from fastapi import APIRouter
from fastapi import Body
from typing import Annotated, List, Dict, Any
from pydantic import Field
from app.config.dependencies import RepositoryDep
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
    data : Annotated[Dict[str, Any] , Field(default_factory=dict)]
       
@router.post("/" , response_model=SearchResponse)
async def search_product(
    repository: RepositoryDep,
    request: Annotated[SearchRequest , Body()]
):
    try:
        response = repository.search_product(request.messages)
        return SearchResponse(data=response)
    except Exception as e:
        return SearchResponse(success=False, message=str(e))

