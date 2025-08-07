# 메인 의존성 정의 
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

# 필요 모듈 import 
from .settings import get_settings
from db import create_fashion_repo
from db.repository.fashion import FashionRepository
from aws.aws_manager import AWSManager
from aws.s3 import S3Manager
from aws.dynamodb import DynamoDBManager
from app.services.search import SearchService

import logging 
logger = logging.getLogger(__name__)
# =============================================================================
# DB 관련 의존성 
# =============================================================================
@lru_cache()
def get_fashion_repo()->FashionRepository:
    """캐쉬된 설정 반환"""
    settings = get_settings()    
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


# =============================================================================
# 헬스체크 및 정리 함수들
# =============================================================================
def cleanup_dependencies():
    """애플리케이션 종료 시 리소스 정리"""
    try:
        # 캐시된 리소스들 정리
        if get_fashion_repo.cache_info().currsize > 0:
            repo = get_fashion_repo()
            repo.close_connection()
            get_fashion_repo.cache_clear()
            
        if get_aws_manager.cache_info().currsize > 0:
            aws_manager = get_aws_manager()
            aws_manager.close_connection()
            get_aws_manager.cache_clear()
            
        logger.info("Dependencies cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during dependency cleanup: {e}")

def health_check_dependencies() -> dict:
    """api 서버가 사용하는 모든 의존성에 대한 health check"""
    health_status = {
        "database": False,
        "aws": False,
        "overall": False # 전체 헬스 상태
    }

    try:
        # 데이터베이스 연결 확인
        repo = get_fashion_repo() # 캐시된 FashionRepository 인스턴스 가져오기
        health_status["database"] = repo.is_connected() # Repository의 연결 상태 확인 메서드 호출

        # AWS 연결 확인 (S3 기준)
        s3_manager = get_s3_manager_dependency() # S3Manager 인스턴스 가져오기
        # AWS 연결 상태는 실제 요청 시 확인되므로 여기서는 객체 존재 여부만 확인 (개선 필요)
        health_status["aws"] = s3_manager is not None

        health_status["overall"] = health_status["database"] and health_status["aws"]

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["error"] = str(e) # 오류 발생 시 오류 메시지 추가

    return health_status