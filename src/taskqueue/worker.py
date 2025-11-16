"""ARQ worker configuration and task functions.

Run worker with:
    arq src.taskqueue.worker.WorkerSettings
"""

# Import asyncio at the top level for task functions
import logging
from typing import Any

from loguru import logger

from db import get_async_fashion_sku_repo
from db.repository.fashion_async import AsyncFashionRepository
from redis_cache.client import RedisCacheClient
from redis_cache.config import redis_settings
from taskqueue.config import taskqueue_settings

# TODO : 로커 초기화
# arq 로거 없애기??

# ============================================
# Logging Configuration
# ============================================


def setup_arq_logging():
    """Configure ARQ to use loguru for consistent logging.

    ARQ uses the standard logging module, so we redirect ARQ loggers
    to use loguru handlers for unified logging across the application.
    """
    # ARQ loggers that need to be redirected
    arq_loggers = [
        'arq.worker',  # Worker lifecycle and job execution logs
        'arq.job',  # Individual job logs
        'arq.cron',  # Cron job logs
        'arq',  # Root ARQ logger
    ]

    # Create a loguru handler for the standard logging module
    class LoguruHandler(logging.Handler):
        """Custom logging handler that forwards logs to loguru."""

        def emit(self, record):
            # Get the loguru logger
            loguru_logger = logger.bind(name=record.name)

            # Format the message
            message = self.format(record)

            # Map logging levels to loguru methods
            level_map = {
                logging.DEBUG: loguru_logger.debug,
                logging.INFO: loguru_logger.info,
                logging.WARNING: loguru_logger.warning,
                logging.ERROR: loguru_logger.error,
                logging.CRITICAL: loguru_logger.critical,
            }

            # Log the message using the appropriate loguru method
            log_method = level_map.get(record.levelno, loguru_logger.info)
            log_method(message)

    # Configure ARQ loggers to use loguru
    handler = LoguruHandler()
    formatter = logging.Formatter('[ARQ] %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    for logger_name in arq_loggers:
        arq_logger = logging.getLogger(logger_name)
        # Remove existing handlers to avoid duplicate logs
        for h in arq_logger.handlers[:]:
            arq_logger.removeHandler(h)
        # Add our loguru handler
        arq_logger.addHandler(handler)
        # Set level to INFO to match loguru default
        arq_logger.setLevel(logging.INFO)
        # Prevent propagation to root logger
        arq_logger.propagate = False


# ============================================
# Task Functions
# ============================================


# search_api 에서 사용되는 task
async def update_cache_and_db_task(
    ctx: dict[str, Any],
    cache_key: str,
    product_sku_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Update Redis cache and MongoDB with latest product information.

    This task is executed in the background after a successful Musinsa API call
    to update both cache and database with the latest price information.

    Args:
        ctx: ARQ context dictionary
        product_sku_id: Product SKU ID (format: {product_id}_{color})
        data: Complete product data to cache and update in DB

    Returns:
        Result dictionary with success status and messages
    """
    logger.info(f'[TaskQueue] Starting update_cache_and_db_task for product: {product_sku_id}')

    # Get Redis client from context
    redis_client: RedisCacheClient = ctx['redis_client']
    repository: AsyncFashionRepository = ctx['mongodb_repo']
    try:
        # Step 1: Update Redis cache
        cache_success = await redis_client.json_set(cache_key, data)

        if cache_success:
            logger.info(f'[TaskQueue] Successfully cached product {product_sku_id}')
        else:
            logger.warning(f'[TaskQueue] Failed to cache product {product_sku_id}')

        # Step 2: Update MongoDB with latest price information
        update_data = {
            'products.current_price': data.get('current_price'),
            'products.original_price': data.get('original_price'),
            'products.discount_rate': data.get('discount_rate'),
            'products.is_on_sale': data.get('is_on_sale'),
        }

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if update_data:
            matched, modified = await repository.update_by_id(product_sku_id, update_data, upsert=True)
            if matched == -1:
                # 기술적 오류 발생
                logger.error(f'[TaskQueue] Database error updating product {product_sku_id}: matched={matched}, modified={modified}')
                db_success = False
            elif matched > 0:
                # 문서가 존재하고 업데이트 시도됨
                if modified > 0:
                    logger.info(f'[TaskQueue] Successfully updated DB for product {product_sku_id} (modified {modified} fields)')
                else:
                    logger.info(f'[TaskQueue] DB update completed for product {product_sku_id} (no changes needed)')
                db_success = True
            else:
                # 문서를 찾을 수 없음
                logger.warning(f'[TaskQueue] Product {product_sku_id} not found in database')
                db_success = False
        else:
            logger.warning(f'[TaskQueue] No price data to update for product {product_sku_id}')
            db_success = False

        logger.info(f'[TaskQueue] Completed update_cache_and_db_task for product: {product_sku_id}')

        return {
            'status': 'success' if (cache_success and db_success) else 'partial_success',
            'product_sku_id': product_sku_id,
            'cache_updated': cache_success,
            'db_updated': db_success,
        }

    except Exception as e:
        logger.error(f'[TaskQueue] Error in update_cache_and_db_task for {product_sku_id}: {e}')
        return {
            'status': 'failed',
            'product_sku_id': product_sku_id,
            'error': str(e),
        }


# product_handlers.py 에서 사용되는 리뷰 요약 업데이트 task
async def update_review_summary_in_db_task(
    ctx: dict[str, Any],
    summary_data: dict[str, Any],
) -> dict[str, Any]:
    """Update or insert review summary in MongoDB.

    This task is executed in the background to upsert review summary data
    into the database after generating new summaries.

    Args:
        ctx: ARQ context dictionary
        summary_data: Review summary data to upsert (contains '_id' and other fields)

    Returns:
        Result dictionary with success status and details
    """
    doc_id = summary_data.get('_id')
    if not doc_id:
        logger.error('[TaskQueue] Missing _id in summary_data for update_review_summary_in_db_task')
        return {
            'status': 'failed',
            'error': 'Missing _id in summary_data',
        }

    logger.info(f'[TaskQueue] Starting update_review_summary_in_db_task for document: {doc_id}')

    # Get MongoDB repository from context
    repository: AsyncFashionRepository = ctx['mongodb_repo']

    try:
        # Prepare document data (exclude _id from the data to set)
        document_data = {k: v for k, v in summary_data.items() if k != '_id'}

        # Perform upsert operation using existing update_by_id method
        matched, modified = await repository.update_by_id(doc_id, document_data, upsert=True)

        if matched == -1:
            # 기술적 오류 발생
            logger.error(f'[TaskQueue] Database error upserting review summary document {doc_id}')
            return {
                'status': 'failed',
                'doc_id': doc_id,
                'error': 'Database error',
            }
        elif matched > 0 and modified > 0:
            logger.info(f'[TaskQueue] Successfully updated existing review summary document: {doc_id}')
            operation = 'updated'
        elif matched == 0 and modified == 0:
            # upsert로 새로 생성된 경우
            logger.info(f'[TaskQueue] Successfully inserted new review summary document: {doc_id}')
            operation = 'inserted'
        else:
            logger.warning(f'[TaskQueue] No changes made to review summary document: {doc_id}')
            operation = 'no_change'

        logger.info(f'[TaskQueue] Completed update_review_summary_in_db_task for document: {doc_id}')

        return {
            'status': 'success',
            'doc_id': doc_id,
            'operation': operation,
            'matched': matched,
            'modified': modified,
        }

    except Exception as e:
        logger.error(f'[TaskQueue] Error in update_review_summary_in_db_task for {doc_id}: {e}')
        return {
            'status': 'failed',
            'doc_id': doc_id,
            'error': str(e),
        }


# product_handlers.py 에서 사용되는 도구 호출 결과 캐시 업데이트 task (handle_get_product_details, handle_get_product_sizing_info)
async def update_tool_cache_task(
    ctx: dict[str, Any],
    cache_key: str,
    cache_value: dict | str,
) -> dict[str, Any]:
    """(신규) 핸들러 도구의 결과를 Redis 캐시에 저장하는 범용 태스크"""
    logger.info(f'[TaskQueue] Starting update_tool_cache_task for key: {cache_key}')
    redis_client: RedisCacheClient = ctx['redis_client']

    try:
        # json_set을 사용하여 구조화된 데이터 저장
        if isinstance(cache_value, (dict, list)):
            success = await redis_client.json_set(cache_key, cache_value)
        else:
            success = await redis_client.set(cache_key, cache_value)
        if success:
            logger.info(f'[TaskQueue] Successfully cached key: {cache_key}')
            return {'status': 'success', 'cache_key': cache_key}
        else:
            logger.warning(f'[TaskQueue] Failed to cache key: {cache_key}')
            return {'status': 'failed', 'cache_key': cache_key, 'error': 'cache failed'}
    except Exception as e:
        logger.error(f'[TaskQueue] Error in update_tool_cache_task for {cache_key}: {e}')
        return {'status': 'failed', 'cache_key': cache_key, 'error': str(e)}


# ============================================
# Worker Lifecycle Hooks
# ============================================


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook.

    Args:
        ctx: ARQ context dictionary
    """
    # Setup unified logging for ARQ
    setup_arq_logging()

    logger.info('ARQ worker starting up...')
    # Initialize resources (database connections, external clients, etc.)

    # Initialize Redis client for reuse across tasks
    redis_client = RedisCacheClient(redis_settings)
    await redis_client.connect()
    ctx['redis_client'] = redis_client

    # Initialize MongoDB repository for reuse across tasks
    mongodb_repo = await get_async_fashion_sku_repo()
    ctx['mongodb_repo'] = mongodb_repo

    logger.info('ARQ worker startup completed')


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook.

    Args:
        ctx: ARQ context dictionary
    """
    logger.info('ARQ worker shutting down...')
    # Cleanup resources

    # Close Redis connection
    if 'redis_client' in ctx:
        await ctx['redis_client'].close()
        logger.info('Redis connection closed')

    # Close MongoDB connection
    if 'mongodb_repo' in ctx:
        await ctx['mongodb_repo'].close()
        logger.info('MongoDB connection closed')

    logger.info('ARQ worker shutdown completed')


# ============================================
# Worker Settings
# ============================================


class WorkerSettings:
    """ARQ worker settings class.

    This class configures the ARQ worker with Redis connection,
    task functions, and worker behavior settings.
    """

    # Redis connection settings
    redis_settings = taskqueue_settings.get_redis_settings()

    # Queue configuration
    queue_name = taskqueue_settings.DEFAULT_QUEUE

    # Task functions that this worker can execute
    functions = [
        update_cache_and_db_task,
        update_review_summary_in_db_task,
        update_tool_cache_task,
    ]

    # Worker behavior settings
    max_jobs = taskqueue_settings.MAX_JOBS
    job_timeout = taskqueue_settings.JOB_TIMEOUT
    keep_result = taskqueue_settings.KEEP_RESULT
    health_check_interval = taskqueue_settings.HEALTH_CHECK_INTERVAL

    # Retry policy
    max_tries = taskqueue_settings.MAX_TRIES
    retry_jobs = True

    # taskqueue result keep time
    keep_result = taskqueue_settings.KEEP_RESULT_TIME
    # Disable ARQ's built-in logging since we use unified loguru logging
    log_results = False

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Cron jobs (periodic tasks)
    # cron_jobs = [
    #     cron(cleanup_old_data_task, hour={2}, minute={0}),  # Run daily at 2:00 AM
    # ]


# Alternative: High priority worker for urgent tasks
# class HighPriorityWorkerSettings(WorkerSettings):
#     """High priority worker for urgent tasks."""

#     queue_name = taskqueue_settings.HIGH_PRIORITY_QUEUE
#     max_jobs = 5  # Fewer concurrent jobs for better response time
#     job_timeout = 60  # Shorter timeout for urgent tasks
