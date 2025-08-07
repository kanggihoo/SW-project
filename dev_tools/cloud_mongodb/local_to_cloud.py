import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
import logging
from db import create_fashion_repo
from pymongo import UpdateOne

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

local = create_fashion_repo(use_atlas=False)
cloud = create_fashion_repo(use_atlas=True)


# 로컬로부터 데이터 가져오기 
result_cursor = local.find_by_data_status("EB_COMP")

BATCH_SIZE = 50 
operations = []
local_id_to_update = []

#=============================================================================
# Products 정보 파싱 
#=============================================================================
def _captions_parsing(doc):
    return doc["caption_info"]["deep_caption"]["image_captions"]

def _description_info_parsing(doc):
    return doc["caption_info"]["text_images"]

def products_processing(doc):
    result = {}
    '''
    rename 해야 하는 키 정보 
    "product_brand_name" : "brand_name",
    "product_price" : "current_price",
    "product_discount_rate" : "discount_rate",
    "product_original_price" : "original_price",

    좀더 파싱 해야 하는 키정보
    captions 
    description_info
    '''
    
    result["product_id"] = doc["_id"]
    result["product_name"] = doc["product_name"]
    result["brand_name"] = doc["product_brand_name"]

    # 할인율 계산
    original_price = doc["product_original_price"]
    current_price = doc["product_price"]
    discount_rate =  int(round( ((original_price - current_price) / original_price)*100))

    result["current_price"] = current_price
    result["original_price"] = original_price
    result["discount_rate"] = discount_rate

    result["num_likes"] = doc["num_likes"]
    result["avg_rating"] = doc["avg_rating"]
    result["review_count"] = doc["review_count"]
    result["size_detail_info"] = doc["size_detail_info"]

    result["detail_text"] = doc["detail_text"]
    result["captions"] = _captions_parsing(doc)
    result["description_info"] = _description_info_parsing(doc)
    result["fit_info"] = doc["fit_info"]
    return result

#=============================================================================
# SKU 정보 파싱 
#=============================================================================

def _structured_attributes_parsing(doc , result):
    structured_attributes = doc["caption_info"]["deep_caption"]["structured_attributes"]
    subjective_info = structured_attributes["subjective"]
    common_tags = structured_attributes["common"]
    result["fit"] = subjective_info["fit"]
    result["style_tags"] = subjective_info["style_tags"]
    result["tpo_tags"] = subjective_info["tpo_tags"]
    result["common"] = common_tags

def _color_info_parsing(doc , product_id , result):
    color_name = []
    color_hex = []
    color_brightness = []
    color_saturation = []
    image_urls = []
    color_info:list = doc["caption_info"]["color_images"]["color_info"]
    representative_assets:list = doc["representative_assets"]

    sku_id = [product_id + "_" + c["name"] for c in color_info]
    for idx, c in enumerate(color_info):
        color_name.append(c["name"])
        color_hex.append(c["hex"])
        color_brightness.append(c["attributes"]["brightness"])
        color_saturation.append(c["attributes"]["saturation"])
        image_urls.append(representative_assets["color_variant"][idx])

    result["sku_id"] = sku_id
    result["color_name"] = color_name
    result["color_hex"] = color_hex
    result["color_brightness"] = color_brightness
    result["color_saturation"] = color_saturation
    result["image_urls"] = image_urls

def skus_processing(doc):
    result = {}
    product_id = doc["_id"]
        
    _color_info_parsing(doc , product_id , result)

    result["main_category"] = doc["main_category"]
    result["sub_category"] = doc["sub_category"]
    result["gender"] = doc["gender"]

    _structured_attributes_parsing(doc , result)

    return result

#=============================================================================
# Product Images 정보 파싱 
#=============================================================================
def product_images_processing(doc):
    
    return doc["representative_assets"]

#=============================================================================
# Product Embedding 정보 파싱 
#=============================================================================
def product_embedding_processing(doc):
    return doc["embedding"]

def product_reviews_processing(doc):
    return doc["review_texts"]

def data_processing(doc):
    result = {}
    result["products"] = products_processing(doc)
    result["product_skus"] = skus_processing(doc)
    result["images"] = product_images_processing(doc)
    result["embedding"] = product_embedding_processing(doc)
    result["reviews"] = product_reviews_processing(doc)
    return result

def test_processing():
    doc = local.find_by_id("4026789")
    print(doc["_id"])
    result = data_processing(doc)
    return result

if __name__ == "__main__":
    import pprint
    result = test_processing()
    result["embedding"]["comprehensive_description"]["vector"] = result["embedding"]["comprehensive_description"]["vector"][:10]
    pprint.pprint(result , indent=4)

# for doc in result_cursor:
#     processed_doc = data_processing(doc.copy())
#     update_data = {k:v for k ,v in processed_doc.items() if k != "_id"}
#     operations.append(UpdateOne({"_id": doc["_id"]}, {"$set": update_data} , upsert=True))
#     local_id_to_update.append(processed_doc["_id"])

#     if len(operations) >= BATCH_SIZE:
#         try:
#             #TODO : 예외처리가 좀더 필요할거 같은데 , 2번의 bulk_write 중 하나라도 실패하면 어디서 실패하는지? 어떻게 알지 
#             result = cloud.collection.bulk_write(operations , ordered=False)
#             # 성공한 작업들 로깅
#             logger.info(f"✅ Cloud DB에  {BATCH_SIZE} 개 bulk_write 성공:")
#             logger.info(f"   - 수정된 문서: {result.modified_count}")
#             logger.info(f"   - 삽입된 문서: {result.upserted_count}")
#             logger.info(f"   - 매칭된 문서: {result.matched_count}")
#             # 로컴에서도 데이터 반영 
#             local_update_operations = [UpdateOne({"_id": local_id}, {"$set": {"data_status": "CL_COMP"}}) for local_id in local_id_to_update]
#             local.collection.bulk_write(local_update_operations , ordered=False)

#             logger.info(f"✅ Local DB에  {BATCH_SIZE} 개 bulk_write 성공(data_status 업데이트):")
#             logger.info(f"   - 수정된 문서: {result.modified_count}")
#             logger.info(f"   - 삽입된 문서: {result.upserted_count}")
#             logger.info(f"   - 매칭된 문서: {result.matched_count}")
#         except Exception as e:
#             logger.error(f"❌ 배치 중 예외 발생: {e}")
        
#         finally:
#             operations = []
#             local_id_to_update = []

# if operations:
#     try:
#         result = cloud.collection.bulk_write(operations , ordered=False)
#         logger.info(f"✅ Cloud DB에  {len(operations)} 개 bulk_write 성공:")
#         logger.info(f"   - 수정된 문서: {result.modified_count}")
#         logger.info(f"   - 삽입된 문서: {result.upserted_count}")
#         logger.info(f"   - 매칭된 문서: {result.matched_count}")

#         local_update_operations = [UpdateOne({"_id": local_id}, {"$set": {"data_status": "CL_COMP"}}) for local_id in local_id_to_update]
#         local.collection.bulk_write(local_update_operations , ordered=False)

#         logger.info(f"✅ Local DB에  {len(local_id_to_update)} 개 bulk_write 성공(data_status 업데이트):")
#         logger.info(f"   - 수정된 문서: {result.modified_count}")
#         logger.info(f"   - 삽입된 문서: {result.upserted_count}")
#         logger.info(f"   - 매칭된 문서: {result.matched_count}")
#     except Exception as e:
#         logger.error(f"❌ 배치 중 예외 발생: {e}")

        
        
        
        

    

    
    
    





    








