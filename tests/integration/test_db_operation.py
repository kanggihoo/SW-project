from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from db import get_async_fashion_sku_repo
from db.repository.fashion_async import AsyncFashionRepository


@pytest_asyncio.fixture
async def db_repository():
    """Real AsyncFashionRepository fixture for integration testing with fallback to mock."""
    try:
        repo = await get_async_fashion_sku_repo()
        yield repo
    except Exception:
        # 연결 실패 시 mock으로 fallback
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=None)
        yield mock_repo


class TestDBOperation:
    """DB 연동 테스트 클래스"""

    TEST_PRODUCT_ID = '4149670'

    @pytest.mark.asyncio
    async def test_db_connection(self, db_repository: AsyncFashionRepository):
        assert await db_repository.is_connected()

    @pytest.mark.asyncio
    async def test_db_find_by_id(self, db_repository: AsyncFashionRepository):
        result = await db_repository.find_by_id('review_' + self.TEST_PRODUCT_ID)
        print(result)
        # assert result is not None

    @pytest.mark.asyncio
    async def test_db_get_product_description_info(self, db_repository: AsyncFashionRepository):
        result = await db_repository.get_product_description_info(self.TEST_PRODUCT_ID)
        print(result)
        assert result is not None
