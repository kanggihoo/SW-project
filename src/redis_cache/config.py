"""Redis cache configuration settings."""

from typing import Annotated

from pydantic import Field

from config.redis_base import BaseRedisSettings


class RedisCacheSettings(BaseRedisSettings):
    """Redis cache configuration with connection pool settings."""

    # Cache-specific Redis database
    DB: Annotated[int, 'Redis database number for cache'] = Field(default=0)
    SSL: Annotated[bool, 'Use SSL connection'] = Field(default=False)

    # Connection pool settings
    SOCKET_CONNECT_TIMEOUT: Annotated[int, 'Socket connection timeout in seconds'] = Field(default=5)
    SOCKET_TIMEOUT: Annotated[int, 'Socket read/write timeout in seconds'] = Field(default=5)

    # Cache behavior settings
    DEFAULT_TTL: Annotated[int, 'Default TTL in seconds'] = Field(default=int(60 * 60 * 24))  # 1 day
    KEY_PREFIX: Annotated[str, 'Prefix for all cache keys'] = Field(default='cache:')

    def get_redis_url(self) -> str:
        """Generate Redis connection URL."""
        protocol = 'rediss' if self.SSL else 'redis'
        password_part = f':{self.PASSWORD}@' if self.PASSWORD else ''
        return f'{protocol}://{password_part}{self.HOST}:{self.PORT}/{self.DB}'


# Global settings instance
redis_settings = RedisCacheSettings()
