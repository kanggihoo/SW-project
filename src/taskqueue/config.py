"""ARQ task queue configuration and Redis settings."""

from typing import Annotated

from arq.connections import RedisSettings as ArqRedisSettings
from pydantic import Field

from config.redis_base import BaseRedisSettings


class TaskQueueSettings(BaseRedisSettings):
    """Task queue configuration with ARQ and Redis settings."""

    # Task queue specific Redis database
    DB: Annotated[int, 'Redis database number for task queue'] = Field(default=1)

    # Worker configuration
    MAX_JOBS: Annotated[int, 'Maximum number of concurrent jobs per worker'] = Field(default=10)
    JOB_TIMEOUT: Annotated[int, 'Job timeout in seconds'] = Field(default=300)
    KEEP_RESULT: Annotated[int, 'Keep job results in seconds'] = Field(default=3600)
    HEALTH_CHECK_INTERVAL: Annotated[int, 'Health check interval in seconds'] = Field(default=60)

    # Queue configuration
    DEFAULT_QUEUE: Annotated[str, 'Default queue name'] = Field(default='arq:taskqueue')
    HIGH_PRIORITY_QUEUE: Annotated[str, 'High priority queue name'] = Field(default='high_priority')

    # Retry policy
    MAX_TRIES: Annotated[int, 'Maximum number of retry attempts'] = Field(default=3)
    RETRY_DELAY: Annotated[int, 'Delay between retries in seconds'] = Field(default=60)

    # taskqueue result keep time
    KEEP_RESULT_TIME: Annotated[int, 'Keep taskqueue result in seconds'] = Field(default=int(60 * 10))  # 10 minutes

    # whether to show taskqueue log results (disabled when using unified logging)
    LOG_RESULTS: Annotated[bool, 'Whether to show taskqueue log results'] = Field(default=False)

    def get_redis_settings(self) -> ArqRedisSettings:
        """Create ARQ RedisSettings instance.

        Returns:
            ArqRedisSettings instance for ARQ worker
        """
        return ArqRedisSettings(
            host=self.HOST,
            port=self.PORT,
            password=self.PASSWORD,
            database=self.DB,
            max_connections=self.MAX_CONNECTIONS,
        )

    def get_redis_url(self) -> str:
        """Generate Redis connection URL for task queue.

        Returns:
            Redis URL string
        """
        password_part = f':{self.PASSWORD}@' if self.PASSWORD else ''
        return f'redis://{password_part}{self.HOST}:{self.PORT}/{self.DB}'


# Global settings instance
taskqueue_settings = TaskQueueSettings()


# Queue name constants
class QueueNames:
    """Task queue name constants."""

    DEFAULT = taskqueue_settings.DEFAULT_QUEUE
    HIGH_PRIORITY = taskqueue_settings.HIGH_PRIORITY_QUEUE
