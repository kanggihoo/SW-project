from loguru import logger
from pymongo import AsyncMongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.server_api import ServerApi


class AsyncDatabaseManager:
    """비동기 DB 연결 관리 클래스"""

    def __init__(self, connection_string: str, database_name: str = None, collection_name: str = None, timeout_ms: int = 5000):
        """AsyncDatabaseManager 클래스 초기화 (연결은 하지 않음)"""
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.timeout_ms = timeout_ms

        self._client: AsyncMongoClient = None
        self._db: Database = None
        self._connection_status: bool = False

    async def connect(self):
        """데이터베이스 연결 초기화"""
        if self._connection_status:
            return
        try:
            self._validate_connection_string()
            self._create_client()
            await self._connect_to_database()
            await self._verify_connection()
            self._connection_status = True
            logger.info(f'Successfully connected to MongoDB (async): {self.database_name}')
        except Exception as e:
            logger.error(f'Failed to connect to MongoDB (async): {e}')
            self._connection_status = False
            raise ConnectionError(f'Failed to connect to MongoDB (async): {e}')

    def _validate_connection_string(self):
        """연결 문자열 검증"""
        if not self.connection_string:
            raise ValueError('Connection string is required')
        if not self.database_name:
            raise ValueError('Database name is required')
        if not self.collection_name:
            raise ValueError('Collection name is required')

    def _create_client(self):
        """AsyncMongoClient 생성"""
        self._client = AsyncMongoClient(
            self.connection_string,
            serverSelectionTimeoutMS=self.timeout_ms,
            connectTimeoutMS=self.timeout_ms,
            socketTimeoutMS=self.timeout_ms,
            server_api=ServerApi('1'),
        )

    async def _connect_to_database(self):
        """데이터베이스 연결"""
        if not self._client:
            raise ConnectionError('AsyncMongoClient is not initialized')
        self._db = self._client[self.database_name]

    async def _verify_connection(self):
        """연결 상태 검증"""
        try:
            await self._client.admin.command('ping')
            collection_names = await self._db.list_collection_names()
            logger.info(f'Database verified (async): {len(collection_names)} collections found')
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise ConnectionError(f'Connection verification failed (async): {e}')

    def get_collection(self):
        if self._db is None:
            raise ConnectionError('Database connection not established (async)')
        return self._db[self.collection_name]

    async def is_connected(self) -> bool:
        if not self._connection_status or not self._client:
            return False
        try:
            await self._client.admin.command('ping')
            return True
        except ConnectionFailure:
            self._connection_status = False
            return False

    async def close(self):
        if self._client:
            await self._client.close()
            logger.info('MongoDB async client closed')
        self._connection_status = False

    async def __aenter__(self):
        if not self._connection_status:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
