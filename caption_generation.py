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

logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s : %(filename)s - %(lineno)d' , datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
if __name__ == "__main__":
    load_dotenv()
    db_config = Config()
    aws_manager = AWSManager()    
    fashion_repository_local = create_fashion_repo(use_atlas=False)
    fashion_repository_atlas = create_fashion_repo(use_atlas=True)


    fashion_caption_generator = FashionCaptionGenerator()
    pagenator = aws_manager.dynamodb_manager.get_product_pagenator(partition={"key":"sub_category_curation_status","value":"1005#COMPLETED","type":"S"},GSI_NAME = "CurationStatus-SubCategory-GSI")
    count = 0
    for page in pagenator:
        items = page.get('Items')
        logger.debug(f"현재 총 제품 수 : {page.get('Count')}")
        count += page.get('Count')
        if items:
            #TODO 여기 for문은 좀더 효율적으로 돌릴 수 있을 거 같은데 
            for i in items:
                item = aws_manager.dynamodb_manager._convert_dynamodb_item_to_python(i)
                logger.info(f"main_category : {item.get('main_category')} , sub_category : {item.get('sub_category')} , 제품 id : {item.get('product_id')} ")
                main_category = item.get('main_category')
                sub_category = item.get('sub_category')
                product_id = item.get('product_id')
                
                #TODO : 하의 일때 model 처리 필요
                if main_category == "TOP":
                    category = "상의"
                else:
                    category = "하의"
                images = aws_manager.get_product_images_from_paginator(item)
                logger.debug(f"이미지 정보 리스트 : {images}")   
                download_images_sync(images)
                base64_data_for_llm = parsing_data_for_llm(images, target_size=224)
                
                
                result = fashion_caption_generator.invoke(base64_data_for_llm , category=category)
                
                deep_caption = result.get("deep_caption").model_dump()
                color_images = result.get("color_images").model_dump()
                text_images = result.get("text_images").model_dump_json()
                print(deep_caption)
                print(color_images)
                print(text_images)
                sys.exit()
                
                
                # dynamodb 반영 (caption PENDING => COMPLETED)
                # aws_manager.dynamodb_manager.update_caption_result(sub_category, product_id, "COMPLETED")
        
                #mongodb 로 부터 데이터 가져오기 _id로 접근 
                # doc = fashion_repository.find_by_id(product_id)
              

                # #TODO : mongoatlas에 저장할 필드만 가져오고 ,  # 최종 데이터 분리 (denormalize 및 대표 이미지 색상 필드 추가 및 product_id + 색상명으로 유니크 키 생성)
            
                # # 최종 데이터 저장 mongodb atlas 저장 => 이후에 벡터 필드에 대한 임베딩 벡터 추가 
                # '''
                # - product_id , 
                # - 
                
                # '''

                
