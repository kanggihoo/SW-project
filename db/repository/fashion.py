from .base import BaseRepository
from typing import Dict, Any, Optional , List , override
from pymongo.errors import DuplicateKeyError , BulkWriteError
import logging
logger = logging.getLogger(__name__)

'''
어떻게 데이터를 가지고 올 것인지에 대한 작성 

'''
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
            product = self.collection.find_one({"_id": doc_id})
            # if product:
            #     return self._process_product_output(product)
            return product
        except Exception as e:
            logger.error(f"Error finding product by ID {doc_id}: {e}")
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
            logger.error(f"Error finding products: {e}")
            return []
    
    @override
    def create(self, document: Dict) -> Optional[str]:
        """상품 생성"""
        try:
            # 상품 데이터 검증
            if not self._validate_product_data(document):
                return None
            
            # # 상품 데이터 전처리
            # processed_data = self._process_product_input(document)
            
            # 삽입 실행
            result = self.collection.insert_one(document)
            return str(result.inserted_id) if result.inserted_id else None
            
        except DuplicateKeyError:
            logger.warning(f"Duplicate product ID: {document.get('product_id', 'Unknown')}")
            return None
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            return None
    
    @override
    def update_by_id(self, doc_id: str, update_data: Dict) -> bool:
        """상품 업데이트"""
        try:
            if not update_data:
                return False
            
            # # 업데이트 데이터 전처리
            # processed_update = self._process_update_data(update_data)
            
            result = self.collection.update_one(
                {"_id": doc_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating product {doc_id}: {e}")
            return False
    
    @override
    def delete_by_id(self, doc_id: str) -> bool:
        """상품 삭제"""
        try:
            result = self.collection.delete_one({"_id": doc_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting product {doc_id}: {e}")
            return False
    
    @override
    def find(self , query: dict) -> List[Dict]:
        """쿼리에 맞는 문서 조회"""
        return self.collection.find(query)
    
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
        filter_dict = {"category_main": category_main}
        if category_sub:
            filter_dict["category_sub"] = category_sub
        
        return self.find_products(filter_query=filter_dict)
    
    def find_by_caption_status(self , caption_status: str) -> List[Dict]:
        """캡션 상태별 상품 조회"""
        query = self.query_builder.caption_status_filter(caption_status)
        return self.find(query)
    
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
    # def _validate_product_data(self, product_data: Dict[str, Any]) -> bool:
    #     """상품 데이터 유효성 검증"""
    #     required_fields = ["product_id", "category_main", "category_sub"]
        
    #     for field in required_fields:
    #         if field not in product_data or not product_data[field]:
    #             logger.error(f"Required field missing: {field}")
    #             return False
        
    #     return True
    
    # def _process_product_input(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """입력 상품 데이터 전처리 (생성 시)"""
    #     processed_data = product_data.copy()
        
    #     # product_id를 _id로 매핑
    #     if "product_id" in processed_data:
    #         processed_data["_id"] = processed_data["product_id"]
        
    #     return processed_data
    
    # def _process_product_output(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """출력 상품 데이터 후처리 (조회 시)"""
    #     processed_data = product_data.copy()
        
    #     # MongoDB ObjectId를 문자열로 변환
    #     if "_id" in processed_data:
    #         processed_data["_id"] = str(processed_data["_id"])
        
    #     return processed_data
    
    # def _process_update_data(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """업데이트 데이터 전처리"""
    #     # 업데이트에서는 _id 변경 금지
    #     processed_data = update_data.copy()
        
    #     # _id나 product_id 변경 방지
    #     processed_data.pop("_id", None)
    #     processed_data.pop("product_id", None)
        
    #     return processed_data
    
    # def _prepare_bulk_data(self, products_data: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
    #     """일괄 처리용 데이터 검증 및 전처리"""
    #     valid_products = []
    #     errors = []
        
    #     for i, product in enumerate(products_data):
    #         if self._validate_product_data(product):
    #             processed_product = self._process_product_input(product)
    #             valid_products.append(processed_product)
    #         else:
    #             errors.append({
    #                 "index": i,
    #                 "product_id": product.get("product_id", "Unknown"),
    #                 "error": "Validation failed"
    #             })
        
    #     return valid_products, errors