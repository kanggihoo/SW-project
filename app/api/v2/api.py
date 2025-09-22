from fastapi import APIRouter
from . import search

api_router = APIRouter(
    prefix="/api/v2",
)

api_router.include_router(search.router)