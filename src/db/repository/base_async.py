from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from db.config.database_async import AsyncDatabaseManager
from db.query_builders.fashion_queries import FashionQueryBuilder


class BaseAsyncRepository(ABC):
    """기본 비동기 Repository 추상 클래스"""

    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.db_manager = AsyncDatabaseManager(connection_string, database_name, collection_name)
        self.collection = None  # connect() 후에 초기화
        self.query_builder = FashionQueryBuilder()

    async def connect(self):
        """DB 연결 및 컬렉션 객체 획득"""
        await self.db_manager.connect()
        self.collection = self.db_manager.get_collection()

    async def close(self):
        """DB 연결 종료"""
        await self.db_manager.close()

    async def is_connected(self) -> bool:
        """데이터베이스 연결 상태 확인"""
        return await self.db_manager.is_connected()

    @abstractmethod
    async def find_by_id(self, doc_id: str) -> dict | None:
        """ID로 문서 조회"""
        pass

    @abstractmethod
    async def find_all(self, filter_dict: dict | None = None) -> AsyncIterator[dict]:
        """조건에 맞는 모든 문서 조회"""
        pass

    @abstractmethod
    async def create(self, document: dict) -> str | None:
        """문서 생성"""
        pass

    @abstractmethod
    async def update_by_id(self, doc_id: str, update_data: dict) -> bool:
        """ID로 문서 업데이트"""
        pass

    @abstractmethod
    async def delete_by_id(self, doc_id: str) -> bool:
        """ID로 문서 삭제"""
        pass

    @abstractmethod
    async def find(self, query: dict) -> AsyncIterator[dict]:
        """쿼리에 맞는 문서 조회"""
        pass
