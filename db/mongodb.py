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
    
