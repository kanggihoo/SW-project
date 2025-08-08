import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from dev_tools.local_mongodb.config import Config
from db.repository.fashion_sync import FashionRepository

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
from tabulate import tabulate
import pandas as pd

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s : %(message)s')
logger = logging.getLogger(__name__)


class ProductMetaManager:
    """
    Products 컬렉션의 메타데이터를 관리하는 클래스
    
    주요 기능:
    1. 전체 제품 데이터 메타정보 수집
    2. 특정 main_category 또는 sub_category에 대한 메타정보 업데이트
    3. 유연한 메타데이터 조회 및 관리
    """
    
    def __init__(self, config:Config):
        """
        ProductMetaManager 초기화
        
        Args:
            connection_string (str): MongoDB 연결 문자열
            database_name (str): 데이터베이스 이름
            products_collection (str): 상품 정보 컬렉션 이름
            meta_collection (str): 메타데이터 컬렉션 이름
        """
        self.db_config = config.get_mongodb_local_dict()
        self.db = FashionRepository(connection_string=self.db_config["CONNECTION_STRING"],
                                                    database_name=self.db_config["DATABASE_NAME"],
                                                    collection_name=self.db_config["COLLECTION_NAME"])
        
        self.all_possible_statuses = ['CR_DET', 'IMG_DOWN', 'AWS_UPL', 'RE_COMP', 'CA_COMP', 'EB_COMP' , 'CL_COMP']
    
    def show_terminal(self):
                                    
        """
        제품 메타데이터 집계
        
        Args:
            main_category (Optional[str]): 메인 카테고리 필터
            sub_category (Optional[str]): 서브 카테고리 필터
        
        Returns:
            List[Dict[str, Any]]: 메타데이터 집계 결과
        """
        pipeline = [
        {
            "$group": {
                "_id": {
                    "main_category": "$main_category",
                    "sub_category": "$sub_category",
                    "data_status": "$data_status"
                },
                "total_count_per_status": {"$sum": 1} 
            }
        },
        {
            "$group": {
                "_id": {
                    "main_category": "$_id.main_category",
                    "sub_category": "$_id.sub_category"
                },
                "status_breakdown": {
                    "$push": {
                        "status": "$_id.data_status",
                        "count": "$total_count_per_status"
                    }
                },
                "total_overall_count": {"$sum": "$total_count_per_status"} 
            }
        },
        {
            "$project": {
                "_id": 0,
                "main_category": "$_id.main_category",
                "sub_category": "$_id.sub_category",
                "status_breakdown": 1,
                "total_overall_count": 1
            }
        },
        {
            "$unwind": "$status_breakdown"
        },
        {
            "$group": {
                "_id": {
                    "main_category": "$main_category",
                    "sub_category": "$sub_category"
                },
                "CR_DET": {
                    "$sum": {
                        "$cond": [{ "$eq": ["$status_breakdown.status", "CR_DET"] }, "$status_breakdown.count", 0]
                    }
                },
                "AWS_UPL": {
                    "$sum": {
                        "$cond": [{ "$eq": ["$status_breakdown.status", "AWS_UPL"] }, "$status_breakdown.count", 0]
                    }
                },
                "RE_COMP": {
                    "$sum": {
                        "$cond": [{ "$eq": ["$status_breakdown.status", "RE_COMP"] }, "$status_breakdown.count", 0]
                    }
                },
                "CA_COMP": {
                    "$sum": {
                        "$cond": [{ "$eq": ["$status_breakdown.status", "CA_COMP"] }, "$status_breakdown.count", 0]
                    }
                },
                "EB_COMP": {
                    "$sum": {
                        "$cond": [{ "$eq": ["$status_breakdown.status", "EB_COMP"] }, "$status_breakdown.count", 0]
                    }
                },
                "CL_COMP": {
                    "$sum": {
                        "$cond": [{ "$eq": ["$status_breakdown.status", "CL_COMP"] }, "$status_breakdown.count", 0]
                    }
                },
                "total_count": { "$first": "$total_overall_count" } 
            }
        },
        {
            "$project": {
                "_id": 0,
                "main_category": "$_id.main_category",
                "sub_category": "$_id.sub_category",
                "CR_DET": 1,
                "AWS_UPL": 1,
                "RE_COMP": 1,
                "CA_COMP": 1,
                "EB_COMP": 1,
                "CL_COMP": 1,
                "total_count": 1
            }
        }
        ]
        result = list(self.db.collection.aggregate(pipeline))
        # # # tabulate 라이브러리를 사용하여 DataFrame을 텍스트 표로 변환
        df = pd.DataFrame(result)
        df = df[['main_category', 'sub_category', 'CR_DET', 'AWS_UPL', 'RE_COMP', 'CA_COMP', 'EB_COMP', 'CL_COMP', 'total_count']]
        df = df.sort_values(by=['main_category', 'sub_category'], ascending=True)
        
        print(tabulate(df, headers='keys', tablefmt='grid'))
    

    def get_sub_categories(self , main_category:str) ->List:
        query_filter = {"main_category":main_category}
        sub_categories = self.db.collection.distinct("category_sub" , query_filter)
        return sub_categories

    def show_df(self):
        pipeline = [
        {
            "$group": {
                "_id": {
                    "main_category": "$main_category",
                    "sub_category": "$sub_category",
                    "data_status": "$data_status"
                },
                "total_count": {"$sum": 1}
            }
        },
        {
            "$group": {
                "_id": {
                    "main_category": "$_id.main_category",
                    "sub_category": "$_id.sub_category"
                },
                "status_list": {
                    "$push": {
                        "status": "$_id.data_status",
                        "count": "$total_count"
                    }
                },
                "total_count": {"$sum": "$total_count"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "main_category": "$_id.main_category",
                "sub_category": "$_id.sub_category",
                "status_list": 1,
                "total_count": 1
            }
        }
        ]
        sub_categories = self.db.collection.aggregate(pipeline)
        result = list(sub_categories)
        # 1. 초기 DataFrame 생성
        df_raw = pd.DataFrame(result)
        
        # 2. status_breakdown 배열을 풀기 (explode)
        # 각 status_breakdown 항목을 개별 행으로 만듭니다.
        df_exploded = df_raw.explode('status_list')    

        # # status와 count를 독립적인 컬럼으로 만듭니다.
        df_normalized = pd.json_normalize(df_exploded['status_list'])
        
        # # 4. 원본 DataFrame과 정규화된 데이터 결합
        df_flattened = pd.concat([df_exploded.drop(columns=['status_list', 'total_count']).reset_index(drop=True), df_normalized], axis=1)
        
        
        # # 5. 피벗 테이블을 사용하여 각 status를 컬럼으로 만들고 total_count 합치기
    
        df_pivot = df_flattened.pivot_table(
            index=['main_category', 'sub_category'],
            columns='status',
            values='count',
            aggfunc='sum',
            fill_value=0 # 값이 없는 경우 0으로 채움
        ).reset_index()
        
        # Add missing columns with 0 to df_pivot
        for status in self.all_possible_statuses:
            if status not in df_pivot.columns:
                df_pivot[status] = 0
        
        df_pivot['total_count'] = df_pivot.iloc[:, 2:].sum(axis=1) # index, main, sub 이후 컬럼들 (status count)의 합

        # # 컬럼 순서 재정의 (보기 좋게)
        # status_columns = [col for col in df_pivot.columns if col not in ['main_category', 'sub_category', 'total_count']]
        df_final = df_pivot[['main_category', 'sub_category'] + self.all_possible_statuses + ['total_count']]
        print(df_final)

    
    def close(self):
        """MongoDB 연결 종료"""
        self.fasionrepo.close_connection()

# 사용 예시
if __name__ == "__main__":
    # 제품 메타데이터 관리자 초기화
    db_config = Config().get_mongodb_local_dict()
    manager = ProductMetaManager(config=Config())
    manager.show_terminal()
    
    
