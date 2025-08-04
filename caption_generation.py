import logging
import sys
from typing import Any
from aws.aws_manager import AWSManager
from processing.image_processor import download_images , parsing_data_for_llm 
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
class ImageSize:
    deep_caption_size : int 
    color_caption_size : int
    text_caption_size : int

@dataclass
class CaptionDependency:
    '''캡션 생성에 필요한 의존성 관리 클래스'''
    asw_manager : AWSManager
    fashion_repository_local : FashionRepository
    fashion_caption_generator : FashionCaptionGenerator
    size : ImageSize 


@dataclass
class StatisticManager:
    total_count : int = 0
    success_count : int = 0 
    fail_count : int = 0
    
    def add_success(self, count:int=0):
        self.success_count += count
    
    def add_fail(self, count:int=0):
        self.fail_count += count
    
    def add_total(self , count:int):
        self.total_count += count

def setup_dependencies(page_size:int|None=None , deep_caption_size:int=512 , color_caption_size:int=224 , text_caption_size:int=512):
    try:
        aws_manager = AWSManager()    
        # dynamodb 의 pagesize 조정 필요.
        if page_size:
            aws_manager.dynamodb_manager.page_size = page_size
        fashion_repository_local = create_fashion_repo(use_atlas=False)
        fashion_caption_generator = FashionCaptionGenerator()
        size = ImageSize(deep_caption_size=deep_caption_size, color_caption_size=color_caption_size, text_caption_size=text_caption_size)
        return CaptionDependency(aws_manager, fashion_repository_local, fashion_caption_generator, size)
    except Exception as e:
        logger.error(f"Error setting up dependencies: {e}")
        raise e
    
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
        await download_images(images)

        # 다운로드 된 이미지 파싱 
        base64_data_for_llm = await asyncio.to_thread(
            parsing_data_for_llm,
            images,
            image_sizes=dep.size 
        )

        # mongodb 에서 product_id 로 제품 조회(dynamodb 에는 있지만 mongodb에는 없는 경우 있는지 체크할 필요가?)
        doc = dep.fashion_repository_local.find_by_id(product_id)
        has_size = True if doc.get("size_detail_info") else False

        # 캡션 생성(비동기)
        result = await dep.fashion_caption_generator.ainvoke(base64_data_for_llm , category=category , has_size=has_size)

        # 결과 구성 및 저장
        caption_result = parsing_caption_result(result, representative_assets)

        #TODO : dynamodb, mongodb(local) 반영 
        # dynamodb 반영 (caption PENDING => COMPLETED)
        dep.asw_manager.dynamodb_manager.update_caption_result(sub_category, product_id, "COMPLETED")

        # local mongodb 에 저장 및 data_status 업데이트 (CA_COMP)
        caption_result["data_status"] = "CA_COMP"
        dep.fashion_repository_local.update_by_id(product_id, caption_result)
        
        logger.debug(f"caption generation completed - main_category : {main_category} , sub_category : {sub_category} , 제품 id : {product_id} ")
        return True
        
    except Exception as e:
        logger.error(f"Error caption generation: {e}")
        # local mongodb 에 저장 및 data_status 업데이트 (AWS_UPS) -> 업로드는 되어 있는 상태 
        # dep.fashion_repository_local.update_by_id(product_id, {"data_status": "AWS_UPS"})
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

            # 테스트 용도 break
            break

    return statistic

async def main():
    load_dotenv()
    dep = setup_dependencies(page_size=2)
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



   