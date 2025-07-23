import pytest
from unittest.mock import Mock, patch, MagicMock
from aws.dynamodb import DynamoDBManager
from pathlib import Path

import logging
from botocore.exceptions import ClientError
from tests.conftest import mock_open_config

# Set up logging for test debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# class TestDynamoDBManagerWithMocks:
#     """Mock을 사용한 DynamoDBManager 클래스 테스트"""

    
#     def test_get_item_success(self, mock_dynamodb_manager_initialized):
#         """get_item 성공 테스트"""
#         manager = mock_dynamodb_manager_initialized
        
#         result = manager.get_item(sub_category=1005, product_id="test_product_123")        
#         # get_item이 올바른 키로 호출되었는지 확인
#         manager.client.get_item.assert_called_once()
#         call_args = manager.client.get_item.call_args
#         assert call_args[1]['TableName'] == "TestProductAssets"
#         assert 'Key' in call_args[1]
        
    
#     def test_get_product_paginator_success(self, mock_dynamodb_manager_initialized):
#         """get_product_pagenator 성공 테스트"""
#         manager = mock_dynamodb_manager_initialized
        
#         iterator = manager.get_product_pagenator(
#             sub_category=1005,
#             condition={'curation_status': 'COMPLETED'}
#         )
        
#         manager.client.get_paginator.assert_called_once_with('query')
        
#         logger.info("get_product_paginator success test passed")
    
#     def test_get_product_paginator_without_condition(self, mock_dynamodb_manager_initialized):
#         """get_product_pagenator 조건 없이 테스트"""
#         manager = mock_dynamodb_manager_initialized
        
#         iterator = manager.get_product_pagenator(sub_category=1005)
        
#         assert iterator is not None
#         manager.client.get_paginator.assert_called_once_with('query')
        
#         logger.info("get_product_paginator without condition test passed")
    
    
#     def test_python_to_dynamodb_conversion(self, mock_dynamodb_manager_initialized):
#         """Python to DynamoDB 변환 테스트"""
#         manager = mock_dynamodb_manager_initialized
        
#         test_data = {
#             'numbers': [1, 2, 3],  # Python list of ints
#             'metadata': {  # Python nested dict
#                 'created_at': '2024-03-20',
#                 'is_active': True
#             },
#             'tags': {'tag1', 'tag2'},  # Python set
#         }
    
#         converted = manager._convert_python_to_dynamodb(test_data)
        
#         # 각 Python 타입이 올바른 DynamoDB 타입으로 변환되었는지
#         assert converted['numbers']['L'][0]['N'] == '1'  # list -> {'L': [{'N': '1'}, ...]}
#         assert converted['metadata']['M']['is_active']['BOOL'] is True  # bool -> {'BOOL': true}
#         # set은 순서가 보장되지 않으므로, 변환 결과의 SS 값은 정렬해서 비교
#         assert sorted(converted['tags']['SS']) == sorted(['tag1', 'tag2'])  # set -> {'SS': [...]}
        
#         logger.info("Python to DynamoDB conversion test passed")
    
#     def test_dynamodb_to_python_conversion(self, mock_dynamodb_manager_initialized):
#         """DynamoDB to Python 변환 테스트"""
#         manager = mock_dynamodb_manager_initialized
        
#         dynamodb_data = {
#             'sub_category': {'N': '1005'},
#             'product_id': {'S': 'test_product_123'},
#             'curation_status': {'S': 'COMPLETED'},
#             'representative_assets': {
#                 'M': {
#                     'front': {'S': 'front_image.jpg'},
#                     'back': {'S': 'back_image.jpg'}
#                 }
#             },
#             'detail': {
#                 'L': [
#                     {'S': 'detail1'},
#                     {'S': 'detail2'}
#                 ]
#             },
#             'is_active': {'BOOL': True},
#             'price': {'N': '29.99'},
#             'tags': {'SS': ['tag1', 'tag2']},
#             'metadata': {'NULL': True}
#         }
        
#         converted = manager._convert_dynamodb_item_to_python(dynamodb_data)
        
#         assert isinstance(converted, dict)
#         assert converted['sub_category'] == 1005
#         assert converted['product_id'] == 'test_product_123'
#         assert converted['curation_status'] == 'COMPLETED'
#         assert isinstance(converted['representative_assets'], dict)
#         assert converted['representative_assets']['front'] == 'front_image.jpg'
#         assert isinstance(converted['detail'], list)
#         assert len(converted['detail']) == 2
#         assert converted['is_active'] is True
#         assert converted['price'] == 29.99
#         assert converted['tags'] == ['tag1', 'tag2']
#         assert converted['metadata'] is None
        
#         logger.info("DynamoDB to Python conversion test passed")
    
#     def test_load_config_success(self, aws_mock_config):
#         """_load_config 성공 테스트"""
#         with patch('pathlib.Path.exists', return_value=True), \
#              patch('builtins.open', mock_open_config(aws_mock_config)):
            
#             manager = DynamoDBManager.__new__(DynamoDBManager)
#             config = manager._load_config()
            
#             assert config == aws_mock_config
#             assert 'aws' in config
#             assert 'dynamodb' in config
            
#             logger.info("Load config success test passed")
    
#     def test_load_config_file_not_found(self):
#         """_load_config 파일 없음 테스트"""
#         with patch('pathlib.Path.exists', return_value=False):
#             manager = DynamoDBManager.__new__(DynamoDBManager)
            
#             with pytest.raises(FileNotFoundError):
#                 manager._load_config()
            
#             logger.info("Load config file not found test passed")
    

from aws.config import Config
@pytest.fixture
def dynamodb():
    return DynamoDBManager(
        region_name="ap-northeast-2",
        table_name="ProductAssets",
        config=Config().get_dynamodb_config()
    )

class TestDynamoDBManager:
    def test_get_product_pagenator(self, dynamodb):
        logger.info("sd")
        print("sdsds")
        pagenator = dynamodb.get_product_pagenator(
            partition={"key":"curation_status","value":"COMPLETED","type":"S"},
            GSI_NAME = "CurationStatus-RecommendationOrder-GSI"
        )
        for page in pagenator:
            logger.info(page)
            for item in page.get("Items"):
                print(item)

        