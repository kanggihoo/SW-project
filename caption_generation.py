import logging
import sys
from typing import Any
from aws.aws_manager import AWSManager
from processing.image_processor import download_images_sync , parsing_data_for_llm 
from caption.models.product import ImageManager, ProductManager, Base64DataForLLM
from caption.fashion_caption_generator import FashionCaptionGenerator
from db.repository.fashion import FashionRepository
from db.config.database import DatabaseManager
from db import create_fashion_repo
from db.config import Config
from utils import setup_logger
from dotenv import load_dotenv
from dataclasses import dataclass
import asyncio

#TODO : 실패한 제품 id에 대한 처리 필요 (log 파일 저장 )
logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s : %(filename)s - %(lineno)d' , datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


@dataclass
class CaptionDependency:
    '''캡션 생성에 필요한 의존성 관리 클래스'''
    asw_manager : AWSManager
    fashion_repository_local : FashionRepository
    fashion_caption_generator : FashionCaptionGenerator
    target_size : int

@dataclass
class StatisticManager:
    total_count : int = 0
    success_count : int = 0 
    fail_count : int = 0
    
    def add_success(self):
        self.success_count += 1
    
    def add_fail(self):
        self.fail_count += 1
    
    def add_total(self , count:int):
        self.total_count += count
    
def parsing_caption_result(result:dict , representative_assets:Any):
    '''캡션 생성 결과 파싱 함수'''
    
    deep_caption = result.get("deep_caption").model_dump()
    color_images = result.get("color_images").model_dump()
    text_images = result.get("text_images").model_dump_json() if result.get("text_images") else None
    
    return {
        "caption_info": {
            "caption_status": "COMPLETED",
            "deep_caption": deep_caption,
            "color_images": color_images,
            "text_images": text_images,
        },
        "representative_assets": representative_assets
    }
    
async def process_single_item(item:dict, dep:CaptionDependency):
    try:
        converted_item = dep.asw_manager.dynamodb_manager._convert_dynamodb_item_to_python(item)
        main_category = converted_item.get('main_category')
        sub_category = converted_item.get('sub_category')
        product_id = converted_item.get('product_id')
        representative_assets = converted_item.get('representative_assets')
        
        logger.info(f"Processing - main_category : {main_category} , sub_category : {sub_category} , 제품 id : {product_id} ")

        category = "상의" if main_category.lower() == "top" else "하의"
        images = dep.asw_manager.get_product_images_from_paginator(converted_item)

        # 이미지 다운로드 
        await download_images_sync(images)

        base64_data_for_llm = await asyncio.to_thread(
            parsing_data_for_llm,
            images,
            target_size=dep.target_size
        )

        # mongodb 에서 product_id 로 제품 조회
        doc = dep.fashion_repository_local.find_by_id(product_id)
        has_size = True if doc.get("size_detail_info") else False

        # 캡션 생성
        result = await dep.fashion_caption_generator.ainvoke(base64_data_for_llm , category=category , has_size=has_size)

        # 결과 구성 및 저장
        caption_result = parsing_caption_result(result, representative_assets)

        # dynamodb 반영 (caption PENDING => COMPLETED)
        # dep.asw_manager.dynamodb_manager.update_caption_result(sub_category, product_id, "COMPLETED")

        # local mongodb 에 저장 및 data_status 업데이트 (CA_COMP)
        # dep.fashion_repository_local.update_by_id(product_id, caption_result)
        
        logger.debug(f"caption generation completed - main_category : {main_category} , sub_category : {sub_category} , 제품 id : {product_id} ")
        return True
        
    except Exception as e:
        logger.error(f"Error caption generation: {e}")
        # local mongodb 에 저장 및 data_status 업데이트 (AWS_UPS) -> 업로드는 되어 있는 상태 
        return False
    

async def process_page_items(items:list[dict], dep:CaptionDependency)->tuple[int,int]:
    '''페이지 단위 처리 함수'''
    success_count = 0
    fail_count = 0
    logger.info(f"Processing {len(items)} items concurrently...")

    tasks = [process_single_item(item, dep) for item in items]
    results = await asyncio.gather(*tasks , return_exceptions=True)

    for result in results:
        if result:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count
    
async def process_all_pages(paginator , deps:CaptionDependency):
    '''모든 페이지 처리 함수'''
    statistic = StatisticManager()
    
    for page in paginator:
        items = page.get('Items')
        count = page.get('Count')

        logger.info(f"Processing {count} items concurrently...")
        statistic.add_total(count)

        if items:
            success_count , fail_count = await process_page_items(items , deps)
            statistic.add_success(success_count)
            statistic.add_fail(fail_count)

    return statistic

def setup_dependencies():
    try:
        aws_manager = AWSManager()    
        # dynamodb 의 pagesize 조정 필요. 
        fashion_repository_local = create_fashion_repo(use_atlas=False)
        fashion_caption_generator = FashionCaptionGenerator()
        return CaptionDependency(aws_manager, fashion_repository_local, fashion_caption_generator, target_size=512)
    except Exception as e:
        logger.error(f"Error setting up dependencies: {e}")
        raise e

async def main():
    load_dotenv()
    dep = setup_dependencies()
    try:
        # pagenator 지정 
        pagenator = dep.asw_manager.dynamodb_manager.get_product_pagenator(partition={"key":"sub_category_curation_status","value":"3002#COMPLETED","type":"S"},GSI_NAME = "CurationStatus-SubCategory-GSI")

        # 모든 페이지 처리
        statistic = await process_all_pages(pagenator , dep)

        logger.info(f"총 제품 수 : {statistic.total_count}")
        logger.info(f"성공 제품 수 : {statistic.success_count}")
        logger.info(f"실패 제품 수 : {statistic.fail_count}")
    except Exception as e:
        logger.error(f"Error caption pagenator 지정시 오류 발생 : {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(main())
    # load_dotenv()
    # db_config = Config()
    # aws_manager = AWSManager()    
    # fashion_repository_local = create_fashion_repo(use_atlas=False)

    # fashion_caption_generator = FashionCaptionGenerator()
    # pagenator = aws_manager.dynamodb_manager.get_product_pagenator(partition={"key":"sub_category_curation_status","value":"3002#COMPLETED","type":"S"},GSI_NAME = "CurationStatus-SubCategory-GSI")
    # total_count = 0
    # success_count = 0
    # fail_count = 0
    # for page in pagenator:
    #     items = page.get('Items')
    #     logger.debug(f"현재 총 제품 수 : {page.get('Count')}")
    #     total_count += page.get('Count')
    #     if items:
    #         #TODO 여기 for문은 좀더 효율적으로 돌릴 수 있을 거 같은데(어차피 dynamodb에서 paginator로 가져오기 때문에 20개정도 동시에 다 돌리면 되지 않을까?) 
    #         for i in items:
    #             try:
    #                 item = aws_manager.dynamodb_manager._convert_dynamodb_item_to_python(i)
    #                 logger.info(f"main_category : {item.get('main_category')} , sub_category : {item.get('sub_category')} , 제품 id : {item.get('product_id')} ")
    #                 main_category = item.get('main_category')
    #                 sub_category = item.get('sub_category')
    #                 product_id = item.get('product_id')
    #                 representative_assets = item.get('representative_assets')
                    
    #                 category = "상의" if main_category.lower() == "top" else "하의"
    #                 images = aws_manager.get_product_images_from_paginator(item)
    #                 # logger.info(f"이미지 정보 리스트 : {images}")  
    #                 logger.info(f"category : {category}")
    #                 download_images_sync(images)
    #                 base64_data_for_llm = parsing_data_for_llm(images, target_size=512)
    #                 #해당 제품이 사이즈 정보 있는지 확인 (local mongodb 에서 확인, _id로 접근)
    #                 doc = fashion_repository_local.find_by_id(product_id)

    #                 has_size = True if doc.get("size_detail_info") else False
    #                 result = fashion_caption_generator.invoke(base64_data_for_llm , category=category , has_size=has_size)
                    
    #                 deep_caption = result.get("deep_caption").model_dump()
    #                 color_images = result.get("color_images").model_dump()
    #                 text_images = result.get("text_images").model_dump_json() if result.get("text_images") else None

    #                 caption_result = {
    #                     "caption_info": {
    #                         "caption_status": "COMPLETED",
    #                         "deep_caption": deep_caption,
    #                         "color_images": color_images,
    #                         "text_images": text_images,
    #                     },
    #                     "representative_assets": representative_assets
    #                 }
                    
    #                 #dynamodb 반영 (caption PENDING => COMPLETED)
    #                 # aws_manager.dynamodb_manager.update_caption_result(sub_category, product_id, "COMPLETED")
            
    #                 #local mongodb 에 저장 
    #                 fashion_repository_local.update_by_id(product_id , caption_result)
    #                 success_count+=1
    #                 sys.exit()
    
    #             except Exception as e:
    #                 logger.error(f"Error caption generation: {e}")
    #                 fail_count+=1
    #                 sys.exit()
    # logger.info("caption generation completed")
    # logger.info(f"총 제품 수 : {total_count}")
    # logger.info(f"성공 제품 수 : {success_count}")
    # logger.info(f"실패 제품 수 : {fail_count}")

              
