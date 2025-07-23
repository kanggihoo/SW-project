from pathlib import Path
from typing import Annotated, Iterator, Any
import logging

from .config import Config
from .s3 import S3Manager
from .dynamodb import DynamoDBManager
from caption.models.product import ImageManager, ProductManager

logger = logging.getLogger(__name__)
   

class AWSManager:
    def __init__(self) -> None:
        self.config = Config()
        self.s3_manager = None 
        self.dynamodb_manager = None
        self._initialize_services()
    # =============================================================================
    # 초기화 관련 함수
    # =============================================================================
        
    def _initialize_services(self) -> None:
        try:
            #s3 초기화
            s3_config = self.config.get_s3_config()
            self.s3_manager = S3Manager(
                region_name=s3_config.get('region_name'),
                bucket_name=s3_config.get('bucket_name')
            )
            

            # dynamodb 초기화
            dynamodb_config = self.config.get_dynamodb_config()
            self.dynamodb_manager = DynamoDBManager(
                region_name=dynamodb_config.get('region_name'),
                table_name=dynamodb_config.get('table_name'),
                config=dynamodb_config
            )

            # 연결 테스트 
            self._verify_connection()
            logger.info("AWS 서비스 초기화 완료")

        except Exception as e:
            logger.error(f"AWS 서비스 초기화 실패: {e}")
            raise 
    
    def _verify_connection(self):
        connection_status = self._test_connection()

        if not connection_status['success']:
            error_msg = "AWS 연결 초기화 실패:\n"
            if not connection_status['s3']:
                error_msg += f"- S3 연결 실패: {self.s3_manager.bucket_name}\n"
            if not connection_status['dynamodb']:
                error_msg += f"- DynamoDB 연결 실패: {self.dynamodb_manager.table_name}\n"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

    def _test_connection(self):
        # 연결 테스트 및 상세한 에러 처리
        s3_success = self.s3_manager.test_connection()
        dynamodb_success = self.dynamodb_manager.test_connection()
        
        return {
            "success": all([s3_success, dynamodb_success]),
            "s3": s3_success,
            "dynamodb": dynamodb_success
        }
    # def _initialize_cache(self):
    #     self.HOME_DIR = Path.home()
    #     self.CACHE_DIR = Path(config["DEFAULT_CACHE_DIR"])
    #     self.cache_manager = CacheManager(s3_manager=self.s3_manager, cache_dir=str(self.CACHE_DIR))
        
    # =============================================================================
    # 주요 함수
    # =============================================================================
    
    def get_product_images_from_paginator(self, item:dict) -> list[ImageManager]:
        """dynanodb의 페이지네이터를 통해 조회한 1개의 데이터를 파싱하여 S3 에서 다운로드 가능한 url 반환
        Args:
            item (dict): dynamodb 페이지네이터를 통해 조회한 1개의 데이터(dynamodb 타입 변환 후)

        Returns:
            list[ImageManager]: 이미지 정보 리스트
        """
       
        # converted_item = self.dynamodb_manager._convert_dynamodb_item_to_python(item)
        success, images = self._parse_data_for_caption(item)
        if not success:
            logger.error(f"데이터 파싱간 오류 발생. product_id : {item['product_id']} , 데이터 : {item}")
        
        product_model = ProductManager(
            main_category=item['main_category'],
            product_id=item['product_id'],
            sub_category=item['sub_category'],
            images=images
        )
        
        # s3_key 를 다운받기 위한 url 생성
        for image in product_model.images:
            image.s3_url = self.s3_manager.generate_presigned_url(key=image.s3_key)
            
        return product_model.images 
        
        
    # =============================================================================
    # 유틸리티 함수
    # =============================================================================
    def close_connection(self):
        if self.s3_manager:
            self.s3_manager.close_connection()
        if self.dynamodb_manager:
            self.dynamodb_manager.close_connection()
        self.aws_manager = None
        logger.info("AWS 서비스 연결 종료")

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
            value = "text/" + value
            images.append(ImageManager(folder_path=value, type="text"))
        return True , images
    
    def _parse_data_for_caption(self,data:dict) -> tuple[bool, list[ImageManager]]:
        success1 , images1 = self._parse_representative_assets(data['representative_assets'])
        success2 , images2 = self._parse_text_image(data['text'])
        if not success1 and not success2:
            return False , []
        return True , images1 + images2
        
    

    
    
    
        
        
        