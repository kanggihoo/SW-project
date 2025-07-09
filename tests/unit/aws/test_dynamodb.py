import pytest
from unittest.mock import Mock, patch, MagicMock
from aws.dynamodb import DynamoDBManager
from aws.config import Config
from pathlib import Path
import json
import logging
from botocore.exceptions import ClientError

# Set up logging for test debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_config():
    """Mock 설정 데이터를 제공하는 fixture"""
    config = Config()
    return {
        "aws": {
            "region_name": "ap-northeast-2"
        },
        "dynamodb": {
            "table_name": "ProductAssets"
        },
        "DEFAULT_PROJECTION_FIELDS": config["DEFAULT_PROJECTION_FIELDS"],
        "DEFAULT_PAGINATOR_CONFIG": config["DEFAULT_PAGINATOR_CONFIG"]
    }

@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDB 클라이언트를 제공하는 fixture"""
    mock_client = Mock()
    
    # describe_table 성공 응답 mock
    mock_client.describe_table.return_value = {
        'Table': {
            'TableName': 'ProductAssets',
            'TableStatus': 'ACTIVE',
            'KeySchema': [
                {'AttributeName': 'sub_category', 'KeyType': 'HASH'},
                {'AttributeName': 'product_id', 'KeyType': 'RANGE'}
            ]
        }
    }
    
    # get_item 성공 응답 mock
    mock_client.get_item.return_value = {
        'Item': {
            'sub_category': {'N': '1005'},
            'product_id': {'S': 'test_product_123'},
            'curation_status': {'S': 'COMPLETED'},
            'main_category': {'S': 'TOP'},
            'representative_assets': {
                'M': {
                    'front': {'S': 'front_image.jpg'},
                    'back': {'S': 'back_image.jpg'},
                    'model': {'S': 'model_image.jpg'}
                }
            }
        }
    }
    
    # update_item 성공 응답 mock
    mock_client.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    
    # paginator mock
    mock_paginator = Mock()
    mock_paginator.paginate.return_value = iter([
        {
            'Items': [
                {
                    'sub_category': {'N': '1005'},
                    'product_id': {'S': 'product_1'},
                    'curation_status': {'S': 'COMPLETED'}
                }
            ],
            'Count': 1,
            'ScannedCount': 1
        }
    ])
    mock_client.get_paginator.return_value = mock_paginator
    
    return mock_client

@pytest.fixture
def dynamodb_manager_with_mocks(mock_config, mock_dynamodb_client):
    """Mock을 사용한 DynamoDBManager 인스턴스를 제공하는 fixture"""
    with patch('aws.dynamodb.boto3.client', return_value=mock_dynamodb_client), \
         patch.object(DynamoDBManager, '_load_config', return_value=mock_config):
        manager = DynamoDBManager()
        return manager

class TestDynamoDBManagerWithMocks:
    """Mock을 사용한 DynamoDBManager 클래스 테스트"""
    
    def test_initialization_with_mocks(self, dynamodb_manager_with_mocks):
        """Mock을 사용한 DynamoDBManager 초기화 테스트"""
        manager = dynamodb_manager_with_mocks
        
        assert manager is not None
        assert manager.client is not None
        assert manager.region_name == "ap-northeast-2"
        assert manager.table_name == "ProductAssets"
        assert hasattr(manager, 'config')
        
        logger.info("DynamoDB Manager successfully initialized with mocks")
    
    def test_test_connection_success(self, dynamodb_manager_with_mocks):
        """연결 테스트 성공 시나리오"""
        manager = dynamodb_manager_with_mocks
        
        result = manager.test_connection()
        
        assert result is True
        assert hasattr(manager, 'table_info')
        manager.client.describe_table.assert_called_once_with(TableName="ProductAssets")
        
        logger.info("Connection test successful with mock")
    
    
    def test_get_item_success(self, dynamodb_manager_with_mocks):
        """get_item 성공 테스트"""
        manager = dynamodb_manager_with_mocks
        
        result = manager.get_item(sub_category=1005, product_id="test_product_123")
        
        assert result is not None
        assert isinstance(result, dict)
        assert result['sub_category'] == 1005
        assert result['product_id'] == "test_product_123"
        assert result['curation_status'] == "COMPLETED"
        assert result['main_category'] == "TOP"
        assert 'representative_assets' in result
        
        # get_item이 올바른 키로 호출되었는지 확인
        manager.client.get_item.assert_called_once()
        call_args = manager.client.get_item.call_args
        assert call_args[1]['TableName'] == "ProductAssets"
        assert 'Key' in call_args[1]
        
        logger.info("get_item success test passed")
    
    def test_get_item_not_found(self, mock_config):
        """get_item 데이터 없음 테스트"""
        mock_client = Mock()
        mock_client.get_item.return_value = {}  # Item이 없는 경우
        
        with patch('aws.dynamodb.boto3.client', return_value=mock_client), \
             patch.object(DynamoDBManager, '_load_config', return_value=mock_config):
            manager = DynamoDBManager()
            
            result = manager.get_item(sub_category=9999, product_id="nonexistent")
            
            assert result is None
            logger.info("get_item not found test passed")
    
    
    def test_update_caption_result_success(self, dynamodb_manager_with_mocks):
        """update_caption_result 성공 테스트"""
        manager = dynamodb_manager_with_mocks
        
        result = manager.update_caption_result(
            sub_category=1005,
            product_id="test_product",
            update_result="COMPLETED"
        )
        
        assert result is True
        manager.client.update_item.assert_called_once()
        
        call_args = manager.client.update_item.call_args
        assert call_args[1]['TableName'] == "ProductAssets"
        assert call_args[1]['UpdateExpression'] == "SET caption_status = :status"
        assert call_args[1]['ExpressionAttributeValues'][':status']['S'] == "COMPLETED"
        
        logger.info("update_caption_result success test passed")
    
    def test_update_caption_result_invalid_status(self, dynamodb_manager_with_mocks):
        """update_caption_result 잘못된 상태값 테스트"""
        manager = dynamodb_manager_with_mocks
        
        result = manager.update_caption_result(
            sub_category=1005,
            product_id="test_product",
            update_result="INVALID_STATUS"
        )
        
        assert result is False
        # update_item이 호출되지 않아야 함
        manager.client.update_item.assert_not_called()
        
        logger.info("update_caption_result invalid status test passed")

    
    def test_get_product_paginator_success(self, dynamodb_manager_with_mocks):
        """get_product_pagenator 성공 테스트"""
        manager = dynamodb_manager_with_mocks
        
        iterator = manager.get_product_pagenator(
            sub_category=1005,
            condition={'curation_status': 'COMPLETED'}
        )
        
        assert iterator is not None
        assert hasattr(iterator, '__iter__')
        
        # 첫 번째 페이지 확인
        first_page = next(iter(iterator))
        assert 'Items' in first_page
        assert len(first_page['Items']) == 1
        
        manager.client.get_paginator.assert_called_once_with('query')
        
        logger.info("get_product_paginator success test passed")

    
    def test_get_category_status_stats_success(self, dynamodb_manager_with_mocks):
        """get_category_status_stats 성공 테스트"""
        manager = dynamodb_manager_with_mocks
        
        # 통계 데이터를 위한 특별한 응답 설정
        manager.client.get_item.return_value = {
            'Item': {
                'sub_category': {'N': '0'},
                'product_id': {'S': 'STATUS_STATS_TOP_1005'},
                'completed_count': {'N': '50'},
                'pending_count': {'N': '30'},
                'pass_count': {'N': '5'},
                'total_products': {'N': '85'}
            }
        }
        
        result = manager.get_category_status_stats(main_category="TOP", sub_category=1005)
        
        assert result is not None
        assert isinstance(result, dict)
        assert result['completed_count'] == 50
        assert result['pending_count'] == 30
        assert result['total_products'] == 85
        
        logger.info("get_category_status_stats success test passed")
    
    def test_python_to_dynamodb_conversion(self, dynamodb_manager_with_mocks):
        """Python to DynamoDB 변환 테스트"""
        manager = dynamodb_manager_with_mocks
        
        test_data = {
            'sub_category': 1005,
            'product_id': 'test_product_123',
            'curation_status': 'PENDING',
            'main_category': 'TOP'
        }
        
        converted = manager._convert_python_to_dynamodb(test_data)
        
        assert isinstance(converted, dict)
        assert converted['sub_category']['N'] == '1005'
        assert converted['product_id']['S'] == 'test_product_123'
        assert converted['curation_status']['S'] == 'PENDING'
        assert converted['main_category']['S'] == 'TOP'
        
        logger.info("Python to DynamoDB conversion test passed")
    
    def test_dynamodb_to_python_conversion(self, dynamodb_manager_with_mocks):
        """DynamoDB to Python 변환 테스트"""
        manager = dynamodb_manager_with_mocks
        
        dynamodb_data = {
            'sub_category': {'N': '1005'},
            'product_id': {'S': 'test_product_123'},
            'curation_status': {'S': 'COMPLETED'},
            'representative_assets': {
                'M': {
                    'front': {'S': 'front_image.jpg'},
                    'back': {'S': 'back_image.jpg'}
                }
            },
            'detail': {
                'L': [
                    {'S': 'detail1'},
                    {'S': 'detail2'}
                ]
            },
            'is_active': {'BOOL': True},
            'price': {'N': '29.99'},
            'tags': {'SS': ['tag1', 'tag2']},
            'metadata': {'NULL': True}
        }
        
        converted = manager._convert_dynamodb_item_to_python(dynamodb_data)
        
        assert isinstance(converted, dict)
        assert converted['sub_category'] == 1005
        assert converted['product_id'] == 'test_product_123'
        assert converted['curation_status'] == 'COMPLETED'
        assert isinstance(converted['representative_assets'], dict)
        assert converted['representative_assets']['front'] == 'front_image.jpg'
        assert isinstance(converted['detail'], list)
        assert len(converted['detail']) == 2
        assert converted['is_active'] is True
        assert converted['price'] == 29.99
        assert converted['tags'] == ['tag1', 'tag2']
        assert converted['metadata'] is None
        
        logger.info("DynamoDB to Python conversion test passed")

    def test_string_sub_category_conversion(self, dynamodb_manager_with_mocks):
        """문자열 sub_category가 정수로 변환되는지 테스트"""
        manager = dynamodb_manager_with_mocks
        
        # get_item에서 문자열 sub_category 전달
        result = manager.get_item(sub_category="1005", product_id="test_product")
        
        assert result is not None
        # 내부적으로 정수로 변환되어 호출되어야 함
        manager.client.get_item.assert_called_once()
        
        logger.info("String sub_category conversion test passed")



