import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class DynamoDBManager:
    def __init__(self , region_name: str, table_name: str):
        self.region_name = region_name
        self.table_name = table_name
        self.initialize_dynamodb_client()
        
    def initialize_dynamodb_client(self):
        self.client = boto3.client('dynamodb', region_name=self.region_name)
        
    def test_connection(self) -> bool:
        try:
            self.client.describe_table(TableName=self.table_name)
            return True
        except ClientError as e:
            return False
        
        
        
        
        
        