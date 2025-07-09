import pytest
from unittest.mock import Mock, patch, MagicMock
from aws.aws_manager import AWSManager
from aws.product_models import ImageManager, ProductManager
from pathlib import Path
import json
import logging
from tests.conftest import mock_open_config

# Set up logging for test debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAWSManagerWithMocks:
    """Mock을 사용한 AWSManager 클래스 테스트"""
    
    
    def test_get_product_images_from_paginator_success(self, mock_aws_manager_initialized, sample_dynamodb_item):
        """get_product_images_from_paginator 성공 테스트"""
        manager = mock_aws_manager_initialized
        
        images = manager.get_product_images_from_paginator(sample_dynamodb_item)
        # DynamoDB 변환 함수가 호출되었는지 확인
        manager.dynamodb_manager._convert_dynamodb_item_to_python.assert_called_once_with(sample_dynamodb_item)
        
        # S3 presigned URL 생성이 호출되었는지 확인
        assert manager.s3_manager.generate_presigned_url.call_count == len(images)
        
        logger.info("get_product_images_from_paginator success test passed")
    
    def test_parse_representative_assets_success(self, mock_aws_manager_initialized):
        """_parse_representative_assets 성공 테스트"""
        manager = mock_aws_manager_initialized
        
        representative_assets = {
            'front': 'images/front/test_front.jpg',
            'back': 'images/back/test_back.jpg',
            'model': 'images/model/test_model.jpg',
            'color_variant': ['images/color1/test_color1.jpg', 'images/color2/test_color2.jpg']
        }
        
        success, images = manager._parse_representative_assets(representative_assets)
        
        assert success is True
        assert isinstance(images, list)
        assert len(images) == 5  # front, back, model + 2 color variants
        
        # 각 이미지 타입 확인
        image_types = [img.type for img in images]
        assert 'front' in image_types
        assert 'back' in image_types
        assert 'model' in image_types
        assert image_types.count('color_variant') == 2
        
        logger.info("parse_representative_assets success test passed")
    
    def test_parse_representative_assets_invalid_format(self, mock_aws_manager_initialized):
        """_parse_representative_assets 잘못된 형식 테스트"""
        manager = mock_aws_manager_initialized
        
        # 잘못된 형식의 데이터
        representative_assets = {
            'front': 123,  # 문자열이 아닌 숫자
            'back': None,  # None 값
            'invalid_type': 'some_image.jpg'  # 지원하지 않는 타입
        }
        
        success, images = manager._parse_representative_assets(representative_assets)
        
        assert success is False
        logger.info("parse_representative_assets invalid format test passed")

    
    def test_parse_text_image_empty_list(self, mock_aws_manager_initialized):
        """_parse_text_image 빈 리스트 테스트"""
        manager = mock_aws_manager_initialized
        
        text_images = []
        
        success, images = manager._parse_text_image(text_images)
        
        assert success is True
        assert isinstance(images, list)
        assert len(images) == 0
        
        logger.info("parse_text_image empty list test passed")
    
    
    def test_parse_data_for_caption_both_fail(self, mock_aws_manager_initialized):
        """_parse_data_for_caption 모든 파싱 실패 테스트"""
        manager = mock_aws_manager_initialized
        
        test_cases = [
        # 완전히 잘못된 형식
            {'invalid': 123},
            
            # 필수 필드 누락
            {'front': 'url.jpg'},  # back, model 누락
            
            # 잘못된 값 타입
            {'front': 123, 'back': 456, 'model': 789},
            
            # 빈 값
            {'front': '', 'back': '', 'model': ''}
        ]
    
        for invalid_data in test_cases:
            success, images = manager._parse_representative_assets(invalid_data)
            assert success is False, f"Should fail for invalid data: {invalid_data} , success : {success}"

        
        logger.info("parse_data_for_caption both fail test passed")
