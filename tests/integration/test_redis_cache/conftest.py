"""Cache integration tests configuration."""

import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from loguru import logger

from redis_cache import RedisCacheClient


@pytest.fixture(scope='session', autouse=True)
def setup_logging():
    """Setup loguru logging for cache integration tests."""
    # Remove default handler
    logger.remove()

    # Add handler for test output
    logger.add(
        sink=sys.stderr,
        level='INFO',
        format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> '
        '<level>{message}</level>',
        colorize=True,
    )


@pytest_asyncio.fixture(scope='function')
async def redis_client() -> AsyncGenerator[RedisCacheClient, None]:
    """Redis cache client fixture for integration tests.

    This fixture provides a connected RedisCacheClient instance
    for each test. The client is properly cleaned up after the test completes.

    Changed from session scope to function scope to avoid event loop conflicts.
    """
    client = RedisCacheClient()

    try:
        await client.connect()
        # Clear all existing cache data to ensure clean test state
        await client.clear_pattern('*')
        yield client
    finally:
        await client.close()
