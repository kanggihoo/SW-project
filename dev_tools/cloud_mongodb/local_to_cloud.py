import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
import logging
from db import create_fashion_repo
from pymongo import UpdateOne

logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d' , datefmt='%H:%M:%S')
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
    #TODO : 여기서 이미지 개수 다르면 임시 방편으로 pass 해버려야 겠는데 
    sku_id = [product_id + "_" + c["name"] for c in color_info]
    for idx, c in enumerate(color_info):
        color_name.append(c["name"])
        color_hex.append(c["hex"])
        color_brightness.append(c["attributes"]["brightness"])
        color_saturation.append(c["attributes"]["saturation"])
        #TODO : 실제 이미지 개수랑 모델이 인식한 거랑 다른 경우에 대한 예외처리필요(한 이미지에 2개 옷있으면 색상을 2개 반환해버림)
        try:
            image_urls.append(representative_assets["color_variant"][idx])
        except:
            logger.error(f"color_variant 에 대응하는 이미지 없음 : {product_id} , {idx}")
            logger.error(f"color_variant 개수 : {len(representative_assets['color_variant'])}")
            logger.error(f"모델이 인식한 color 개수 : {len(color_info)}")
            raise Exception(f"color_variant 에 대응하는 이미지 없음 : {product_id} , {idx}")

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
    result = data_processing(doc)
    result["_id"] = doc["_id"]
    return result

def migrate_data_with_status_update(batch_size:int = 50):
    """Cloud로 데이터 마이그레이션 후 local status 업데이트"""
    cursor = local.find_by_data_status("EB_COMP")
    docs = []
    successful_uploads = []
    
    with cloud.db_manager.client.start_session() as session:
        try:
            for doc in cursor:
                processed_doc = data_processing(doc)
                processed_doc["_id"] = doc["_id"]
                docs.append(processed_doc)
                
                if len(docs) >= batch_size:
                    # Cloud 업로드
                    result = cloud.bulk_insert_documents(session, docs)
                    
                    if result and result.get("success", False):
                        # 성공한 문서들의 ID 수집
                        batch_ids = [doc["_id"] for doc in docs]
                        successful_uploads.extend(batch_ids)
                        
                        # Local status 업데이트 (session 없이)
                        local_update_result = local.bulk_update_documents(
                            session=None,
                            document_ids=batch_ids,
                            update_data={"data_status": "CL_COMP"}
                        )
                        
                        if local_update_result.get("success", False):
                            logger.info(f"✅ 배치 처리 완료: {len(docs)}개 문서")
                            logger.info(f"   - Cloud 업로드: {result['inserted_count']}개")
                            logger.info(f"   - Local 업데이트: {local_update_result['modified_count']}개")
                        else:
                            logger.error(f"❌ Local 업데이트 실패: {local_update_result['error_count']}개 오류")
                    else:
                        logger.error(f"❌ Cloud 업로드 실패: {len(docs)}개 문서")
                    
                    docs = []
            
            # 남은 문서들 처리
            if docs:
                result = cloud.bulk_insert_documents(session, docs)
                
                if result and result.get("success", False):
                    batch_ids = [doc["_id"] for doc in docs]
                    successful_uploads.extend(batch_ids)
                    
                    local_update_result = local.bulk_update_documents(
                        session=None,
                        document_ids=batch_ids,
                        update_data={"data_status": "CL_COMP"}
                    )
                    
                    if local_update_result.get("success", False):
                        logger.info(f"✅ 마지막 배치 처리 완료: {len(docs)}개 문서")
                        logger.info(f"   - Cloud 업로드: {result['inserted_count']}개")
                        logger.info(f"   - Local 업데이트: {local_update_result['modified_count']}개")
                    else:
                        logger.error(f"❌ 마지막 배치 Local 업데이트 실패: {local_update_result['error_count']}개 오류")
                else:
                    logger.error(f"❌ 마지막 배치 Cloud 업로드 실패: {len(docs)}개 문서")
                    
        except Exception as e:
            logger.error(f"❌ 마이그레이션 중 예외 발생: {e}")
            # 세션 롤백
            session.abort_transaction()
            raise

if __name__ == "__main__":
    # 새로운 함수 사용
    migrate_data_with_status_update(batch_size=10)
    
   
        
        
        
        

    

    
    
    





    








