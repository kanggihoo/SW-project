# 설정관리
from enum import StrEnum
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = 'development'  # 개발환경(실제 API 호출)
    PRODUCTION = 'production'  # 운영환경 (실제 API 호출)
    TESTING = 'test'  # 테스트 환경 (Mock API 호출 및 MOCK 그래프 노드 호출)


class FastAPIMode(StrEnum):
    DEVELOPMENT = 'dev'  # 개발환경(실제 API 호출)
    PRODUCTION = 'production'  # 운영환경 (실제 API 호출)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        # 환경변수를 우선적으로 사용
        env_prefix='',
        extra='ignore',
    )

    MODE: Annotated[FastAPIMode, 'Fastapi Server model로 reload 할때 사용'] = FastAPIMode.DEVELOPMENT
    ENV: Annotated[Environment, '실행 환경변수 : development, production, test'] = Field(default=Environment.PRODUCTION)
    USE_ATLAS: Annotated[bool, 'MongoDB Atlas 사용 여부'] = Field(default=True)

    # ===============================================================================================================
    # 데이터베이스 설정(Connection String 정보 및 Connection Pool 설정)
    # ===============================================================================================================

    def is_dev(self) -> bool:
        """Check if the server is in development mode"""
        return self.MODE == FastAPIMode.DEVELOPMENT

    def is_mock_use(self) -> bool:
        """Check if the server is in testing mode"""
        return self.ENV == Environment.TESTING


settings = Settings()
