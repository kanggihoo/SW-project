from fastapi import APIRouter
from .endpoints import products, search

api_router = APIRouter(
    prefix="/api/v1",
    tags=["api/v1"],
)

api_router.include_router(products.router)
api_router.include_router(search.router)