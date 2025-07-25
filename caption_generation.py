import logging
from aws.aws_manager import AWSManager
from processing.image_processor import download_images_sync , parsing_data_for_llm 
from caption.models.product import ImageManager, ProductManager, Base64DataForLLM
from caption.fashion_caption_generator import FashionCaptionGenerator
import sys
from db.repository.fashion import FashionRepository
from db.config.database import DatabaseManager
from db import create_fashion_repo
from db.config import Config
from utils import setup_logger
from dotenv import load_dotenv

#TODO : 실패한 제품 id에 대한 처리 필요 (log 파일 저장 )
logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s : %(filename)s - %(lineno)d' , datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
if __name__ == "__main__":
    load_dotenv()
    db_config = Config()
    aws_manager = AWSManager()    
    fashion_repository_local = create_fashion_repo(use_atlas=False)
    fashion_repository_atlas = create_fashion_repo(use_atlas=True)


    fashion_caption_generator = FashionCaptionGenerator()
    pagenator = aws_manager.dynamodb_manager.get_product_pagenator(partition={"key":"sub_category_curation_status","value":"3002#COMPLETED","type":"S"},GSI_NAME = "CurationStatus-SubCategory-GSI")
    total_count = 0
    success_count = 0
    fail_count = 0
    for page in pagenator:
        items = page.get('Items')
        logger.debug(f"현재 총 제품 수 : {page.get('Count')}")
        total_count += page.get('Count')
        if items:
            #TODO 여기 for문은 좀더 효율적으로 돌릴 수 있을 거 같은데 
            for i in items:
                try:
                    item = aws_manager.dynamodb_manager._convert_dynamodb_item_to_python(i)
                    logger.info(f"main_category : {item.get('main_category')} , sub_category : {item.get('sub_category')} , 제품 id : {item.get('product_id')} ")
                    main_category = item.get('main_category')
                    sub_category = item.get('sub_category')
                    product_id = item.get('product_id')
                    representative_assets = item.get('representative_assets')
                    
                    category = "상의" if main_category.lower() == "top" else "하의"
                    images = aws_manager.get_product_images_from_paginator(item)
                    # logger.info(f"이미지 정보 리스트 : {images}")  
                    logger.info(f"category : {category}")
                    download_images_sync(images)
                    base64_data_for_llm = parsing_data_for_llm(images, target_size=512)
                    #해당 제품이 사이즈 정보 있는지 확인 (local mongodb 에서 확인, _id로 접근)
                    doc = fashion_repository_local.find_by_id(product_id)

                    has_size = True if doc.get("size_detail_info") else False
                    result = fashion_caption_generator.invoke(base64_data_for_llm , category=category , has_size=has_size)
                    
                    deep_caption = result.get("deep_caption").model_dump()
                    color_images = result.get("color_images").model_dump()
                    text_images = result.get("text_images").model_dump_json() if result.get("text_images") else None

                    caption_result = {
                        "caption_info": {
                            "caption_status": "COMPLETED",
                            "deep_caption": deep_caption,
                            "color_images": color_images,
                            "text_images": text_images,
                        },
                        "representative_assets": representative_assets
                    }
                    
                    #dynamodb 반영 (caption PENDING => COMPLETED)
                    # aws_manager.dynamodb_manager.update_caption_result(sub_category, product_id, "COMPLETED")
            
                    #local mongodb 에 저장 
                    fashion_repository_local.update_by_id(product_id , caption_result)
                    success_count+=1
                    sys.exit()
    
                except Exception as e:
                    logger.error(f"Error caption generation: {e}")
                    fail_count+=1
                    sys.exit()
    logger.info("caption generation completed")
    logger.info(f"총 제품 수 : {total_count}")
    logger.info(f"성공 제품 수 : {success_count}")
    logger.info(f"실패 제품 수 : {fail_count}")

              

                
