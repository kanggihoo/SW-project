import logging
import sys
from aws.aws_manager import AWSManager
from processing.image_processor import download_images_sync , parsing_data_for_llm 
from caption.models.product import ImageManager, ProductManager, Base64DataForLLM
from caption.fashion_caption_generator import FashionCaptionGenerator

from db.repository.fashion import FashionRepository
from db.config.database import DatabaseManager
import json 
from db.config import Config
from utils import setup_logger

logger = logging.getLogger(__name__)
if __name__ == "__main__":
    db_config = Config()
    aws_manager = AWSManager()

    mongodb_client = DatabaseManager(connection_string=db_config["MONGODB_LOCAL_CONNECTION_STRING"] , database_name=db_config["MONGODB_LOCAL_DATABASE_NAME"] , collection_name=db_config["MONGODB_LOCAL_COLLECTION_NAME"])
    mongodb_atlas_client = DatabaseManager(connection_string=db_config["MONGODB_ATLAS_CONNECTION_STRING"] , database_name=db_config["MONGODB_ATLAS_DATABASE_NAME"] , collection_name=db_config["MONGODB_ATLAS_COLLECTION_NAME"])
    collection_local = mongodb_client.get_collection()
    collection_atlas = mongodb_atlas_client.get_collection()
    fashion_repository = FashionRepository(collection=collection_local)


    fashion_caption_generator = FashionCaptionGenerator()
    pagenator = aws_manager.dynamodb_manager.get_product_pagenator(sub_category=1005 , condition={"curation_status":"COMPLETED"})
    count = 0
    for page in pagenator:
        items = page.get('Items')
        logger.info(f"현재 총 제품 수 : {page.get('Count')}")
        count += page.get('Count')
        if items:
            #TODO 여기 for문은 좀더 효율적으로 돌릴 수 있을 거 같은데 
            for item in items:
                logger.info(f"main_category : {item.get('main_category')} , sub_category : {item.get('sub_category')} , 제품 id : {item.get('product_id')} , 제품 이름 : {item.get('product_name')}")
                main_category = item.get('main_category')
                sub_category = item.get('sub_category')
                product_id = item.get('product_id')
                
                images = aws_manager.get_product_images_from_paginator(item)
                logger.info(f"이미지 정보 리스트 : {images}")   
                download_images_sync(images)
                base64_data_for_llm = parsing_data_for_llm(images, target_size=224)
                result = fashion_caption_generator.invoke(base64_data_for_llm , category="상의")
                
                deep_caption = result.get("deep_caption").model_dump()
                color_images = result.get("color_images").model_dump()
                text_images = result.get("text_images").model_dump_json()

                # dynamodb 반영 (caption PENDING => COMPLETED)
                aws_manager.dynamodb_manager.update_caption_result(sub_category, product_id, "COMPLETED")
        
                #mongodb 로 부터 데이터 가져오기 _id로 접근 
                doc = fashion_repository.find_by_id(product_id)

                #TODO : mongoatlas에 저장할 필드만 가져오고 ,  # 최종 데이터 분리 (denormalize 및 대표 이미지 색상 필드 추가 및 product_id + 색상명으로 유니크 키 생성)
            
                # 최종 데이터 저장 mongodb atlas 저장 => 이후에 벡터 필드에 대한 임베딩 벡터 추가 
                '''
                - product_id , 
                - 
                
                '''

                
