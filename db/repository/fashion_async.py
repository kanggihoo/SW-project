from .base_async import BaseAsyncRepository
from typing import Dict, Any, Optional, List, AsyncIterator
from pymongo.errors import DuplicateKeyError
import logging
from typing_extensions import override

logger = logging.getLogger(__name__)

class AsyncFashionRepository(BaseAsyncRepository):
    """패션 상품 전용 비동기 Repository"""

    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        super().__init__(connection_string, database_name, collection_name)

    @override
    async def find_by_id(self, doc_id: str) -> Optional[Dict]:
        """상품 ID로 비동기 조회"""
        try:
            return await self.collection.find_one({"_id": doc_id})
        except Exception as e:
            logger.error(f"Error finding product by ID (async) {doc_id}: {e}")
            return None

    @override
    async def find_all(self, filter_dict: Optional[Dict] = None) -> AsyncIterator[Dict]:
        """조건에 맞는 모든 상품 비동기 조회"""
        filter_dict = filter_dict or {}
        return self.collection.find(filter_dict)

    @override
    async def create(self, document: Dict) -> Optional[str]:
        """상품 비동기 생성"""
        try:
            result = await self.collection.insert_one(document)
            return str(result.inserted_id) if result.inserted_id else None
        except DuplicateKeyError:
            logger.warning(f"Duplicate product ID (async): {document.get('_id', 'Unknown')}")
            return None
        except Exception as e:
            logger.error(f"Error creating product (async): {e}")
            return None

    @override
    async def update_by_id(self, doc_id: str, update_data: Dict) -> bool:
        """상품 비동기 업데이트"""
        try:
            if not update_data:
                return False
            result = await self.collection.update_one(
                {"_id": doc_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating product (async) {doc_id}: {e}")
            return False

    @override
    async def delete_by_id(self, doc_id: str) -> bool:
        """상품 비동기 삭제"""
        try:
            result = await self.collection.delete_one({"_id": doc_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting product (async) {doc_id}: {e}")
            return False

    @override
    async def find(self, query: dict) -> AsyncIterator[Dict]:
        """쿼리에 맞는 문서 비동기 조회"""
        return await self.collection.find(query)

    async def vector_search(self, embedding: list[float], limit: int, pre_filter: Optional[Dict] = None) -> List[Dict]:
        """비동기 벡터 검색"""
        pipeline = self.query_builder.vector_search_pipeline(
            embedding=embedding,
            limit=limit,
            pre_filter=pre_filter
        )
        try:
            cursor = await self.collection.aggregate(pipeline)
            return [doc async for doc in cursor]
        except Exception as e:
            logger.error(f"Error during vector search (async): {e}")
            raise e
