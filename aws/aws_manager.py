from pathlib import Path
import json

from dynamodb import DynamoDBManager
from s3 import S3Manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSManager:
    def __init__(self):
        self._initialize_aws_services()
        
        
    def _initialize_aws_services(self):
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
        
        
    def _load_config(self) -> dict:
        config_path = Path(__file__).parent / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    
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
    
    
if __name__ == "__main__":
    aws_manager = AWSManager()
    
    
    
        
        
        