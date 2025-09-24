# 메인 의존성 정의 
from functools import lru_cache
from typing import Annotated , AsyncGenerator
from fastapi import Depends , Request , Path , HTTPException
import logging 
import httpx

# 필요 모듈 import 
from .settings import get_settings
from db import get_async_fashion_repo , get_async_fashion_sku_repo
from db.repository.fashion_async import AsyncFashionRepository
from aws.aws_manager import AWSManager
from aws.s3 import S3Manager
from aws.dynamodb import DynamoDBManager
from app.services.search import SearchService
from embedding.embedding import JinaEmbedding
from query_analyzer.multi_step_analyzer import MultiStepAnalyzer
from query_analyzer.single_step_analyzer import SingleStepAnalyzer
from embedding.other_api import GeminiEmbedding
from langgraph.graph.state import CompiledStateGraph
# from graph.agents import get_all_agent_info , get_agents_openapi_examples
from psycopg import AsyncConnection

logger = logging.getLogger(__name__)
# =============================================================================
# DB 관련 의존성 mongo db(비동기)
# =============================================================================

def get_async_repo_provider(is_sku: bool = False) -> AsyncFashionRepository:
    if is_sku:
        return get_async_fashion_sku_repo()
    else:
        return get_async_fashion_repo()

async def get_async_fashion_repo_dependency(request: Request) -> AsyncFashionRepository:
    """AsyncFashionRepository 의존성 반환"""
    return request.app.state.db_repo

# =============================================================================
# DB 관련 의존성 postgres db(비동기)
# =============================================================================

# #TODO : 에러 처리 다 따로 빼고 
# async def get_db_connection(request: Request) -> AsyncGenerator[AsyncConnection, None]:
#     async with request.app.state.connection_pool.connection() as conn:
#         try:
#             yield conn
#         except Exception as e:
#             logger.error(f"Error getting db connection: {e}")
#             raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# AWS 관련 의존성 
# =============================================================================
def get_aws_manager()->AWSManager:
    """AWSManager 의존성 반환"""
    return AWSManager()

def get_s3_manager_dependency(request: Request)->S3Manager:
    """S3Manager 의존성 반환"""
    aws_manager = request.app.state.aws_manager
    return aws_manager.s3_manager

def get_dynamodb_manager_dependency(request: Request)->DynamoDBManager:
    """DynamoDBManager 의존성 반환"""
    aws_manager = request.app.state.aws_manager
    return aws_manager.dynamodb_manager

def get_aws_manager_dependency(request: Request)->AWSManager:
    """AWSManager 의존성 반환"""
    return request.app.state.aws_manager

# =============================================================================
# Jina Embedding 관련 의존성
# =============================================================================
# def get_jina_embedding(session: httpx.AsyncClient)->JinaEmbedding:
#     return JinaEmbedding(session=session)

# def get_jina_embedding_dependency(request: Request) -> JinaEmbedding:
#     """JinaEmbedding 의존성 반환""" 
#     return request.app.state.jina_embedding

# =============================================================================
# Query Analyzer 관련 의존성 
# =============================================================================
@lru_cache()
def get_query_analyzer_dependency() -> MultiStepAnalyzer:
    """QueryAnalyzer 의존성 반환"""
    # TODO: 모델명과 프로바이더는 나중에 설정(settings.py)에서 관리하는 것이 좋습니다.
    
    return SingleStepAnalyzer(
        model_provider="openrouter",
        model_name="google/gemini-2.5-flash-lite"
    )
    return MultiStepAnalyzer(
        model_provider1="openrouter",
        model_name1="google/gemini-2.5-flash-lite",
        model_provider2="openrouter",
        model_name2="google/gemini-2.5-flash-lite"
    )

# =============================================================================
# Musinsa API Wrapper 관련 의존성
# =============================================================================
from app.services.musinsa import MusinsaAPIWrapper

def get_musinsa_api_wrapper(request: Request) -> MusinsaAPIWrapper:
    """MusinsaAPIWrapper 의존성 반환. app.state에 저장된 싱글톤 인스턴스를 사용합니다."""
    return request.app.state.musinsa_api_wrapper

# =============================================================================
# 서비스 관련 의존성 (비동기)
# =============================================================================
async def get_search_service_dependency(
        
    s3_manager: Annotated[S3Manager, Depends(get_s3_manager_dependency)],
    repository: Annotated[AsyncFashionRepository, Depends(get_async_fashion_repo_dependency)],
    query_analyzer: Annotated[MultiStepAnalyzer, Depends(get_query_analyzer_dependency)]
) -> SearchService:
    """SearchService 의존성 반환 (비동기)"""
    return SearchService(s3_manager, repository, query_analyzer)

# =============================================================================
# langgraph 관련 의존성 
# =============================================================================
# def get_agent(request: Request , agent_name:Annotated[str, Path(...,description=f"사용할 에이전트 이름 \n 에이전트 목록 : {get_all_agent_info()}" , openapi_examples=get_agents_openapi_examples())] ) -> CompiledStateGraph:
#     if agent_name not in request.app.state.agents:
#         raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
#     return request.app.state.agents[agent_name]

# def get_agents(request: Request) -> dict[str, CompiledStateGraph]:
#     return request.app.state.agents


# =============================================================================
# 의존성 타입 어노테이션 정의
# =============================================================================

# DB 관련
RepositoryDep = Annotated[AsyncFashionRepository, Depends(get_async_fashion_repo_dependency)]
# DBConnectionDep = Annotated[AsyncConnection, Depends(get_db_connection)]

# AWS 관련
AWSManagerDep = Annotated[AWSManager, Depends(get_aws_manager_dependency)]
S3ManagerDep = Annotated[S3Manager, Depends(get_s3_manager_dependency)]
DynamoDBManagerDep = Annotated[DynamoDBManager, Depends(get_dynamodb_manager_dependency)]

# Query Analyzer 관련
QueryAnalyzerDep = Annotated[MultiStepAnalyzer, Depends(get_query_analyzer_dependency)]

# 서비스 관련
SearchServiceDep = Annotated[SearchService, Depends(get_search_service_dependency)]
MusinsaAPIWrapperDep = Annotated[MusinsaAPIWrapper, Depends(get_musinsa_api_wrapper)]

# agent 관련 
# AgentDep = Annotated[CompiledStateGraph, Depends(get_agent)]
# =============================================================================
# 헬스체크 및 정리 함수들 (수정 필요)
# =============================================================================
# TODO: 아래 함수들은 동기 방식으로 작성되어 비동기 리소스를 직접 다룰 수 없습니다.
# 애플리케이션의 lifespan 관리자(app/main.py)에서 리소스 정리 및 헬스체크를 수행하는 것이 좋습니다.
# def cleanup_dependencies():
#     """애플리케이션 종료 시 리소스 정리"""
#     pass

# async def health_check_dependencies() -> dict:
#     """api 서버가 사용하는 모든 의존성에 대한 health check"""
#     pass
