# 설정관리
from enum import StrEnum
from typing import Annotated

from pydantic import BeforeValidator, Field, SecretStr, TypeAdapter
from pydantic.networks import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


# import os
# from db.config.config import Config as DBConfig
# from aws.config import Config as AWSConfig
# 입력된 문자열이 유효한 HTTP URL 형식인지 검증하는 함수입니다.
def check_str_is_http(x: str) -> str:
    # Pydantic의 HttpUrl 타입을 사용하여 유효성을 검사하는 어댑터를 생성합니다.
    http_url_adapter = TypeAdapter(HttpUrl)
    # 입력값(x)의 유효성을 검사하고, 통과하면 문자열로 변환하여 반환합니다.
    return str(http_url_adapter.validate_python(x))


class DatabaseType(StrEnum):
    """Database type"""

    SQLITE = 'sqlite'
    POSTGRES = 'postgres'
    MONGO = 'mongo'


class MonitoringType(StrEnum):
    """Monitoring type"""

    LANGFUSE = 'langfuse'
    LANGSMITH = 'langsmith'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        # 환경변수를 우선적으로 사용
        env_prefix='',
        extra='ignore',
    )

    MODE: Annotated[str, 'Fastapi Server model로 reload 할때 사용'] = Field(default='')
    DATABASE_TYPE: DatabaseType = DatabaseType.POSTGRES
    USE_ATLAS: Annotated[bool, Field(default=True)]

    # monitoering type
    MONITORING_TYPE: MonitoringType = MonitoringType.LANGFUSE

    # Langsmith
    LANGSMITH_TRACING: Annotated[str, 'Langsmith tracing'] = Field(default='False')
    LANGSMITH_PROJECT: Annotated[str, 'Langsmith project'] = Field(default='langgraph-agent-test')
    LANGSMITH_ENDPOINT: str | None = None
    LANGSMITH_API_KEY: SecretStr | None = None

    # Langfuse
    LANGFUSE_TRACING: bool = False
    LANGFUSE_HOST: Annotated[str, BeforeValidator(check_str_is_http)] = 'https://cloud.langfuse.com'
    LANGFUSE_PUBLIC_KEY: SecretStr | None = None
    LANGFUSE_SECRET_KEY: SecretStr | None = None

    # ===============================================================================================================
    # 데이터베이스 설정(Connection String 정보 및 Connection Pool 설정)
    # ===============================================================================================================

    def is_dev(self) -> bool:
        """Check if the server is in development mode"""
        return self.MODE == 'dev'


settings = Settings()
