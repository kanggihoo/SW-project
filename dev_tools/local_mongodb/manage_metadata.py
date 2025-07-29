import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from dev_tools.local_mongodb.config import Config
from db.repository.fashion import FashionRepository

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
from enum import Enum
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s : %(message)s')
logger = logging.getLogger(__name__)

class DataSaveStatus(Enum):
    CR_SUM = "CR_SUM" # 크롤링 summary 완료 
    CR_DET = "CR_DET" # 크롤링 detail 완료 
    IMG_DOWN = "IMG_DOWN" # 크롤링한 결과에 대한 이미지 다운로드 완료 
    AWS_UPL = "AWS_UPL" # 다운로드 한 이미지 aws에 업로드 완료 
    RE_COMP = "RE_COMP" # 대표 이미지 정보 저장 완료
    CA_COMP = "CA_COMP" # 선정된 대표 이미지에 대해 캡션 정보 저장 완료 
    EMB_COMP = "EMB_COMP" # 캡션 완료된 제품에 대한 임베딩 정보 저장 완료 

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
        self.meta_config = config.get_mongodb_local_meta_dict()
        self.db_config = config.get_mongodb_local_dict()
        self.db = FashionRepository(connection_string=self.db_config["CONNECTION_STRING"],
                                                    database_name=self.db_config["DATABASE_NAME"],
                                                    collection_name=self.db_config["COLLECTION_NAME"])
        
        self.meta = FashionRepository(connection_string=self.meta_config["CONNECTION_STRING"],
                                                    database_name=self.meta_config["DATABASE_NAME"],
                                                    collection_name=self.meta_config["COLLECTION_NAME"])
    
    def _aggregate_product_metadata(self):
                                    
        """
        제품 메타데이터 집계
        
        Args:
            main_category (Optional[str]): 메인 카테고리 필터
            sub_category (Optional[str]): 서브 카테고리 필터
        
        Returns:
            List[Dict[str, Any]]: 메타데이터 집계 결과
        """
        pipeline = []
        
        # # 필터 조건 추가
        # match_stage = {}
        # if main_category:
        #     match_stage["main_category"] = main_category
        # if sub_category:
        #     match_stage["sub_category"] = sub_category
        
        # if match_stage:
        #     pipeline.append({"$match": match_stage})
        
        # 메타데이터 집계 파이프라인
        pipeline.extend([
            {
                "$group": {
                    "_id": {
                        "main_category": "$category_main", 
                        "sub_category": "$category_sub",
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
                    "status_breakdown": {
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
                    "status_breakdown": 1,
                    "total_count": 1
                }
            }
        ])
        
        return list(self.products_collection.aggregate(pipeline))
    
    def update_product_metadata(self, 
                                main_category: Optional[str] = None, 
                                sub_category: Optional[str] = None) -> Dict[str, Any]:
        """
        제품 메타데이터 업데이트
        
        Args:
            main_category (Optional[str]): 메인 카테고리 필터
            sub_category (Optional[str]): 서브 카테고리 필터
        
        Returns:
            Dict[str, Any]: 업데이트 결과
        """
        try:
            # 전체 데이터 개수 확인
            total_products = self.products_collection.count_documents({})
            
            # 메타데이터 집계
            metadata_results = self._aggregate_product_metadata(main_category, sub_category)
            
            # 메타데이터 저장
            meta_document = {
                "total_products": total_products,
                "last_updated": datetime.now(),
                "category_metadata": metadata_results
            }
            
            # 기존 메타데이터 대체 또는 삽입
            filter_query = {}
            if main_category:
                filter_query["main_category"] = main_category
            if sub_category:
                filter_query["sub_category"] = sub_category
            
            self.meta_collection.replace_one(
                filter_query, 
                meta_document, 
                upsert=True
            )
            
            logger.info(f"메타데이터 업데이트 완료: {len(metadata_results)}개 카테고리")
            
            return {
                "success": True,
                "total_products": total_products,
                "category_count": len(metadata_results)
            }
        
        except Exception as e:
            logger.error(f"메타데이터 업데이트 중 오류 발생: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_product_metadata(self, 
                             main_category: Optional[str] = None, 
                             sub_category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        제품 메타데이터 조회
        
        Args:
            main_category (Optional[str]): 메인 카테고리 필터
            sub_category (Optional[str]): 서브 카테고리 필터
        
        Returns:
            Optional[Dict[str, Any]]: 메타데이터
        """
        try:
            # 필터 쿼리 생성
            filter_query = {}
            if main_category:
                filter_query["main_category"] = main_category
            if sub_category:
                filter_query["sub_category"] = sub_category
            
            # 메타데이터 조회
            return self.meta_collection.find_one(filter_query)
        
        except Exception as e:
            logger.error(f"메타데이터 조회 중 오류 발생: {e}")
            return None
    def get_sub_categories(self , main_category:str) ->List:
        query_filter = {"main_category":main_category}
        sub_categories = self.db.collection.distinct("category_sub" , query_filter)
        return sub_categories

    
    def close(self):
        """MongoDB 연결 종료"""
        self.fasionrepo.close_connection()

# 사용 예시
if __name__ == "__main__":
    # 제품 메타데이터 관리자 초기화
    meta_config = Config().get_mongodb_local_meta_dict()
    db_config = Config().get_mongodb_local_dict()
    db = FashionRepository(connection_string=db_config["CONNECTION_STRING"],
                                                database_name=db_config["DATABASE_NAME"],
                                                collection_name=db_config["COLLECTION_NAME"])
    
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
                "status_breakdown": {
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
                "status_breakdown": 1,
                "total_count": 1
            }
        },
        #   {
        #     "$project": {
        #         "_id": 0,
        #         "main_category": "$_id.main_category",
        #         "sub_category": "$_id.sub_category",
        #         "data_status": "$_id.data_status",
        #         "total_count": 1
        #     }
        # }
        
    ]
    sub_categories = db.collection.aggregate(pipeline)
    for i in sub_categories:
        print(i)
   
    print("########################################################")
    print(db.collection.distinct("main_category"))
    print("########################################################")
    print(db.collection.distinct("sub_category"))
    
