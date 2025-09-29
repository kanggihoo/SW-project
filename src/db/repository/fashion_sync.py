from .base_sync import BaseRepository
from typing import Dict, Any, Optional, List, override, Iterator
from pymongo.errors import DuplicateKeyError, BulkWriteError, WriteError
from pymongo.client_session import ClientSession
from pymongo.operations import InsertOne
import logging
from embedding import JinaEmbedding

logger = logging.getLogger(__name__)

"""
어떻게 데이터를 가지고 올 것인지에 대한 작성 

"""


class FashionRepository(BaseRepository):
    """패션 상품 전용 Repository"""

    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        """
        FashionRepository 초기화
        Args:
            connection_string (str): 데이터베이스 연결 문자열
            database_name (str): 데이터베이스 이름
            collection_name (str): 컬렉션 이름
        """
        super().__init__(connection_string, database_name, collection_name)

    # ============================================================================
    # 추상 메서드 구현 (BaseRepository에서 상속)
    # ============================================================================
    @override
    def find_by_id(self, doc_id: str) -> Optional[Dict]:
        """상품 ID로 조회"""
        try:
            product = self.collection.find_one({'_id': doc_id})
            return product
        except Exception as e:
            logger.error(f'Error finding product by ID {doc_id}: {e}')
            return None

    @override
    def find_all(self, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """조건에 맞는 모든 상품 조회"""
        try:
            filter_dict = filter_dict or {}
            cursor = self.collection.find(filter_dict)
            # products = []

            # for product in cursor:
            #     processed_product = self._process_product_output(product)
            #     products.append(processed_product)

            return cursor
        except Exception as e:
            logger.error(f'Error finding products: {e}')
            return []

    @override
    def create(self, document: Dict) -> Optional[str]:
        """상품 생성"""
        try:
            # # 상품 데이터 검증
            # if not self._validate_product_data(document):
            #     return None

            # # 상품 데이터 전처리
            # processed_data = self._process_product_input(document)

            # 삽입 실행
            result = self.collection.insert_one(document)
            return str(result.inserted_id) if result.inserted_id else None

        except DuplicateKeyError:
            logger.warning(f'Duplicate product ID: {document.get("product_id", "Unknown")}')
            return None
        except Exception as e:
            logger.error(f'Error creating product: {e}')
            return None

    @override
    def update_by_id(self, doc_id: str, update_data: Dict) -> bool:
        """상품 업데이트"""
        try:
            if not update_data:
                return False

            # # 업데이트 데이터 전처리
            # processed_update = self._process_update_data(update_data)

            result = self.collection.update_one({'_id': doc_id}, {'$set': update_data})

            return result.modified_count > 0
        except Exception as e:
            logger.error(f'Error updating product {doc_id}: {e}')
            return False

    @override
    def delete_by_id(self, doc_id: str) -> bool:
        """상품 삭제"""
        try:
            result = self.collection.delete_one({'_id': doc_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f'Error deleting product {doc_id}: {e}')
            return False

    @override
    def find(self, query: dict) -> Iterator[Dict]:
        """쿼리에 맞는 문서 조회"""
        return self.collection.find(query)

    # ============================================================================
    # Bulk Write 기능
    # ============================================================================
    def bulk_insert_documents(self, session: ClientSession, documents: List[Dict[str, Any]], ordered: bool = False) -> Dict[str, Any]:
        """
        MongoDB bulk write를 이용한 대량 문서 삽입

        Args:
            documents (List[Dict[str, Any]]): 삽입할 문서 리스트
            ordered (bool): 순서대로 처리할지 여부 (False면 병렬 처리)

        Returns:
            Dict[str, Any]: 삽입 결과 정보
                {
                    "success": bool,
                    "inserted_count": int,
                    "error_count": int,
                    "errors": List[Dict],
                    "inserted_ids": List[str],
                    "execution_time": float
                }
        """
        import time

        start_time = time.time()
        result_info = {'success': False, 'inserted_count': 0, 'error_count': 0, 'errors': [], 'inserted_ids': [], 'execution_time': 0.0}

        if not documents:
            raise ValueError('No documents provided for bulk insert')

        def txn(sess):
            logger.info(f'Starting bulk insert transaction for {len(documents)} documents')
            operations = [InsertOne(doc) for doc in documents]
            bulk_result = self.collection.bulk_write(operations, ordered=ordered, session=sess)
            return bulk_result

        try:
            bulk_result = session.with_transaction(txn)
            result_info['success'] = True
            result_info['inserted_count'] = bulk_result.inserted_count
            # inserted_ids는 bulk_write의 InsertManyResult와 달리 insert_one/bulk_write에서는 제공되지 않음
            # pymongo 최신 버전에서도 bulk_write는 inserted_ids를 제공하지 않으므로 빈 리스트로 둠
            result_info['inserted_ids'] = []
            logger.info(f'Bulk insert completed successfully: {bulk_result.inserted_count} documents inserted')
        except BulkWriteError as bwe:
            result_info['error_count'] = len(bwe.details.get('writeErrors', []))
            result_info['inserted_count'] = bwe.details.get('nInserted', 0)
            for write_error in bwe.details.get('writeErrors', []):
                error_info = {
                    'type': 'bulk_write_error',
                    'index': write_error.get('index'),
                    'code': write_error.get('code'),
                    'message': write_error.get('errmsg', 'Unknown bulk write error'),
                    'document_id': write_error.get('op', {}).get('_id', 'Unknown'),
                }
                result_info['errors'].append(error_info)
            logger.error(f'Bulk write error: {result_info["error_count"]} errors, {result_info["inserted_count"]} inserted')
        except WriteError as we:
            result_info['error_count'] = 1
            error_info = {'type': 'write_error', 'code': we.code, 'message': str(we), 'details': getattr(we, 'details', {})}
            result_info['errors'].append(error_info)
            logger.error(f'Write error during bulk insert: {we}')
        except Exception as e:
            result_info['error_count'] = len(documents)
            error_info = {'type': 'unexpected_error', 'message': str(e), 'error_class': type(e).__name__}
            result_info['errors'].append(error_info)
            logger.error(f'Unexpected error during bulk insert: {e}')

        result_info['execution_time'] = time.time() - start_time

        if result_info['success']:
            logger.info(f'Bulk insert completed in {result_info["execution_time"]:.2f}s')
        else:
            logger.error(f'Bulk insert failed after {result_info["execution_time"]:.2f}s')

        return result_info

    def bulk_update_documents(
        self, session: ClientSession, document_ids: List[str], update_data: Dict[str, Any], ordered: bool = False
    ) -> Dict[str, Any]:
        """
        MongoDB bulk write를 이용한 대량 문서 업데이트

        Args:
            session (ClientSession): MongoDB 세션 (None일 수 있음)
            document_ids (List[str]): 업데이트할 문서 ID 리스트
            update_data (Dict[str, Any]): 업데이트할 데이터
            ordered (bool): 순서대로 처리할지 여부 (False면 병렬 처리)

        Returns:
            Dict[str, Any]: 업데이트 결과 정보
                {
                    "success": bool,
                    "modified_count": int,
                    "error_count": int,
                    "errors": List[Dict],
                    "execution_time": float
                }
        """
        import time
        from pymongo.operations import UpdateOne

        start_time = time.time()
        result_info = {'success': False, 'modified_count': 0, 'error_count': 0, 'errors': [], 'execution_time': 0.0}

        if not document_ids:
            raise ValueError('No document IDs provided for bulk update')

        try:
            operations = [UpdateOne({'_id': doc_id}, {'$set': update_data}) for doc_id in document_ids]

            logger.info(f'Starting bulk update for {len(document_ids)} documents (no session)')
            bulk_result = self.collection.bulk_write(operations, ordered=ordered)

            result_info['success'] = True
            result_info['modified_count'] = bulk_result.modified_count
            logger.info(f'Bulk update completed successfully: {bulk_result.modified_count} documents modified')

        except BulkWriteError as bwe:
            result_info['error_count'] = len(bwe.details.get('writeErrors', []))
            result_info['modified_count'] = bwe.details.get('nModified', 0)
            for write_error in bwe.details.get('writeErrors', []):
                error_info = {
                    'type': 'bulk_write_error',
                    'index': write_error.get('index'),
                    'code': write_error.get('code'),
                    'message': write_error.get('errmsg', 'Unknown bulk write error'),
                    'document_id': write_error.get('op', {}).get('_id', 'Unknown'),
                }
                result_info['errors'].append(error_info)
            logger.error(f'Bulk write error: {result_info["error_count"]} errors, {result_info["modified_count"]} modified')
        except WriteError as we:
            result_info['error_count'] = 1
            error_info = {'type': 'write_error', 'code': we.code, 'message': str(we), 'details': getattr(we, 'details', {})}
            result_info['errors'].append(error_info)
            logger.error(f'Write error during bulk update: {we}')
        except Exception as e:
            result_info['error_count'] = len(document_ids)
            error_info = {'type': 'unexpected_error', 'message': str(e), 'error_class': type(e).__name__}
            result_info['errors'].append(error_info)
            logger.error(f'Unexpected error during bulk update: {e}')

        result_info['execution_time'] = time.time() - start_time

        if result_info['success']:
            logger.info(f'Bulk update completed in {result_info["execution_time"]:.2f}s')
        else:
            logger.error(f'Bulk update failed after {result_info["execution_time"]:.2f}s')

        return result_info

    # def bulk_insert_with_validation(self, documents: List[Dict[str, Any]],
    #                                validation_rules: Optional[Dict] = None) -> Dict[str, Any]:
    #     """
    #     데이터 검증을 포함한 대량 삽입

    #     Args:
    #         documents (List[Dict[str, Any]]): 삽입할 문서 리스트
    #         validation_rules (Optional[Dict]): 검증 규칙

    #     Returns:
    #         Dict[str, Any]: 삽입 결과 정보
    #     """
    #     # 데이터 검증
    #     valid_documents = []
    #     validation_errors = []

    #     for i, doc in enumerate(documents):
    #         validation_result = self._validate_document(doc, validation_rules)
    #         if validation_result["valid"]:
    #             valid_documents.append(doc)
    #         else:
    #             validation_errors.append({
    #                 "index": i,
    #                 "document_id": doc.get("_id", f"index_{i}"),
    #                 "errors": validation_result["errors"]
    #             })

    #     # 검증 실패한 문서가 있으면 오류 정보와 함께 반환
    #     if validation_errors:
    #         return {
    #             "success": False,
    #             "inserted_count": 0,
    #             "error_count": len(validation_errors),
    #             "errors": validation_errors,
    #             "inserted_ids": [],
    #             "execution_time": 0.0,
    #             "validation_failed": True
    #         }

    #     # 검증된 문서들로 bulk insert 실행
    #     return self.bulk_insert_documents(valid_documents)

    # def _validate_document(self, document: Dict[str, Any],
    #                       validation_rules: Optional[Dict] = None) -> Dict[str, Any]:
    #     """
    #     문서 검증

    #     Args:
    #         document (Dict[str, Any]): 검증할 문서
    #         validation_rules (Optional[Dict]): 검증 규칙

    #     Returns:
    #         Dict[str, Any]: 검증 결과
    #     """
    #     errors = []

    #     # 기본 검증 규칙
    #     default_rules = {
    #         "required_fields": ["_id"],
    #         "forbidden_fields": []
    #     }

    #     rules = {**default_rules, **(validation_rules or {})}

    #     # 필수 필드 검증
    #     for field in rules.get("required_fields", []):
    #         if field not in document or document[field] is None:
    #             errors.append(f"Required field '{field}' is missing or null")

    #     # 금지된 필드 검증
    #     for field in rules.get("forbidden_fields", []):
    #         if field in document:
    #             errors.append(f"Forbidden field '{field}' is present")

    #     # 문서 크기 검증 (MongoDB 16MB 제한)
    #     import sys
    #     doc_size = sys.getsizeof(document)
    #     if doc_size > 16 * 1024 * 1024:  # 16MB
    #         errors.append(f"Document size ({doc_size} bytes) exceeds 16MB limit")

    #     return {
    #         "valid": len(errors) == 0,
    #         "errors": errors
    #     }

    # ============================================================================
    # 패션 도메인 특화 메서드들
    # ============================================================================
    # def find_products(self,
    #                  filter_query: Optional[Dict[str, Any]] = None,
    #                  projection: Optional[Dict[str, int]] = None,
    #                  sort_by: Optional[List[tuple]] = None,
    #                  limit: Optional[int] = None,
    #                  skip: Optional[int] = None) -> List[Dict[str, Any]]:
    #     """고급 상품 검색 (필터링, 정렬, 페이징)"""
    #     try:
    #         cursor = self.collection.find(filter_query or {}, projection)

    #         if sort_by:
    #             cursor = cursor.sort(sort_by)
    #         if skip:
    #             cursor = cursor.skip(skip)
    #         if limit:
    #             cursor = cursor.limit(limit)

    #         products = []
    #         for product in cursor:
    #             processed_product = self._process_product_output(product)
    #             products.append(processed_product)

    #         return products

    #     except Exception as e:
    #         logger.error(f"Error in advanced product search: {e}")
    #         return []

    def find_by_category(self, category_main: str, category_sub: Optional[str] = None) -> List[Dict]:
        """카테고리별 상품 조회"""
        filter_dict = {'category_main': category_main}
        if category_sub:
            filter_dict['category_sub'] = category_sub

        return self.find_products(filter_query=filter_dict)

    # def find_by_caption_status(self , caption_status: str) -> List[Dict]:
    #     """캡션 상태별 상품 조회"""
    #     query = self.query_builder.caption_status_filter(caption_status)
    #     return self.find(query)

    def find_by_data_status(self, data_status: str) -> List[Dict]:
        """데이터 상태별 상품 조회"""
        query = self.query_builder.data_status_filter(data_status)
        return self.find(query)

    async def vector_search(self, embedding: list[float], limit: int, pre_filter: Optional[Dict] = None) -> List[Dict]:
        """벡터 검색
        Args:
            query (str): 검색 쿼리
            limit (int): 검색 결과 개수
            pre_filter (Optional[Dict], optional): 사전 필터링 조건. Defaults to None.

        Returns:
            List[Dict]: 검색 결과 데이터
        """

        pipeline = self.query_builder.vector_search_pipeline(
            embedding=embedding,
            limit=limit,
            pre_filter=pre_filter,
            num_candidates=100,
            index_name='tmp',
            embedding_field_path='embedding.comprehensive_description.vector',
        )
        # TODO : 여기 부분 비동기 처리 해야함.
        return list(self.collection.aggregate(pipeline))

    def health_check(self) -> Dict[str, Any]:
        """리포지토리 헬스체크"""
        health_info = {
            'connected': False,
            'collection_exists': False,
            'connection_string': self.connection_string,
            'database_name': self.database_name,
            'collection_name': self.collection_name,
            'error': None,
        }

        try:
            # 연결 상태 확인
            health_info['connected'] = self.is_connected()
            health_info['collection_exists'] = self.collection_name in self.db_manager._db.list_collection_names()
            health_info['connection_string'] = self.connection_string
            health_info['database_name'] = self.database_name
            health_info['collection_name'] = self.collection_name
        except Exception as e:
            health_info['error'] = str(e)
            logger.error(f'Health check failed: {e}')

        return health_info

    # def get_product_stats(self) -> Dict[str, Any]:
    #     """상품 통계 정보"""
    #     try:
    #         total_count = self.count_documents()

    #         # 카테고리별 통계
    #         category_pipeline = [
    #             {"$group": {"_id": "$category_main", "count": {"$sum": 1}}},
    #             {"$sort": {"count": -1}}
    #         ]
    #         categories = list(self.collection.aggregate(category_pipeline))

    #         return {
    #             "total_products": total_count,
    #             "categories": categories,
    #             "database_info": self.get_connection_info()
    #         }

    #     except Exception as e:
    #         logger.error(f"Error getting product stats: {e}")
    #         return {"total_products": 0, "categories": [], "error": str(e)}

    # def create_products_bulk(self, products_data: List[Dict[str, Any]],
    #                        continue_on_error: bool = True) -> Dict[str, Any]:
    #     """여러 상품 일괄 생성"""
    #     if not products_data:
    #         return {"success_count": 0, "error_count": 0, "errors": []}

    #     # 데이터 검증 및 전처리
    #     valid_products, errors = self._prepare_bulk_data(products_data)

    #     if not valid_products:
    #         return {
    #             "success_count": 0,
    #             "error_count": len(products_data),
    #             "errors": errors
    #         }

    #     # 일괄 삽입 실행
    #     try:
    #         result = self.collection.insert_many(
    #             valid_products,
    #             ordered=not continue_on_error
    #         )

    #         return {
    #             "success_count": len(result.inserted_ids),
    #             "error_count": len(errors),
    #             "errors": errors,
    #             "inserted_ids": result.inserted_ids
    #         }

    #     except BulkWriteError as e:
    #         success_count = e.details.get('nInserted', 0)

    #         bulk_errors = errors + [
    #             {
    #                 "index": error.get('index'),
    #                 "error": error.get('errmsg', 'Unknown error')
    #             }
    #             for error in e.details.get('writeErrors', [])
    #         ]

    #         return {
    #             "success_count": success_count,
    #             "error_count": len(products_data) - success_count,
    #             "errors": bulk_errors
    #         }

    #     except Exception as e:
    #         logger.error(f"Bulk insert error: {e}")
    #         return {
    #             "success_count": 0,
    #             "error_count": len(products_data),
    #             "errors": [{"error": str(e)}]
    #         }

    # # ============================================================================
    # # 내부 헬퍼 메서드들 (데이터 처리 및 검증)
    # # ============================================================================
