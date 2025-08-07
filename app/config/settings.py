# 설정관리 
from functools import lru_cache
from pydantic_settings import BaseSettings , SettingsConfigDict
from pydantic import Field
from typing import Annotated
from db.config.config import Config as DBConfig
from aws.config import Config as AWSConfig
import os
class Settings(BaseSettings):
    USE_ATLAS: Annotated[bool, Field(default=True)]
    
    # 환경변수가 None일 경우를 대비한 검증 추가
    MONGODB_ATLAS_URI: Annotated[str, Field(
        description="MongoDB Atlas connection URI",
        min_length=1  # 빈 문자열 방지
    )]
    
    MONGODB_ATLAS_DATABASE: Annotated[str, Field(default="fashion_db")]
    MONGODB_ATLAS_COLLECTION: Annotated[str, Field(default="products")]
    
    # 다른 필수 환경변수들도 추가
    JINA_API_KEY: Annotated[str, Field(default=None)]
    OPENAI_API_KEY: Annotated[str, Field(default=None)]
    GOOGLE_API_KEY: Annotated[str, Field(default=None)]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        # 환경변수를 우선적으로 사용
        env_prefix="",
        extra="ignore"
    )
    
    # def __init__(self, **kwargs):
    #     # 환경변수 직접 확인 및 로그
    #     required_vars = ['MONGODB_ATLAS_URI']
    #     missing_vars = []
        
    #     for var in required_vars:
    #         env_value = os.environ.get(var)
    #         if not env_value:
    #             missing_vars.append(var)
    #         else:
    #             print(f"✓ {var}: {env_value[:20]}...")
        
    #     if missing_vars:
    #         print(f"❌ 누락된 환경변수: {', '.join(missing_vars)}")
    #         print("현재 환경변수 목록:")
    #         for key, value in os.environ.items():
    #             if any(x in key.upper() for x in ['MONGO', 'API', 'ATLAS']):
    #                 print(f"  {key}: {value[:20] if value else 'None'}...")
            
    #         # 환경변수가 누락된 경우 명확한 에러 메시지
    #         raise ValueError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        
    #     super().__init__(**kwargs)


@lru_cache
def get_settings():
    return Settings()