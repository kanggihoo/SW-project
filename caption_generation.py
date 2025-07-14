import logging
import sys
from aws.aws_manager import AWSManager
from processing.image_processor import download_images_sync , parsing_data_for_llm 
from caption.models.product import ImageManager, ProductManager, Base64DataForLLM
from caption.fashion_caption_generator import FashionCaptionGenerator
import json 
from utils import setup_logger

logger = setup_logger()
logger.info("test")
if __name__ == "__main__":
    aws_manager = AWSManager()
    fashion_caption_generator = FashionCaptionGenerator()
    pagenator = aws_manager.dynamodb_manager.get_product_pagenator(sub_category=1005 , condition={"curation_status":"COMPLETED"})
    count = 0
    for page in pagenator:
        items = page.get('Items')
        logger.info(f"현재 총 제품 수 : {page.get('Count')}")
        count += page.get('Count')
        if items:
            # 여기 for문은 좀더 효율적으로 돌릴 수 있을 거 같은데 
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

                # dynamodb 반영 
                aws_manager.dynamodb_manager.update_caption_result(sub_category, product_id, "COMPLETED")
        
                # csv 파일에서 product_id로 부터 추가 정보 가져오기 (json으로 저장할 이유가 없네 , csv 파일로 빠르게 제품 id를 인덱스로 해서 빠르게 찾을 수 있게 해야지)

                # 최종 데이터 분리 (denormalize 및 대표 이미지 색상 필드 추가 및 product_id + 색상명으로 유니크 키 생성)

                # 최종 데이터 저장 mongodb 저장 => 이후에 벡터 필드에 대한 임베딩 벡터 추가 

                
