"""Base Redis configuration shared across services."""

from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseRedisSettings(BaseSettings):
    """Base Redis connection settings shared across all Redis-based services."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        env_prefix='REDIS_',
        extra='ignore',
    )

    # Common Redis connection settings
    HOST: Annotated[str, 'Redis server host'] = Field(default='localhost')
    PORT: Annotated[int, 'Redis server port'] = Field(default=6379)
    PASSWORD: Annotated[str | None, 'Redis password'] = Field(default=None)
    MAX_CONNECTIONS: Annotated[int, 'Maximum number of connections in pool'] = Field(default=10)
