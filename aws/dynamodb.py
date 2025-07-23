import boto3
import logging
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer
from pathlib import Path
from typing import Iterator , Any
from pydantic import validate_call 

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class DynamoDBManager:
    def __init__(self , region_name: str|None = None, table_name: str|None = None, config:dict=None):
        self.region_name = region_name
        self.table_name = table_name
        self.projection_fields = config.get("DEFAULT_PROJECTION_FIELDS",[])
        self.pagenator_config = config.get("DEFAULT_PAGINATOR_CONFIG",{})
        self.GSI_NAME = config.get("DEFAULT_GSI_NAME",None)
        self.client = None
        self._initialize_client()
    
    # =============================================================================
    # 클라이언트 초기화 관련 함수
    # =============================================================================
    def _initialize_client(self):
        try:
            self.client = boto3.client('dynamodb', region_name=self.region_name)
        except ClientError as e:
            logger.error(f"DynamoDB 클라이언트 초기화 실패: {e}")
            raise 
        except Exception as e:
            logger.error(f"DynamoDB 클라이언트 초기화 예상치 못한 오류: {e}")
            raise 
        logger.info(f"DynamoDB 클라이언트 초기화 완료: {self.table_name}")


    def test_connection(self) -> bool:
        """DynamoDB 연결 테스트"""
        try:
            if not self.client:
                return False
            self.table_info = self.client.describe_table(TableName=self.table_name)
            return True
        except ClientError as e:
            logger.error(f"DynamoDB 연결 테스트 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"DynamoDB 연결 중 예상치 못한 오류: {e}")
            return False
    
    # =============================================================================
    # CRUD , Query 관련 함수들
    # =============================================================================
    @validate_call
    def get_item(self, sub_category:int, product_id: str) -> dict|None:
        """현재 테이블의 파티션 키와 정렬 키를 기반으로 조회후 python 딕셔너리로 변환

        Args:
            sub_category (int): 서브 카테고리 ID
            product_id (str): 제품 ID
        Returns:
            dict|None: 조회 결과 (없으면 None)
        """
        if isinstance(sub_category, str):
            sub_category = int(sub_category)
            
        key = self._convert_python_to_dynamodb({
            'sub_category': sub_category,
            'product_id': product_id
        })
        try:
            response = self.client.get_item(
                TableName=self.table_name,
                Key=key
            )
            item = response.get('Item')
            if item:
                logger.info(f"DynamoDB {self.table_name} 조회 성공: {sub_category}-{product_id}")
                return self._convert_dynamodb_item_to_python(item)
            else:
                logger.warning(f"DynamoDB {self.table_name}에 대응하는 항목 없음: {sub_category}-{product_id}")
                return None
        except ClientError as e:
            logger.error(f"DynamoDB 조회 간 오류 발생 : {e}")
            return {}
    @validate_call
    def update_caption_result(self, sub_category: int, product_id: str , update_result:str):
        """caption_status 업데이트 

        Args:
            sub_category (int): 서브 카테고리 ID
            product_id (str): 제품 ID
            update_result (str): 업데이트 결과 => value 값은 COMPLETED, PENDING, FAIL 중 하나
        """
        if isinstance(sub_category, str):
            sub_category = int(sub_category)
        
        if update_result != 'COMPLETED':
            logger.error(f"caption_status 업데이트 결과 값 오류 : {update_result} , 업데이트 결과 값은 COMPLETED 여야 합니다.")
            return
        try:
            key = self._convert_python_to_dynamodb({
                'sub_category': sub_category,
                'product_id': product_id
            })
            update_expression = "SET caption_status = :status"
            expression_attribute_values = {
                ':status': {'S': update_result}
            }
            self.client.update_item(
                TableName=self.table_name,
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            logger.info(f"DynamoDB caption_status 업데이트 성공 : {sub_category} , {product_id} : {update_result}")
        except ClientError as e:
            logger.error(f"DynamoDB 업데이트 간 오류 발생 : {e}")
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생 : {e}")

        
    
    # def put_item(self, item: dict) -> bool:
    #     """
    #     Upsert 연산으로 주어진 key에 대해 이미 존재하면 입력으로 주어진 항목으로 변경(다른 속성 제거), 이미 존재하지 않으면 새로운 item 생성(create)
    #     Args:
    #         item: 추가할 데이터 (타입 정보 포함)
    #     """
    #     ...
    
    # =============================================================================
    # pagenation 관련 함수 
    # =============================================================================

    def get_product_pagenator(self ,
                              partition:dict|None = None ,
                              sub_category:int|None = None,
                              GSI_NAME:str|None = None,
                              projection_fields:list[str]=None,
                              pagenator_config:dict=None,
                              ) -> Iterator[dict] | None:
        """조건에 맞는 제품 리스트 조회 (페이지네이터 반환)

        Args:
            projection_fields (list[str], optional): 조회할 필드 목록. Defaults to None.
            pagenator_config (dict, optional): 페이지네이터 설정. Defaults to None.
            condition (dict, optional): 조회 조건. Defaults to None.
                - curation_status: GSI 사용 시 필수 파티션 키
                - product_id: 정렬 키 조건 (=, begins_with)
                - recommendation_order: GSI 정렬 키 조건 (=, <, >, <=, >=, begins_with)
                - 기타 필드: FilterExpression으로 처리
            pagenator_config (dict, optional): 페이지네이터 설정. Defaults to None.
            projection_fields (list[str], optional): 조회할 필드 목록. Defaults to None.

        Returns:
            _type_: paginator 객체
            
        Raises:
            TypeError: 파라미터 타입이 올바르지 않은 경우
            ValueError: 파라미터 값이 올바르지 않은 경우
        """
        projection_fields = projection_fields if projection_fields else self.projection_fields
        pagenator_config = pagenator_config if pagenator_config else self.pagenator_config
        try:
            # DynamoDB 예약어 처리
            reserved_keywords = {"text"}
            expression_attribute_names = {}
            projection_expresssion_part = []
            for field in projection_fields:
                if field in reserved_keywords:
                    alias = f"#{field}"
                    projection_expresssion_part.append(alias)
                    expression_attribute_names[alias] = field
                else:
                    projection_expresssion_part.append(field)
                    
            # 프로젝션 필드 설정
            projection_expression = ", ".join(projection_expresssion_part)
            
                
            # # condition 파라미터 처리
            # if condition is None:
            #     condition = {}
            
            # GSI 사용 여부 결정 (curation_status가 있으면 GSI 사용)
            use_gsi = GSI_NAME is not None
            
            # 기본 쿼리 파라미터 설정
            query_params = {
                'TableName': self.table_name,
                'PaginationConfig': pagenator_config 
            }
            
            # KeyConditionExpression 및 ExpressionAttributeValues 구성
            key_condition_parts = []
            expression_values = {}
            
            
            if use_gsi:
                # GSI 사용 시
                query_params['IndexName'] = GSI_NAME
                
                # 파티션 키: curation_status
                partition_key = partition.get("key")
                partition_value = partition.get("value")
                partition_type = partition.get("type")
                key_condition_parts.append(f'{partition_key} = :{partition_key}')
                expression_values[f':{partition_key}'] = {partition_type: partition_value}
                
            else:
                # 파티션 키: sub_category
                key_condition_parts.append('sub_category = :sub_category')
                expression_values[':sub_category'] = {'N': str(sub_category)}
                
            #  ProjectionExpression 설정 
            query_params['ProjectionExpression'] = projection_expression
            # KeyConditionExpression 설정 (AND 조건만 가능 )
            if key_condition_parts:
                query_params['KeyConditionExpression'] = ' AND '.join(key_condition_parts)
            
         
            # ExpressionAttributeValues 설정
            if expression_values:
                query_params['ExpressionAttributeValues'] = expression_values
            if expression_attribute_names:
                query_params['ExpressionAttributeNames'] = expression_attribute_names
            
            
            
            paginator = self.client.get_paginator('query')
            return paginator.paginate(**query_params)
        
        except ClientError as e:
            logger.error(f"DynamoDB 조회 간 오류 발생 : {e}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생 : {e}")
            return None
    
    # =============================================================================
    # main_category , sub_category 별 통계 관련 함수
    # =============================================================================
    def get_category_status_stats(self, main_category: str, sub_category: int) -> dict | None:
        stats_id = f"STATUS_STATS_{main_category}_{sub_category}"
        try:
            key = self._convert_python_to_dynamodb({
                'sub_category': 0,
                'product_id': stats_id
            })
            
            response = self.client.get_item(
                TableName=self.table_name,
                Key=key
            )
            
            item = response.get('Item')
            if item:
                return self._convert_dynamodb_item_to_python(item)
            else:
                return None
        except Exception as e:
            logger.error(f"카테고리 상태 통계 조회 실패 {main_category}-{sub_category}: {e}")
            return None
        

    # =============================================================================
    # 유틸리티 함수
    # =============================================================================
    def close_connection(self):
        if self.client:
            self.client.close()
            self.client = None
            logger.info(f"DynamoDB 클라이언트 연결 종료: {self.table_name}")

    def _convert_dynamodb_item_to_python(self, item: dict) -> dict:
        """
        DynamoDB client 응답 아이템을 일반 딕셔너리로 변환합니다.
        
        Args:
            item: DynamoDB에서 쿼리 반환결과인 Item 키에 대한 데이터 (타입 정보 포함)
                example : {'속성이름': {'데이터타입': '값'}, ...}
            
        Returns:
            dict: {"속성이름": "값", ...}
        """
        converted = {}
        for key, value in item.items():
            if 'S' in value:  # String
                converted[key] = value['S']
            elif 'N' in value:  # Number
                # 정수로 변환 시도, 실패하면 float
                try:
                    converted[key] = int(value['N'])
                except ValueError:
                    converted[key] = float(value['N'])
            elif 'SS' in value:  # String Set
                converted[key] = value['SS']
            elif 'NS' in value:  # Number Set
                converted[key] = [int(n) for n in value['NS']]
            elif 'BOOL' in value:  # Boolean
                converted[key] = value['BOOL']
            elif 'NULL' in value:  # Null
                converted[key] = None
            elif 'M' in value:  # Map
                converted[key] = self._convert_dynamodb_item_to_python(value['M'])
            elif 'L' in value:  # List
                # List 내부 아이템들을 변환
                converted_list = []
                for list_item in value['L']:
                    if 'S' in list_item:  # String 아이템
                        converted_list.append(list_item['S'])
                    else:
                        # 다른 타입의 아이템은 재귀 변환
                        converted_list.append(self._convert_dynamodb_item_to_python({'item': list_item})['item'])
                converted[key] = converted_list
            else:
                # 알 수 없는 타입은 그대로 유지
                converted[key] = value
        return converted
        
    def _convert_python_to_dynamodb(self, item: dict) -> dict:
        """
        일반 python 딕셔너리를 DynamoDB client 메서드에 전달할 아이템 형식으로 변환(타입 정보 포함)
        (참고 : python의 Float 타입은 지원되지 않음.)
        Args:
            item (dict): {"속성이름": "값", ...}

        Returns:
            dict: {'속성이름': {'데이터타입': '값'}, ...}
        """
        serializer = TypeSerializer()
        return {k: serializer.serialize(v) for k, v in item.items()}
    

        

# if __name__ == "__main__":
#     dynamodb_manager = DynamoDBManager()
    
#     # 사용 예제
    
    
#     # 2. 특정 product_id로 시작하는 제품들
#     print("=== product_id 조건 예제 ===")
#     condition = {
#         'curation_status': 'COMPLETED'
#     }
#     iterator = dynamodb_manager.get_product_pagenator(
#         sub_category=1005, 
#         condition=condition
#     )

   
    
                