from fastapi import APIRouter

from . import graph, mongodb, postgre, search

api_router = APIRouter()

# api_router.include_router(musinsa.router)
api_router.include_router(mongodb.router)
api_router.include_router(search.router)
api_router.include_router(postgre.router)
api_router.include_router(graph.router)

__all__ = ['api_router']
