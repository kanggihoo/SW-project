"""ARQ task queue client for enqueueing jobs."""

from datetime import datetime, timedelta
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis
from arq.jobs import Job
from loguru import logger

from .config import QueueNames, taskqueue_settings


class TaskQueueClient:
    """Async client for enqueueing tasks to ARQ workers."""

    def __init__(self, settings=None):
        """Initialize task queue client.

        Args:
            settings: Optional TaskQueueSettings instance. Uses global settings if None.
        """
        self._settings = settings or taskqueue_settings
        self._pool: ArqRedis | None = None

    async def connect(self) -> None:
        """Create ARQ Redis connection pool."""
        if self._pool is not None:
            logger.warning('Task queue client is already connected')
            return

        try:
            self._pool = await create_pool(self._settings.get_redis_settings())
            logger.info(f'Task queue client connected to {self._settings.HOST}:{self._settings.PORT}')
        except Exception as e:
            logger.error(f'Failed to connect task queue client: {e}')
            raise

    async def close(self) -> None:
        """Close ARQ Redis connection pool."""
        if self._pool:
            await self._pool.aclose()
            self._pool = None
            logger.info('Task queue client disconnected')

    # TODO : retry 정책 ?? , 직렬화 관련해서 , job_id 관련 , default_queue_name 관련
    async def enqueue_task(
        self,
        function_name: str,
        *args: Any,
        queue: str = QueueNames.DEFAULT,
        job_id: str | None = None,
        defer_by: timedelta | None = None,
        defer_until: datetime | None = None,
        **kwargs: Any,
    ) -> Job | None:
        """Enqueue a task to the worker queue.

        Args:
            function_name: Name of the task function to execute
            *args: Positional arguments for the task function
            queue: Queue name (default or high_priority)
            job_id: Optional custom job ID
            defer_by: Optional delay before job execution
            defer_until: Optional datetime to start job execution
            **kwargs: Keyword arguments for the task function

        Returns:
            Job instance or None if enqueue failed
        """
        if not self._pool:
            raise RuntimeError('Task queue client not connected. Call connect() first.')

        try:
            job = await self._pool.enqueue_job(
                function_name,
                *args,
                _job_id=job_id,
                _queue_name=queue,
                _defer_until=defer_until,
                _defer_by=defer_by,
                **kwargs,
            )
            logger.info(f'Enqueued task: {function_name} (job_id={job.job_id}, queue={queue})')
            return job
        except Exception as e:
            logger.error(f'Failed to enqueue task {function_name}: {e}')
            return None

    # async def enqueue_delayed(
    #     self,
    #     function_name: str,
    #     delay_seconds: int,
    #     *args: Any,
    #     queue: str = QueueNames.DEFAULT,
    #     **kwargs: Any,
    # ) -> Job | None:
    #     """Enqueue a task with delay.

    #     Args:
    #         function_name: Name of the task function to execute
    #         delay_seconds: Delay in seconds before execution
    #         *args: Positional arguments for the task function
    #         queue: Queue name
    #         **kwargs: Keyword arguments for the task function

    #     Returns:
    #         Job instance or None if enqueue failed
    #     """
    #     defer_by = timedelta(seconds=delay_seconds)
    #     return await self.enqueue_task(function_name, *args, queue=queue, defer_by=defer_by, **kwargs)

    # async def enqueue_at(
    #     self,
    #     function_name: str,
    #     execute_at: datetime,
    #     *args: Any,
    #     queue: str = QueueNames.DEFAULT,
    #     **kwargs: Any,
    # ) -> Job | None:
    #     """Enqueue a task to execute at specific datetime.

    #     Args:
    #         function_name: Name of the task function to execute
    #         execute_at: Datetime when to execute the task
    #         *args: Positional arguments for the task function
    #         queue: Queue name
    #         **kwargs: Keyword arguments for the task function

    #     Returns:
    #         Job instance or None if enqueue failed
    #     """
    #     return await self.enqueue_task(function_name, *args, queue=queue, defer_until=execute_at, **kwargs)

    async def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get job status and result.

        Args:
            job_id: Job ID to check

        Returns:
            Job status dict or None if not found
        """
        if not self._pool:
            raise RuntimeError('Task queue client not connected. Call connect() first.')

        try:
            job = Job(job_id, self._pool)
            info = await job.info()

            if info is None:
                logger.debug(f'Job {job_id} not found')
                return None

            status = await job.status()
            result = await job.result(timeout=1)

            return {
                'job_id': job_id,
                'status': status.value if status else 'unknown',
                'result': result,
                'info': info,
            }
        except Exception as e:
            logger.error(f'Failed to get job status for {job_id}: {e}')
            return None

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if job was cancelled, False otherwise
        """
        if not self._pool:
            raise RuntimeError('Task queue client not connected. Call connect() first.')

        try:
            job = Job(job_id, self._pool)
            result = await job.abort()
            logger.info(f'Job {job_id} cancelled')
            return result
        except Exception as e:
            logger.error(f'Failed to cancel job {job_id}: {e}')
            return False

    async def get_queue_info(self, queue: str = QueueNames.DEFAULT) -> dict[str, int]:
        """Get queue statistics.

        Args:
            queue: Queue name

        Returns:
            Dict with queue statistics
        """
        if not self._pool:
            raise RuntimeError('Task queue client not connected. Call connect() first.')

        try:
            # Get queue length using Redis commands
            queue_key = f'arq:queue:{queue}'
            queue_length = await self._pool.llen(queue_key)

            return {
                'queue': queue,
                'pending_jobs': queue_length,
            }
        except Exception as e:
            logger.error(f'Failed to get queue info for {queue}: {e}')
            return {'queue': queue, 'pending_jobs': -1}

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


# async def get_task_queue_client() -> TaskQueueClient:
#     """FastAPI dependency for task queue client.

#     Usage in FastAPI:
#         @app.post('/tasks')
#         async def create_task(
#             client: TaskQueueClient = Depends(get_task_queue_client)
#         ):
#             job = await client.enqueue_task('example_task', name='test')
#             return {'job_id': job.job_id}
#     """
#     client = TaskQueueClient()
#     await client.connect()
#     try:
#         yield client
#     finally:
#         await client.close()


# # Global client instance for convenience (use with caution in production)
# _global_client: TaskQueueClient | None = None


# async def get_global_client() -> TaskQueueClient:
#     """Get or create global task queue client instance.

#     Note: This is convenient for simple use cases but not recommended
#     for production. Use get_task_queue_client() dependency instead.
#     """
#     global _global_client
#     if _global_client is None:
#         _global_client = TaskQueueClient()
#         await _global_client.connect()
#     return _global_client
