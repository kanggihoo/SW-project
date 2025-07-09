import pytest
from unittest.mock import Mock, patch
import json
from pathlib import Path

# =============================================================================
# 공통 Mock 설정 데이터
# =============================================================================

@pytest.fixture
def aws_mock_config():
    """AWS 테스트에서 공통으로 사용할 Mock 설정 데이터"""
    return {
        "aws": {
            "region_name": "ap-northeast-2"
        },
        "s3": {
            "bucket_name": "test-sw-fashion-image-data"
        },
        "dynamodb": {
            "table_name": "TestProductAssets"
        },
        "DEFAULT_PROJECTION_FIELDS": [
            "sub_category", "product_id", "curation_status", 
            "main_category", "representative_assets"
        ],
        "DEFAULT_PAGINATOR_CONFIG": {
            "PageSize": 10,
            "MaxItems": 100
        }
    }

# =============================================================================
# S3 관련 공통 Mock
# =============================================================================

@pytest.fixture
def mock_s3_manager():
    """공통 S3Manager Mock"""
    mock_s3 = Mock()
    mock_s3.test_connection.return_value = True
    mock_s3.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-image.jpg?presigned=true"
    mock_s3.upload_file.return_value = True
    mock_s3.download_file.return_value = True
    mock_s3.list_objects.return_value = ['test_object1.jpg', 'test_object2.jpg']
    return mock_s3

@pytest.fixture 
def mock_s3_client():
    """공통 S3 boto3 클라이언트 Mock"""
    mock_client = Mock()
    
    # head_bucket 성공 응답
    mock_client.head_bucket.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    
    # generate_presigned_url 응답
    mock_client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key.jpg?presigned=true"
    
    # upload_file 성공 응답
    mock_client.upload_file.return_value = None
    
    # download_file 성공 응답
    mock_client.download_file.return_value = None
    
    # list_objects_v2 응답
    mock_client.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'test_object1.jpg', 'Size': 1024},
            {'Key': 'test_object2.jpg', 'Size': 2048}
        ]
    }
    
    return mock_client

# =============================================================================
# DynamoDB 관련 공통 Mock
# =============================================================================

@pytest.fixture
def mock_dynamodb_manager():
    """공통 DynamoDBManager Mock"""
    mock_dynamodb = Mock()
    mock_dynamodb.test_connection.return_value = True
    
    # 기본 get_item 응답
    mock_dynamodb.get_item.return_value = {
        'sub_category': 1005,
        'product_id': 'test_product_123',
        'main_category': 'TOP',
        'curation_status': 'COMPLETED',
        'representative_assets': {
            'front': 'images/front/test_front.jpg',
            'back': 'images/back/test_back.jpg',
            'model': 'images/model/test_model.jpg'
        },
        'text': ['images/text/test_text1.jpg', 'images/text/test_text2.jpg']
    }
    
    # update_caption_result 기본 응답
    mock_dynamodb.update_caption_result.return_value = True
    
    # _convert_dynamodb_item_to_python 기본 응답
    mock_dynamodb._convert_dynamodb_item_to_python.return_value = {
        'sub_category': 1005,
        'product_id': 'test_product_123',
        'main_category': 'TOP',
        'curation_status': 'COMPLETED',
        'representative_assets': {
            'front': 'images/front/test_front.jpg',
            'back': 'images/back/test_back.jpg',
            'model': 'images/model/test_model.jpg',
            'color_variant': ['images/color1/test_color1.jpg', 'images/color2/test_color2.jpg']
        },
        'text': ['images/text/test_text1.jpg', 'images/text/test_text2.jpg']
    }
    
    return mock_dynamodb

@pytest.fixture
def mock_dynamodb_client():
    """공통 DynamoDB boto3 클라이언트 Mock"""
    mock_client = Mock()
    
    # describe_table 성공 응답
    mock_client.describe_table.return_value = {
        'Table': {
            'TableName': 'TestProductAssets',
            'TableStatus': 'ACTIVE',
            'KeySchema': [
                {'AttributeName': 'sub_category', 'KeyType': 'HASH'},
                {'AttributeName': 'product_id', 'KeyType': 'RANGE'}
            ]
        }
    }
    
    # get_item 성공 응답
    mock_client.get_item.return_value = {
        'Item': {
            'sub_category': {'N': '1005'},
            'product_id': {'S': 'test_product_123'},
            'curation_status': {'S': 'COMPLETED'},
            'main_category': {'S': 'TOP'},
            'representative_assets': {
                'M': {
                    'front': {'S': 'images/front/test_front.jpg'},
                    'back': {'S': 'images/back/test_back.jpg'},
                    'model': {'S': 'images/model/test_model.jpg'}
                }
            }
        }
    }
    
    # update_item 성공 응답
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

# =============================================================================
# 테스트 데이터 샘플
# =============================================================================

@pytest.fixture
def sample_dynamodb_item():
    """테스트용 DynamoDB 아이템 샘플"""
    return {
        'sub_category': {'N': '1005'},
        'product_id': {'S': 'test_product_123'},
        'main_category': {'S': 'TOP'},
        'curation_status': {'S': 'COMPLETED'},
        'representative_assets': {
            'M': {
                'front': {'S': 'segment/test_front.jpg'},
                'back': {'S': 'segment/test_back.jpg'},
                'model': {'S': 'segment/test_model.jpg'}
            }
        },
        'text': {
            'L': [
                {'S': 'test_text1.jpg'},
                {'S': 'test_text2.jpg'}
            ]
        }
    }

@pytest.fixture
def sample_converted_item():
    """테스트용 변환된 Python 아이템 샘플"""
    return {
        'sub_category': 1005,
        'product_id': 'test_product_123',
        'main_category': 'TOP',
        'curation_status': 'COMPLETED',
        'representative_assets': {
            'front': 'segment/test_front.jpg',
            'back': 'segment/test_back.jpg',
            'model': 'segment/test_model.jpg',
            'color_variant': ['segment/test_color1.jpg', 'segment/test_color2.jpg']
        },
        'text': ['test_text1.jpg', 'test_text2.jpg']
    }

# =============================================================================
# 유틸리티 함수들
# =============================================================================

def mock_open_config(config_data):
    """설정 파일을 mock하는 헬퍼 함수"""
    from unittest.mock import mock_open
    return mock_open(read_data=json.dumps(config_data))

# =============================================================================
# 클래스별 전용 fixture들
# =============================================================================

@pytest.fixture
def mock_dynamodb_manager_initialized(aws_mock_config, mock_dynamodb_client):
    """DynamoDBManager 테스트용 완전한 Mock 인스턴스"""
    from aws.dynamodb import DynamoDBManager
    
    with patch('aws.dynamodb.boto3.client', return_value=mock_dynamodb_client), \
         patch.object(DynamoDBManager, '_load_config', return_value=aws_mock_config):
        manager = DynamoDBManager()
        return manager

@pytest.fixture 
def mock_s3_manager_initialized(aws_mock_config, mock_s3_client):
    """S3Manager 테스트용 완전한 Mock 인스턴스"""
    from aws.s3 import S3Manager
    
    with patch('aws.s3.boto3.client', return_value=mock_s3_client), \
         patch.object(S3Manager, '_load_config', return_value=aws_mock_config):
        manager = S3Manager()
        return manager

@pytest.fixture
def mock_aws_manager_initialized(aws_mock_config, mock_s3_manager, mock_dynamodb_manager):
    """AWSManager 테스트용 완전한 Mock 인스턴스"""
    from aws.aws_manager import AWSManager
    
    with patch.object(AWSManager, '_load_config', return_value=aws_mock_config), \
         patch('aws.aws_manager.S3Manager', return_value=mock_s3_manager), \
         patch('aws.aws_manager.DynamoDBManager', return_value=mock_dynamodb_manager):
        manager = AWSManager()
        return manager

