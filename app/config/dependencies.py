# 메인 의존성 정의 
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

# 필요 모듈 import 
from .settings import get_settings
from db import get_async_fashion_repo
from db.repository.fashion_async import AsyncFashionRepository
from aws.aws_manager import AWSManager
from aws.s3 import S3Manager
from aws.dynamodb import DynamoDBManager
from app.services.search import SearchService
from embedding.embedding import JinaEmbedding
import logging 
logger = logging.getLogger(__name__)
# =============================================================================
# DB 관련 의존성 (비동기)
# =============================================================================
@lru_cache()
def get_async_repo_provider():
    # 이 함수는 실제 repo가 아닌, repo를 생성하는 비동기 함수를 반환합니다.
    # FastAPI는 Depends에서 이 비동기 함수를 호출하고 결과를 캐시합니다.
    return get_async_fashion_repo

async def get_async_fashion_repo_dependency() -> AsyncFashionRepository:
    """AsyncFashionRepository 의존성 반환"""
    repo_provider = get_async_repo_provider()
    return await repo_provider()

# =============================================================================
# AWS 관련 의존성 
# =============================================================================
@lru_cache()
def get_aws_manager()->AWSManager:
    """AWSManager 의존성 반환"""
    return AWSManager()

def get_s3_manager_dependency()->S3Manager:
    """S3Manager 의존성 반환"""
    aws_manager = get_aws_manager()
    return aws_manager.s3_manager

def get_dynamodb_manager_dependency()->DynamoDBManager:
    """DynamoDBManager 의존성 반환"""
    aws_manager = get_aws_manager()
    return aws_manager.dynamodb_manager

def get_aws_manager_dependency()->AWSManager:
    """AWSManager 의존성 반환"""
    return get_aws_manager()

# =============================================================================
# 서비스 관련 의존성 (비동기)
# =============================================================================
async def get_search_service_dependency(
    s3_manager: Annotated[S3Manager, Depends(get_s3_manager_dependency)],
    repository: Annotated[AsyncFashionRepository, Depends(get_async_fashion_repo_dependency)]
) -> SearchService:
    """SearchService 의존성 반환 (비동기)"""
    embedding = JinaEmbedding()
    return SearchService(s3_manager, repository, embedding)

# =============================================================================
# 의존성 타입 어노테이션 정의
# =============================================================================

# DB 관련
RepositoryDep = Annotated[AsyncFashionRepository, Depends(get_async_fashion_repo_dependency)]

# AWS 관련
AWSManagerDep = Annotated[AWSManager, Depends(get_aws_manager_dependency)]
S3ManagerDep = Annotated[S3Manager, Depends(get_s3_manager_dependency)]
DynamoDBManagerDep = Annotated[DynamoDBManager, Depends(get_dynamodb_manager_dependency)]

# 서비스 관련
SearchServiceDep = Annotated[SearchService, Depends(get_search_service_dependency)]


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