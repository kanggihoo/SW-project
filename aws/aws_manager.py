from pathlib import Path
import json
from typing import Annotated, Iterator, Any
from dataclasses import dataclass, field
from pydantic import Field
import logging

from .config import Config
from .s3 import S3Manager
from .dynamodb import DynamoDBManager
from .product_models import ImageManager, ProductManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
config = Config()
   

class AWSManager:
    def __init__(self) -> None:
        self._initialize_aws_services()
        # self._initialize_cache()
    
    # =============================================================================
    # 초기화 관련 함수
    # =============================================================================
        
    def _initialize_aws_services(self) -> None:
        config = self._load_config()
        self.region_name = config.get('aws', {}).get('region_name', 'ap-northeast-2')
        self.bucket_name = config.get('s3', {}).get('bucket_name', 'sw-fashion-image-data')
        self.table_name = config.get('dynamodb', {}).get('table_name', 'ProductAssets')
        
        # S3와 DynamoDB 매니저 초기화
        self.s3_manager = S3Manager(region_name=self.region_name, bucket_name=self.bucket_name)
        self.dynamodb_manager = DynamoDBManager(region_name=self.region_name, table_name=self.table_name)
        
        # 연결 테스트 및 상세한 에러 처리
        connection_status = self.test_connection()
        if connection_status['success']:
            logger.info("AWS S3 , Dynamodb 연결 성공")
        else:
            error_msg = "AWS 연결 초기화 실패:\n"
            if not connection_status['s3']:
                error_msg += f"- S3 연결 실패: {self.bucket_name}\n"
            if not connection_status['dynamodb']:
                error_msg += f"- DynamoDB 연결 실패: {self.table_name}\n"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    # def _initialize_cache(self):
    #     self.HOME_DIR = Path.home()
        # self.CACHE_DIR = Path(config["DEFAULT_CACHE_DIR"])
        # self.cache_manager = CacheManager(s3_manager=self.s3_manager, cache_dir=str(self.CACHE_DIR))
        

    def test_connection(self) -> dict:
        """
        S3와 DynamoDB 연결 상태를 개별적으로 확인
        
        Returns:
            dict: {'success': bool, 's3': bool, 'dynamodb': bool}
        """
        s3_success = self.s3_manager.test_connection()
        dynamodb_success = self.dynamodb_manager.test_connection()
        
        return {
            'success': all([s3_success, dynamodb_success]),
            's3': s3_success,
            'dynamodb': dynamodb_success
        }
    # =============================================================================
    # 주요 함수
    # =============================================================================
    
    def get_product_images_from_paginator(self, item:dict) -> list[ImageManager]:
        """dynanodb의 페이지네이터를 통해 조회한 1개의 데이터를 파싱하여 S3 에서 다운로드 가능한 url 반환
        Args:
            item (dict): dynamodb 페이지네이터를 통해 조회한 1개의 데이터

        Returns:
            list[ImageManager]: 이미지 정보 리스트
        """
       
        converted_item = self.dynamodb_manager._convert_dynamodb_item_to_python(item)
        success, images = self._parse_data_for_caption(converted_item)
        if not success:
            logger.error(f"데이터 파싱간 오류 발생. product_id : {converted_item['product_id']} , 데이터 : {converted_item}")
        
        product_model = ProductManager(
            main_category=converted_item['main_category'],
            product_id=converted_item['product_id'],
            sub_category=converted_item['sub_category'],
            images=images
        )
        
        # s3_key 를 다운받기 위한 url 생성
        for image in product_model.images:
            image.s3_url = self.s3_manager.generate_presigned_url(key=image.s3_key)
            
        return product_model.images 
        
        
    # =============================================================================
    # 유틸리티 함수
    # =============================================================================
    def _load_config(self) -> dict:
        config_path = Path(__file__).parent / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config

    
    def _parse_representative_assets(self, representative_assets:dict) -> tuple[bool, list[ImageManager]]:
        images = []
        success = True
        try:
            assert len(set(key for key in representative_assets.keys() if key in ["model", "front", "back", "color_variant"]))==4, "representative_assets 형식이 올바르지 않습니다."
            for key, value in representative_assets.items():
                
                if isinstance(value, list) and len(value):
                    for img in value:
                        images.append(ImageManager(folder_path=img, type=key))
                elif isinstance(value, str) and key in ["model", "front", "back"]:
                    images.append(ImageManager(folder_path=value, type=key))
                else:
                    logger.error(f"이미지 파일 형식이 올바르지 않습니다. key : {key} , value : {value}")
                    success = False
                    break
        except Exception as e:
            logger.error(f"이미지 파싱 중 오류 발생 : {e}")
            success = False
        

        return success, images
    
    def _parse_text_image(self, text:list[str]) -> tuple[bool, list[ImageManager]]:
        images = []
        for value in text:
            images.append(ImageManager(folder_path=value, type="text"))
        return True , images
    
    def _parse_data_for_caption(self,data:dict) -> tuple[bool, list[ImageManager]]:
        success1 , images1 = self._parse_representative_assets(data['representative_assets'])
        success2 , images2 = self._parse_text_image(data['text'])
        if not success1 and not success2:
            return False , []
        return True , images1 + images2
        
    
if __name__ == "__main__":
    aws_manager = AWSManager()
    paginator = aws_manager.dynamodb_manager.get_product_pagenator(sub_category=1005, condition={"curation_status": "COMPLETED"})
    if paginator is not None:
        for page in paginator:
            items = page.get('Items')
            logger.info(f"현재 총 제품 수 : {page.get('Count')}")
            if items:
                for item in items:
                    images = aws_manager.get_product_images_from_paginator(item)
                    logger.info(f"이미지 정보 리스트 : {images}")
                    break
            break
            
    
    
    
        
        
        