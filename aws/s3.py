import boto3
import json 
import logging
from botocore.exceptions import ClientError
from pathlib import Path

logger = logging.getLogger(__name__)

class S3Manager:
    def __init__(self , region_name: str, bucket_name: str):
        self.region_name = region_name
        self.bucket_name = bucket_name
        self.initialize_client()

    def initialize_client(self):
        self.client = boto3.client('s3', region_name=self.region_name)
        
    
    def test_connection(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            return False
    
    def get_s3_object_key(self, main_category: str, sub_category: int, product_id: str, relative_path: str) -> str:
        '''
        S3 객체 키를 생성합니다.
        
        Args:
            main_category: 대분류
            sub_category: 소분류
            product_id: 제품 ID
            relative_path: 상대 경로 (예: 'detail/0.jpg', 'meta.json' , "segment/0.jpg")
        Returns:
            str: S3 객체 키 (예: 'main_category/sub_category/product_id/segment/0.jpg')
        '''
        return f"{main_category}/{sub_category}/{product_id}/{relative_path}"
    
    def generate_presigned_url(self, key: str, client_method: str="get_object", expires_in: int = 3600) -> str|None:
        try:
            response = self.client.generate_presigned_url(
                client_method,
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return response
        except ClientError as e:
            logger.error(f"Presigned URL 생성 실패: {e}")
            return None
    
    #TODO :  파일 업로드 , 파일 다운로드 객체 키 생성 , 
    

if __name__ == "__main__":   
    s3_manager = S3Manager(region_name="ap-northeast-2", bucket_name="ai-dataset-curation")
    suceess = s3_manager.test_connection()
    if suceess:
        logger.info(f"S3 연결 성공: {s3_manager.bucket_name}")
    else:
        logger.error(f"S3 연결 실패: {s3_manager.bucket_name}")
    
    