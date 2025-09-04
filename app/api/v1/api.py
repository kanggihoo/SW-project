from fastapi import APIRouter
from .endpoints import musinsa, search

api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(musinsa.router)
api_router.include_router(search.router)