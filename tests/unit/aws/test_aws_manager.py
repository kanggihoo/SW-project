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
        
        assert images is not None
        assert isinstance(images, list)
        assert len(images) > 0
        
        # ImageManager 객체들이 올바르게 생성되었는지 확인
        for image in images:
            assert isinstance(image, ImageManager)
            assert hasattr(image, 's3_url')
            assert image.s3_url == "https://test-bucket.s3.amazonaws.com/test-image.jpg?presigned=true"
        
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
    
    def test_parse_text_image_success(self, mock_aws_manager_initialized):
        """_parse_text_image 성공 테스트"""
        manager = mock_aws_manager_initialized
        
        text_images = ['images/text/text1.jpg', 'images/text/text2.jpg', 'images/text/text3.jpg']
        
        success, images = manager._parse_text_image(text_images)
        
        assert success is True
        assert isinstance(images, list)
        assert len(images) == 3
        
        # 모든 이미지가 'text' 타입인지 확인
        for image in images:
            assert isinstance(image, ImageManager)
            assert image.type == 'text'
        
        logger.info("parse_text_image success test passed")
    
    def test_parse_text_image_empty_list(self, mock_aws_manager_initialized):
        """_parse_text_image 빈 리스트 테스트"""
        manager = mock_aws_manager_initialized
        
        text_images = []
        
        success, images = manager._parse_text_image(text_images)
        
        assert success is True
        assert isinstance(images, list)
        assert len(images) == 0
        
        logger.info("parse_text_image empty list test passed")
    
    def test_parse_data_for_caption_success(self, mock_aws_manager_initialized, sample_converted_item):
        """_parse_data_for_caption 성공 테스트"""
        manager = mock_aws_manager_initialized
        
        success, images = manager._parse_data_for_caption(sample_converted_item)
        
        assert success is True
        assert isinstance(images, list)
        assert len(images) > 0  # representative + text images
        
        # 이미지 타입들 확인
        image_types = [img.type for img in images]
        assert 'front' in image_types
        assert 'back' in image_types
        assert 'text' in image_types
        
        logger.info("parse_data_for_caption success test passed")
    
    def test_parse_data_for_caption_both_fail(self, mock_aws_manager_initialized):
        """_parse_data_for_caption 모든 파싱 실패 테스트"""
        manager = mock_aws_manager_initialized
        
        # representative_assets와 text 모두 잘못된 형식
        data = {
            'representative_assets': {
                'invalid': 123  # 잘못된 형식
            },
            'text': []  # 빈 리스트는 성공하므로, representative_assets만 실패해도 전체는 성공
        }
        
        # representative_assets 파싱을 실패하도록 Mock 설정
        with patch.object(manager, '_parse_representative_assets', return_value=(False, [])), \
             patch.object(manager, '_parse_text_image', return_value=(False, [])):
            
            success, images = manager._parse_data_for_caption(data)
            
            assert success is False
            assert images == []
        
        logger.info("parse_data_for_caption both fail test passed")
    
    def test_load_config_success(self, aws_mock_config):
        """_load_config 성공 테스트"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_config(aws_mock_config)):
            
            manager = AWSManager.__new__(AWSManager)  # __init__ 호출 없이 인스턴스 생성
            config = manager._load_config()
            
            assert config == aws_mock_config
            assert 'aws' in config
            assert 's3' in config
            assert 'dynamodb' in config
            
            logger.info("Load config success test passed")
    
    def test_load_config_file_not_found(self):
        """_load_config 파일 없음 테스트"""
        with patch('pathlib.Path.exists', return_value=False):
            manager = AWSManager.__new__(AWSManager)  # __init__ 호출 없이 인스턴스 생성
            
            with pytest.raises(FileNotFoundError) as exc_info:
                manager._load_config()
            
            assert "설정 파일을 찾을 수 없습니다" in str(exc_info.value)
            logger.info("Load config file not found test passed")
    
    def test_managers_properly_initialized(self, aws_mock_config):
        """S3Manager와 DynamoDBManager가 올바른 파라미터로 초기화되는지 테스트"""
        # 실제 초기화 과정을 다시 실행해서 파라미터 확인
        with patch('aws.aws_manager.S3Manager') as mock_s3_class, \
             patch('aws.aws_manager.DynamoDBManager') as mock_dynamodb_class, \
             patch.object(AWSManager, '_load_config', return_value=aws_mock_config):
            
            # 연결 테스트 성공하도록 설정
            mock_s3_instance = Mock()
            mock_s3_instance.test_connection.return_value = True
            mock_s3_class.return_value = mock_s3_instance
            
            mock_dynamodb_instance = Mock()
            mock_dynamodb_instance.test_connection.return_value = True
            mock_dynamodb_class.return_value = mock_dynamodb_instance
            
            # 새로운 AWSManager 생성
            new_manager = AWSManager()
            
            # S3Manager가 올바른 파라미터로 호출되었는지 확인
            mock_s3_class.assert_called_once_with(
                region_name="ap-northeast-2",
                bucket_name="test-sw-fashion-image-data"
            )
            
            # DynamoDBManager가 올바른 파라미터로 호출되었는지 확인
            mock_dynamodb_class.assert_called_once_with(
                region_name="ap-northeast-2",
                table_name="TestProductAssets"
            )
        
        logger.info("Managers properly initialized test passed")
