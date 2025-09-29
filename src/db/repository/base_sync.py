from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from db.config.database import DatabaseManager
from db.config import Config
from pymongo.collection import Collection
from db.query_builders.fashion_queries import FashionQueryBuilder
import os


class BaseRepository(ABC):
    """기본 Repository 추상 클래스"""

    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        """
        BaseRepository 초기화

        Args:
            connection_string: MongoDB 연결 문자열
            database_name: 데이터베이스 이름
            collection_name: 컬렉션 이름
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.db_manager = DatabaseManager(connection_string, database_name, collection_name)
        self.collection = self.db_manager.get_collection()
        self.query_builder = FashionQueryBuilder()

    # ============================================================================
    # 연결 관리 메서드 (구현체 제공)
    # ============================================================================
    def is_connected(self) -> bool:
        """데이터베이스 연결 상태 확인"""
        return self.db_manager.is_connected()

    def close_connection(self):
        """연결 종료"""
        self.db_manager.close()

    # ============================================================================
    # 추상 메서드들 - 자식 클래스에서 반드시 구현
    # ============================================================================
    @abstractmethod
    def find_by_id(self, doc_id: str) -> Optional[Dict]:
        """ID로 문서 조회"""
        pass

    @abstractmethod
    def find_all(self, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """조건에 맞는 모든 문서 조회"""
        pass

    @abstractmethod
    def create(self, document: Dict) -> Optional[str]:
        """문서 생성"""
        pass

    @abstractmethod
    def update_by_id(self, doc_id: str, update_data: Dict) -> bool:
        """ID로 문서 업데이트"""
        pass

    @abstractmethod
    def delete_by_id(self, doc_id: str) -> bool:
        """ID로 문서 삭제"""
        pass

    @abstractmethod
    def find(self, query: dict) -> List[Dict]:
        """쿼리에 맞는 문서 조회"""
        pass

    # ============================================================================
    # 공통 유틸리티 메서드 (구현체 제공)
    # ============================================================================
    # def count_documents(self, filter_dict: Optional[Dict] = None) -> int:
    #     """문서 개수 조회"""
    #     try:
    #         filter_dict = filter_dict or {}
    #         return self.collection.count_documents(filter_dict)
    #     except Exception:
    #         return 0

    # def collection_exists(self) -> bool:
    #     """컬렉션 존재 여부 확인"""
    #     try:
    #         collection_names = self.db_manager._db.list_collection_names()
    #         return self.db_manager.collection_name in collection_names
    #     except Exception:
    #         return False
