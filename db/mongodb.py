"""
MongoDB Atlas 연결 및 벡터 검색을 위한 매니저 클래스
"""

import os
import logging
from typing import Optional, Dict, List, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class MongoDBAtlasManager:
   """
   MongoDB Atlas 연결 및 벡터 검색 관리 클래스
   """
   
   def __init__(
       self,
       connection_string: str|None = None,
       database_name: str = "fashion_search",
       collection_name: str = "products",
       timeout_ms: int = 5000
   ):
       """
       MongoDB Atlas 매니저 초기화
       
       Args:
           connection_string: MongoDB Atlas 연결 문자열 (환경변수에서 자동 로드)
           database_name: 사용할 데이터베이스 이름
           collection_name: 상품 데이터를 저장할 컬렉션 이름
           timeout_ms: 연결 타임아웃 (밀리초)
       """
       # 환경변수 로드
       load_dotenv()
       
       # 연결 설정
       self.connection_string = connection_string or os.getenv('MONGODB_ATLAS_URI')
       self.database_name = database_name
       self.collection_name = collection_name
       self.timeout_ms = timeout_ms
       
       # 클라이언트 및 컬렉션 초기화
       self.client: MongoClient
       self.database: Database 
       self.collection: Collection
       
       # 연결 초기화
       self._initialize_connection()
       
   def _initialize_connection(self) -> None:
       """MongoDB Atlas 연결 초기화"""
       try:
           if not self.connection_string:
               raise ValueError(
                   "MongoDB Atlas 연결 문자열이 필요합니다. "
                   "MONGODB_ATLAS_URI 환경변수를 설정하거나 connection_string 파라미터를 제공하세요."
               )
           
           # MongoDB 클라이언트 생성
           self.client = MongoClient(
               self.connection_string,
               serverSelectionTimeoutMS=self.timeout_ms,
               connectTimeoutMS=self.timeout_ms,
               socketTimeoutMS=self.timeout_ms,
               serverApi=ServerApi('1')
           )
           
           # 데이터베이스 및 컬렉션 참조
           self.database = self.client[self.database_name]
           self.collection = self.database[self.collection_name]
           
           # 연결 테스트
           self._test_connection()
           
           logger.info(f"MongoDB Atlas 연결 성공: {self.database_name}.{self.collection_name}")
           
       except Exception as e:
           logger.error(f"MongoDB Atlas 연결 실패: {e}")
           self._cleanup()
           raise
   
   def _test_connection(self) -> bool:
       """
       연결 상태 테스트
       
       Returns:
           bool: 연결 성공 여부
       """
       try:
           # 간단한 ping 명령으로 연결 테스트
           self.client.admin.command('ping')
           
           # 데이터베이스 접근 테스트
           collections = self.database.list_collection_names()
           logger.info(f"데이터베이스 '{self.database_name}' 접근 성공. 컬렉션 수: {len(collections)}")
           
           return True
           
       except (ConnectionFailure, ServerSelectionTimeoutError) as e:
           logger.error(f"MongoDB Atlas 연결 테스트 실패: {e}")
           return False
       except Exception as e:
           logger.error(f"예상치 못한 연결 오류: {e}")
           return False
   
   def create_vector_search_index(
       self,
       vector_field: str = "description_vector",
       similarity_metric: str = "cosine",
       dimensions: int = 1536  # OpenAI text-embedding-ada-002 차원수
   ) -> bool:
       """
       벡터 검색용 인덱스 생성
       
       Args:
           vector_field: 벡터가 저장될 필드명
           similarity_metric: 유사도 측정 방식 ('cosine', 'euclidean', 'dotProduct')
           dimensions: 벡터 차원수
           
       Returns:
           bool: 인덱스 생성 성공 여부
       """
       try:
           # Atlas Search 인덱스 정의
           index_definition = {
               "fields": [
                   {
                       "type": "vector",
                       "path": vector_field,
                       "numDimensions": dimensions,
                       "similarity": similarity_metric
                   }
               ]
           }
           
           # 인덱스 생성 (Atlas Search는 Atlas UI 또는 Atlas CLI를 통해 생성해야 함)
           logger.info(f"벡터 검색 인덱스 정의: {index_definition}")
           logger.warning(
               "벡터 검색 인덱스는 MongoDB Atlas UI에서 수동으로 생성해야 합니다. "
               f"다음 정의를 사용하세요: {index_definition}"
           )
           
           return True
           
       except Exception as e:
           logger.error(f"벡터 인덱스 생성 중 오류: {e}")
           return False
   
#    def get_collection_stats(self) -> Dict[str, Any]:
#        """
#        컬렉션 통계 정보 조회
       
#        Returns:
#            Dict: 컬렉션 통계 정보
#        """
#        try:
#            stats = self.database.command("collStats", self.collection_name)
           
#            simplified_stats = {
#                "document_count": stats.get("count", 0),
#                "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
#                "index_count": stats.get("nindexes", 0),
#                "avg_doc_size_bytes": stats.get("avgObjSize", 0)
#            }
           
#            logger.info(f"컬렉션 통계: {simplified_stats}")
#            return simplified_stats
           
#        except Exception as e:
#            logger.error(f"컬렉션 통계 조회 실패: {e}")
#            return {}
   
#    def ensure_indexes(self) -> bool:
#        """
#        필수 인덱스 생성
       
#        Returns:
#            bool: 인덱스 생성 성공 여부
#        """
#        try:
#            # 기본 인덱스들 생성
#            indexes_to_create = [
#                ("product_id", 1),  # 상품 ID 단일 인덱스
#                ("created_at", -1),  # 생성 시간 역순 인덱스
#                ([("style_tags", 1), ("tpo_tags", 1)], None)  # 복합 인덱스
#            ]
           
#            for index_spec in indexes_to_create:
#                if isinstance(index_spec[0], list):
#                    # 복합 인덱스
#                    self.collection.create_index(index_spec[0])
#                    logger.info(f"복합 인덱스 생성: {index_spec[0]}")
#                else:
#                    # 단일 인덱스
#                    self.collection.create_index([(index_spec[0], index_spec[1])])
#                    logger.info(f"단일 인덱스 생성: {index_spec[0]}")
           
#            # 현재 인덱스 목록 출력
#            indexes = list(self.collection.list_indexes())
#            logger.info(f"현재 인덱스 수: {len(indexes)}")
           
#            return True
           
#        except Exception as e:
#            logger.error(f"인덱스 생성 중 오류: {e}")
#            return False
   
#    def health_check(self) -> Dict[str, Any]:
#        """
#        연결 상태 및 시스템 상태 확인
       
#        Returns:
#            Dict: 상태 정보
#        """
#        health_status = {
#            "connection": False,
#            "database_accessible": False,
#            "collection_accessible": False,
#            "error_message": None
#        }
       
#        try:
#            # 연결 테스트
#            if self._test_connection():
#                health_status["connection"] = True
#                health_status["database_accessible"] = True
               
#                # 컬렉션 접근 테스트
#                doc_count = self.collection.count_documents({})
#                health_status["collection_accessible"] = True
#                health_status["document_count"] = doc_count
               
#                logger.info("MongoDB Atlas 상태 확인 완료 - 모든 시스템 정상")
               
#        except Exception as e:
#            health_status["error_message"] = str(e)
#            logger.error(f"상태 확인 중 오류: {e}")
       
#        return health_status
   
   def _cleanup(self) -> None:
       """리소스 정리"""
       if self.client:
           try:
               self.client.close()
               logger.info("MongoDB 클라이언트 연결 종료")
           except Exception as e:
               logger.error(f"클라이언트 종료 중 오류: {e}")
   
   def close(self) -> None:
       """연결 종료"""
       self._cleanup()
       
   def __enter__(self):
       """컨텍스트 매니저 진입"""
       return self
   
   def __exit__(self, exc_type, exc_val, exc_tb):
       """컨텍스트 매니저 종료"""
       self.close()


# 사용 예시 및 테스트 코드
if __name__ == "__main__":
   # 로깅 설정
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s : %(message)s (%(filename)s - %(lineno)d)',
       datefmt='%Y-%m-%d %H:%M:%S'
   )
   
#    try:
#        mongo_manager = MongoDBAtlasManager()
       
           
#    except Exception as e:
#        logger.error(f"MongoDB Atlas 매니저 테스트 실패: {e}")

    # def close(self):
    #     self.client.close()
        
# --- CRUD 함수들 ---
# 이 함수들은 database.py 내에 있거나, 각 라우터 파일로 옮겨질 수 있습니다.
# 여기서는 예시로 database.py에 둡니다.


# async def get_all_items_db(collection):
#     items = []
#     async for item in collection.find(): # Pymongo 4.x 부터는 find가 Cursor를 반환하므로 비동기 처리가 필요 없습니다.
#                                         # 하지만 FastAPI의 비동기 특성을 살리기 위해 async/await를 사용할 수 있습니다.
#                                         # Pymongo 자체는 동기 라이브러리이므로, 실제 DB 호출은 블로킹될 수 있습니다.
#                                         # 이를 해결하려면 Motor 같은 비동기 MongoDB 드라이버를 사용하는 것이 좋습니다.
#                                         # 여기서는 Pymongo를 사용하되, FastAPI 경로 함수를 async로 정의합니다.
#         items.append(item_helper(item))
#     return items
# def process_product_id(product:ProductDetailClientRequest)->dict:
#     """
#     제품 ID를 처리하고 딕셔너리로 반환합니다.
#     """
#     if not isinstance(product, ProductDetailClientRequest):
#         raise ValueError("product must be a ProductDetailClientRequest instance")
#     product_dict = product.model_dump()
#     last_updated = datetime.now()
#     product_dict["last_updated"] = last_updated
#     product_dict["_id"] = product_dict["product_id"]
#     product_dict.pop("product_id")
#     return product_dict

# #TODO async 처리 필요 (add_item_db 함수)
# def add_item_db(product:ProductDetailClientRequest , collection):
#     product_dict = process_product_id(product)
#     product_dict["preprocessing_status"] = {
#         "detail_crawling" : {
#             "status" : product_dict["success_status"],
#             "date" : product_dict["last_updated"]
#         }
#     }
    
#     # REVIEW 최종 DB에 넣기 전 $schema 최종 확인 필요
#     try:
#         product_db = collection.insert_one(product_dict) # Pymongo 4.x+ insert_one은 동기 함수입니다.
#         return collection.find_one({"_id": product_db.inserted_id})
#     except DuplicateKeyError as e:
#         error_message = f"이미 존재하는 제품id : {product_dict["_id"]}"
#         raise DuplicateKeyError(error_message) 
    


# def upsert_bulk_items_db(products:List[ProductDetailClientRequest] , collection):
#     bulk_operations = []
#     for product in products:
        
        
#         pre_product_dict = get_item_db(product.product_id, collection)
#         # db에 존재하지 않은 경우 => db에 추가
#         if pre_product_dict is None:
#             cur_product_dict = process_product_id(product)
#             cur_product_dict["preprocessing_status"] = {
#                     "detail_crawling" : {
#                     "status" : cur_product_dict["success_status"],
#                     "date" : cur_product_dict["last_updated"]
#                 }
#             }
#             bulk_operations.append(InsertOne(cur_product_dict))
#         else:
#             # db에 존재하는 경우 => 업데이트
#             if pre_product_dict["preprocessing_status"]["detail_crawling"]["status"] == "success":
#                 continue
#             else: # 변경사항 있는지 확인
#                 update_fields = {}
#                 for key, value in product["crawling_status"].items():
#                     if value == "failed":
#                         continue
#                     if value == "success" and product["crawling_status"][key] == "failed":
#                         update_fields[key] = product[key]
                
#                 if update_fields:
#                     bulk_operations.append(UpdateOne({"_id": pre_product_dict["_id"]}, {"$set": update_fields}))
#     print(bulk_operations)
#     if bulk_operations:
        
#         result =collection.bulk_write(bulk_operations)
#         print(dir(result))
#         final_result = {
#             "inserted_count" : result.inserted_count,
#             "upserted_count" : result.upserted_count,
#             "matched_count" : result.matched_count,
#             "modified_count" : result.modified_count,
#             "upserted_ids" : result.upserted_ids
#         }
#         print(final_result)
#         return final_result
#     else:
#         return {
#             "matched_count" : 0,
#             "modified_count" : 0,
#             "upserted_ids" : []
#         }
        
   
        
    
    
    


# def get_item_db(id: str, collection):        
#     return collection.find_one({"_id": id})

# # async def update_item_db(item_id: str, item_data: dict, collection):
# #     from bson import ObjectId
# #     try:
# #         oid = ObjectId(item_id)
# #     except Exception:
# #         return False # 잘못된 형식의 ID

# #     # 빈 데이터는 업데이트하지 않도록 필터링 (선택 사항)
# #     update_data = {k: v for k, v in item_data.items() if v is not None}
# #     if not update_data:
# #         # 모든 값이 None이면 업데이트할 내용이 없음
# #         # 이 경우, 기존 아이템을 그대로 반환하거나 특정 메시지를 반환할 수 있습니다.
# #         existing_item = await collection.find_one({"_id": oid})
# #         if existing_item:
# #             return item_helper(existing_item) # 변경 없이 기존 아이템 반환
# #         return None # 아이템이 없는 경우

# #     updated_item = await collection.update_one({"_id": oid}, {"$set": update_data})
# #     if updated_item.modified_count == 1:
# #         new_item = await collection.find_one({"_id": oid})
# #         return item_helper(new_item)
# #     # 아이템이 존재하지만 업데이트되지 않은 경우 (예: 동일한 데이터로 업데이트 시도)
# #     # 또는 아이템이 존재하지 않는 경우 modified_count가 0일 수 있습니다.
# #     existing_item = await collection.find_one({"_id": oid})
# #     if existing_item: # 아이템은 있지만 변경 사항이 없는 경우
# #         return item_helper(existing_item)
# #     return None # 아이템이 없거나 업데이트 실패

# def delete_item_db(id: str, collection):
#     return collection.delete_one({"_id": id})    
    
