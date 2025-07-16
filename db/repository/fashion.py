from .base import BaseRepository
from typing import Dict, Any, Optional , List
from pymongo.errors import DuplicateKeyError , BulkWriteError
import logging
import os
logger = logging.getLogger(__name__)
class FashionRepository(BaseRepository):
    def __init__(self , connection_string: str = None):
        super().__init__(connection_string=connection_string)

    def find_by_id(self, product_id: str) -> Optional[Dict]:
        try:
            return self.collection.find_one({"_id": product_id})
        except Exception as e:
            logger.error(f"상품 조회 중 오류: {e}")
            return None
    
    def find_all(self, filter_dict: Dict = None) -> Any:
        filter_dict = filter_dict or {}
        return self.collection.find(filter_dict)
    
    def find_products(self, 
                    filter_query: Optional[Dict[str, Any]] = None,
                    projection: Optional[Dict[str, int]] = None,
                    sort_by: Optional[List[tuple]] = None,
                    limit: Optional[int] = None,
                    skip: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        상품 검색
        
        Args:
            filter_query: 검색 조건
            projection: 반환할 필드 지정
            sort_by: 정렬 조건
            limit: 결과 개수 제한
            skip: 건너뛸 개수
            
        Returns:
            List: 검색 결과
        """
        try:
            cursor = self.collection.find(
                filter_query or {},
                projection
            )
            
            if sort_by:
                cursor = cursor.sort(sort_by)
            
            if skip:
                cursor = cursor.skip(skip)
                
            if limit:
                cursor = cursor.limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"상품 검색 중 오류: {e}")
            return []
    
    def insert_single_product(self, product_data: Dict[str, Any]) -> bool:
        """
        단일 상품 데이터 저장
        
        Args:
            product_data: 상품 데이터 딕셔너리
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 데이터 검증
            if not self._validate_product_data(product_data):
                logger.error(f"상품 데이터 검증 실패: {product_data.get('product_id', 'Unknown')}")
                return False
            
            # product_id를 _id로 매핑하기 위해 복사본 생성
            product_data_copy = product_data.copy()
            product_id = product_data_copy.get('product_id')
            
            # _id 필드를 product_id 값으로 설정
            product_data_copy['_id'] = product_id    
            # 저장
            result = self.collection.insert_one(product_data_copy)
            
            if result.inserted_id:
                logger.info(f"상품 저장 성공: {product_id} (MongoDB _id: {result.inserted_id})")
                return True
            else:
                logger.error(f"상품 저장 실패: {product_id}")
                return False
                
        except DuplicateKeyError:
            logger.warning(f"중복 상품 ID: {product_data.get('product_id', 'Unknown')}")
            return False
        except Exception as e:
            logger.error(f"상품 저장 중 오류: {e}")
            return False
    
    def insert_multiple_products(self, products_data: List[Dict[str, Any]], 
                               continue_on_error: bool = True) -> Dict[str, Any]:
        """
        여러 상품 데이터 일괄 저장 (한번 bulk 작업시 48MB 제한 (적절하게 배치 나눠서 작업(1000개 단위로 작업)))
        
        Args:
            products_data: 상품 데이터 리스트
            continue_on_error: 오류 발생시 계속 진행 여부
        Returns:
        """
        """
        여러 상품 데이터 일괄 저장
        Args:
            products_data: 상품 데이터 리스트
            continue_on_error: 오류 발생시 계속 진행 여부
            
        Returns:
            Dict: 저장 결과 통계
        """
        if not products_data:
            return {"success_count": 0, "error_count": 0, "errors": []}
        
        # # 메타데이터 추가
        # current_time = datetime.now()
        # for product in products_data:
        #     product["created_at"] = current_time
        #     product["updated_at"] = current_time
        
        # 데이터 검증
        valid_products = []
        validation_errors = []
        
        for product in products_data:
            if self._validate_product_data(product):
                valid_products.append(product)
            else:
                validation_errors.append({
                    "product_id": product.get("product_id", "Unknown"),
                    "error": "데이터 검증 실패"
                })
        
        if not valid_products:
            logger.error("유효한 상품 데이터가 없습니다.")
            return {
                "success_count": 0,
                "error_count": len(products_data),
                "errors": validation_errors
            }
        
        try:
            # 일괄 저장
            result = self.collection.insert_many(
                valid_products, 
                ordered=not continue_on_error
            )
            
            success_count = len(result.inserted_ids)
            error_count = len(products_data) - success_count
            
            logger.info(f"일괄 저장 완료 - 성공: {success_count}, 실패: {error_count}")
            
            return {
                "success_count": success_count,
                "error_count": error_count,
                "errors": validation_errors,
                "inserted_ids": result.inserted_ids
            }
            
        except BulkWriteError as e:
            # 부분적 성공인 경우 처리
            success_count = e.details.get('nInserted', 0)
            error_count = len(products_data) - success_count
            
            errors = validation_errors + [
                {
                    "index": error.get('index'),
                    "error": error.get('errmsg', 'Unknown error')
                }
                for error in e.details.get('writeErrors', [])
            ]
            
            logger.warning(f"일괄 저장 부분 성공 - 성공: {success_count}, 실패: {error_count}")
            
            return {
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"일괄 저장 중 오류: {e}")
            return {
                "success_count": 0,
                "error_count": len(products_data),
                "errors": [{"error": str(e)}]
            }
        
    def update_product(self, product_id: str, update_data: Dict[str, Any]) -> bool:
        """
        상품 정보 부분 업데이트
        
        Args:
            product_id: 상품 ID
            update_data: 업데이트할 데이터
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # update_data["updated_at"] = datetime.now()
            
            result = self.collection.update_one(
                {"_id": product_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"상품 업데이트 성공: {product_id}")
                return True
            else:
                logger.warning(f"업데이트할 상품을 찾을 수 없음: {product_id}")
                return False
                
        except Exception as e:
            logger.error(f"상품 업데이트 중 오류: {e}")
            return False
    def upsert_product(self, product_data: Dict[str, Any]) -> bool:
        """
        상품 데이터 업서트 (존재하면 업데이트, 없으면 삽입)
        
        Args:
            product_data: 상품 데이터 딕셔너리
            
        Returns:
            bool: 처리 성공 여부
        """
        try:
            if not self._validate_product_data(product_data):
                logger.error(f"상품 데이터 검증 실패: {product_data.get('product_id', 'Unknown')}")
                return False
            
            product_id = product_data["product_id"]
            
            result = self.collection.replace_one(
                {"product_id": product_id},
                product_data,
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"상품 신규 생성: {product_id}")
            elif result.modified_count > 0:
                logger.info(f"상품 업데이트: {product_id}")
            else:
                logger.info(f"상품 변경사항 없음: {product_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"상품 업서트 중 오류: {e}")
            return False
    
    # def insert_from_local_to_atlas(self, doc:dict , ) -> bool:
    #     """
    #     로컬 데이터베이스에서 데이터 가져와서 아틀라스 데이터베이스에 저장
    #     """
    #     try:
    #         product_data = self.find_by_id(product_id)
    #         if not product_data:
    
    def delete_product(self, product_id: str) -> bool:
        """
        상품 삭제
        
        Args:
            product_id: 상품 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            result = self.collection.delete_one({"_id": product_id})
            
            if result.deleted_count > 0:
                logger.info(f"상품 삭제 성공: {product_id}")
                return True
            else:
                logger.warning(f"삭제할 상품을 찾을 수 없음: {product_id}")
                return False
                
        except Exception as e:
            logger.error(f"상품 삭제 중 오류: {e}")
            return False
    def _validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """
        상품 데이터 유효성 검증
        
        Args:
            product_data: 검증할 상품 데이터
            
        Returns:
            bool: 유효성 검증 결과
        """
        required_fields = [
            "product_id",
            "category_main",
            "category_sub"
        ]
        
        # 필수 필드 체크
        for field in required_fields:
            if field not in product_data or not product_data[field]:
                logger.error(f"필수 필드 누락: {field}")
                return False
        
        # # 데이터 타입 체크
        # try:
        #     if "product_price" in product_data:
        #         float(product_data["product_price"])
            
        #     if "avg_rating" in product_data:
        #         float(product_data["avg_rating"])
                
        #     if "review_count" in product_data:
        #         int(str(product_data["review_count"]).replace(",", ""))
                
        # except (ValueError, TypeError) as e:
        #     logger.error(f"데이터 타입 오류: {e}")
        #     return False
        
        return True
    
    def close_connection(self):
        """MongoDB 연결 종료"""
        self.client.close()
        logger.info("MongoDB 연결 종료")