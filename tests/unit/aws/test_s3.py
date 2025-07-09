import pytest
from unittest.mock import Mock, patch
from aws import s3 

import json
import os
from pathlib import Path
import pytest
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def config():
    print("\n[Fixture] Loading config...")  # fixture의 print
    # 프로젝트 루트 디렉토리 기준으로 aws/config.json 경로를 계산
    project_root = Path(__file__).resolve().parents[3]
    config_path = project_root / "aws" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    print(f"[Fixture] Config loaded: {config_data}")  # fixture의 print
    return config_data

@pytest.fixture
def s3_manager(config):
    print(f"\n[Fixture] Creating S3Manager with config...")  # fixture의 print
    manager = s3.S3Manager(
        region_name=config["aws"]["region_name"],
        bucket_name=config["s3"]["bucket_name"]
    )
    print(f"[Fixture] S3Manager created with bucket: {manager.bucket_name}")  # fixture의 print
    return manager



def test_s3_manager_test_connection(s3_manager):
    print("\n[Test] Starting connection test...")  # 테스트의 print
    assert s3_manager.test_connection() is True
    print("[Test] Connection test completed")  # 테스트의 print
    

@pytest.mark.parametrize(
    "main_category, sub_category, product_id, relative_path, expected",
    [
        ("clothing", 1, "ABC123", "detail/0.jpg", "clothing/1/ABC123/detail/0.jpg"),
        ("shoes", 2, "XYZ789", "meta.json", "shoes/2/XYZ789/meta.json"),
        ("accessories", 3, "DEF456", "segment/0.jpg", "accessories/3/DEF456/segment/0.jpg"),
    ]
)
def test_s3_manager_get_s3_object_key(s3_manager, main_category, sub_category, product_id, relative_path, expected):
    result = s3_manager.get_s3_object_key(
        main_category=main_category,
        sub_category=sub_category,
        product_id=product_id,
        relative_path=relative_path
    )
    assert result == expected
