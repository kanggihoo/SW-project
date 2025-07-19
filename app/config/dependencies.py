# 메인 의존성 정의 
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

# 필요 모듈 import 
from .settings import get_settings , Settings
from db import create_fashion_repo
from db.repository.fashion import FashionRepository
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

RepositoryDep = Annotated[FashionRepository , Depends(get_fashion_repo_dependency)]
