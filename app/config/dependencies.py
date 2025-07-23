# 메인 의존성 정의 
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

# 필요 모듈 import 
from .settings import get_settings , Settings
from db import create_fashion_repo
from db.repository.fashion import FashionRepository
from aws.aws_manager import AWSManager
from aws.s3 import S3Manager
from aws.dynamodb import DynamoDBManager

from app.services.search import SearchService

# =============================================================================
# DB 관련 의존성 
# =============================================================================
@lru_cache()
def get_cached_settings() -> Settings:
    """캐쉬된 설정 반환"""
    return get_settings()

@lru_cache()
def get_fashion_repo()->FashionRepository:
    """캐쉬된 설정 반환"""
    settings = get_cached_settings()    
    return create_fashion_repo(settings.USE_ATLAS)

def get_fashion_repo_dependency() -> FashionRepository:
    """FashionRepository 의존성 반환"""
    return get_fashion_repo()

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
# 서비스 관련 의존성 
# =============================================================================
@lru_cache()
def get_search_service_dependency()->SearchService:
    s3_manager = get_s3_manager_dependency()
    repository = get_fashion_repo_dependency()
    return SearchService(s3_manager , repository)

# =============================================================================
# 의존성 타입 어노테이션 정의
# =============================================================================

# DB 관련
RepositoryDep = Annotated[FashionRepository , Depends(get_fashion_repo_dependency)]

# AWS 관련
AWSManagerDep = Annotated[AWSManager , Depends(get_aws_manager_dependency)]
S3ManagerDep = Annotated[S3Manager , Depends(get_s3_manager_dependency)]
DynamoDBManagerDep = Annotated[DynamoDBManager , Depends(get_dynamodb_manager_dependency)]

# 서비스 관련
SearchServiceDep = Annotated[SearchService , Depends(get_search_service_dependency)]