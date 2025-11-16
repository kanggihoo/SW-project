from collections.abc import AsyncIterator
from typing import Any, override

from bson.binary import Binary, BinaryVectorDtype
from loguru import logger
from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from .base_async import BaseAsyncRepository


class AsyncFashionRepository(BaseAsyncRepository):
    """패션 상품 전용 비동기 Repository"""

    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        super().__init__(connection_string, database_name, collection_name)

    @override
    async def find_by_id(self, doc_id: str, projection: dict | None = None) -> dict:
        """상품 ID로 비동기 조회"""
        try:
            return await self.collection.find_one({'_id': doc_id}, projection=projection)
        except Exception as e:
            logger.error(f'Error finding product by ID (async) {doc_id}: {e}')
            raise Exception(f'Error finding product by ID (async) {doc_id}: {e}') from e

    @override
    async def find_all(self, filter_dict: dict | None = None) -> AsyncIterator[dict]:
        """조건에 맞는 모든 상품 비동기 조회"""
        filter_dict = filter_dict or {}
        return self.collection.find(filter_dict)

    @override
    async def create(self, document: dict) -> str | None:
        """상품 비동기 생성"""
        try:
            result = await self.collection.insert_one(document)
            return str(result.inserted_id) if result.inserted_id else None
        except DuplicateKeyError:
            logger.warning(f'Duplicate product ID (async): {document.get("_id", "Unknown")}')
            return None
        except Exception as e:
            logger.error(f'Error creating product (async): {e}')
            return None

    @override
    async def update_by_id(self, doc_id: str, update_data: dict, upsert: bool = False) -> tuple[int, int]:
        """
        업데이트를 시도하고 (matched_count, modified_count)를 반환합니다.
        오류 발생 시 (-1, -1)을 반환합니다.
        """
        if not update_data:
            # 업데이트 데이터가 없으면 매치/수정 모두 0
            return 0, 0

        try:
            result = await self.collection.update_one({'_id': doc_id}, {'$set': update_data}, upsert=upsert)
            return result.matched_count, result.modified_count

        except Exception as e:
            logger.error(f'Error updating doc {doc_id}: {e}')
            # 기술적 오류는 특수 값으로 표시
            return -1, -1

    @override
    async def delete_by_id(self, doc_id: str) -> bool:
        """상품 비동기 삭제"""
        try:
            result = await self.collection.delete_one({'_id': doc_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f'Error deleting product (async) {doc_id}: {e}')
            return False

    @override
    async def find(self, query: dict) -> AsyncIterator[dict]:
        """쿼리에 맞는 문서 비동기 조회"""
        return await self.collection.find(query)

    # ===========================================================================
    # 벡터 검색
    # ===========================================================================
    async def vector_search(
        self,
        embedding: list[float],
        limit: int,
        pre_filter: dict | None = None,
    ) -> list[dict]:
        """비동기 벡터 검색"""
        pipeline = self.query_builder.vector_search_pipeline(
            embedding=embedding,
            limit=limit,
            pre_filter=pre_filter,
        )
        try:
            # TODO : 벡터 서치 간에 대응하는 색상이 없는 경우 처리 필요
            # logger.info(f"pipeline: {pipeline}")
            cursor = await self.collection.aggregate(pipeline)
            # logger.info(f"cursor: {cursor}")
            return [doc async for doc in cursor]
        except Exception as e:
            logger.error(f'Error during vector search (async): {e}')
            raise e

    @staticmethod
    def _generate_bson_vector(vector: list[float], vector_dtype: Any) -> Binary:
        """벡터값을 BSON 형태로 변환"""
        # Generate BSON vector from the sample float32 embedding
        return Binary.from_vector(vector, vector_dtype)

    @staticmethod
    def _get_vector_dtype(dtype_str: str) -> Any:
        """문자열로부터 BinaryVectorDtype을 가져옵니다."""
        if dtype_str.lower() == 'float32':
            return BinaryVectorDtype.FLOAT32
        elif dtype_str.lower() == 'int8':
            return BinaryVectorDtype.INT8
        # 필요한 경우 다른 dtype에 대한 처리를 추가할 수 있습니다.
        else:
            raise ValueError(f'Unsupported vector dtype: {dtype_str}')

    async def add_bson_vector_field(self, vector_dtype_str: str, source_field: str, target_field: str, batch_size: int = 500) -> int:
        """
        모든 문서에 대해 지정된 필드의 벡터를 BSON으로 변환하여 새 필드에 추가합니다.
        BATCH_SIZE를 이용해 대량 쓰기 작업을 최적화합니다.

        Args:
            vector_dtype_str (str): 변환할 벡터의 타입 (예: 'float32').
            source_field (str): 소스 벡터 필드의 이름.
            target_field (str): BSON 벡터를 저장할 타겟 필드의 이름.
            batch_size (int): 한 번에 처리할 문서의 수.

        Returns:
            int: 업데이트된 문서의 수.
        """
        try:
            vector_dtype = self._get_vector_dtype(vector_dtype_str)
            updates = []
            total_modified_count = 0

            cursor = self.collection.find({source_field: {'$exists': True}})
            async for doc in cursor:
                vector = doc.get(source_field)
                if vector and isinstance(vector, list):
                    bson_vector = self._generate_bson_vector(vector, vector_dtype)
                    updates.append(UpdateOne({'_id': doc['_id']}, {'$set': {target_field: bson_vector}}))

                if len(updates) >= batch_size:
                    result = await self.collection.bulk_write(updates)
                    total_modified_count += result.modified_count
                    logger.info(f'Processed a batch of {len(updates)} documents. Modified {result.modified_count}.')
                    updates = []

            if updates:
                result = await self.collection.bulk_write(updates)
                total_modified_count += result.modified_count
                logger.info(f'Processed the final batch of {len(updates)} documents. Modified {result.modified_count}.')

            logger.info(f"Successfully updated {total_modified_count} documents in total with BSON vectors in field '{target_field}'.")
            return total_modified_count
        except ValueError as ve:
            logger.error(f'Invalid vector dtype specified: {ve}')
            raise
        except Exception as e:
            logger.error(f'Error adding BSON vector field: {e}')
            raise

    async def remove_field(self, field_name: str) -> int:
        """
        컬렉션의 모든 문서에서 특정 필드를 제거합니다.

        Args:
            field_name (str): 제거할 필드의 이름.

        Returns:
            int: 필드가 제거된 문서의 수.
        """
        try:
            result = await self.collection.update_many({field_name: {'$exists': True}}, {'$unset': {field_name: ''}})
            logger.info(f"Successfully removed field '{field_name}' from {result.modified_count} documents.")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error removing field '{field_name}': {e}")
            raise

    async def get_product_description_info(self, product_id: str) -> str | None:
        """
        products.product_id를 사용하여 해당 상품의 description_info를 비동기적으로 조회합니다.

        """
        try:
            # products.product_id로 문서를 찾고, products.description_info 필드만 프로젝션합니다.
            # find_one을 사용하여 하나의 문서만 가져옵니다.
            document = await self.collection.find_one(
                {'products.product_id': product_id},
                projection={'products.description_info': 1, '_id': 0},
            )
            if document and 'products' in document and 'description_info' in document['products']:
                return document['products']['description_info']
            return None
        except Exception as e:
            logger.error(f'Error getting description_info for product_id {product_id}: {e}')
            raise Exception(f'Error getting description_info for product_id {product_id}: {e}') from e
