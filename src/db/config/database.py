from loguru import logger
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.server_api import ServerApi


class DatabaseManager:
    """DB 연결 관리 클래스"""

    def __init__(self, connection_string: str, database_name: str = None, collection_name: str = None, timeout_ms: int = 5000):
        """DatabaseManager 클래스 초기화

        Args:
            connection_string (str): 데이터베이스 연결 문자열
            database_name (str, optional): 데이터베이스 이름. Defaults to None.
            collection_name (str, optional): 컬렉션 이름. Defaults to None.
            timeout_ms (int, optional): 연결 타임아웃 시간. Defaults to 5000.
        """

        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.timeout_ms = timeout_ms

        # 연결 객체들
        self.client: MongoClient = None
        self._db: Database = None
        self._connection_status: bool = False

        # 초기 연결 시도
        self._initialize_connection()

    def _initialize_connection(self):
        """데이터베이스 연결 초기화"""
        try:
            self._validate_connection_string()
            self._create_client()
            self._connect_to_database()
            self._verify_connection()
            self._connection_status = True
            logger.info(f'Connected to MongoDB: {self.database_name}')

            # self.db:Database = self._client[self.database_name]
            # is_connected = self.__test_connection()
            # if not is_connected:
            #     raise ConnectionError("Failed to connect to MongoDB")
            # logger.info(f"Connected to MongoDB: {self.database_name}")

        except Exception as e:
            logger.error(f'Failed to connect to MongoDB: {e}')
            raise ConnectionError(f'Failed to connect to MongoDB: {e}')

    def _validate_connection_string(self):
        """연결 문자열 검증"""
        if not self.connection_string:
            raise ValueError('Connection string is required')
        if not self.database_name:
            raise ValueError('Database name is required')
        if not self.collection_name:
            raise ValueError('Collection name is required')

    def _create_client(self):
        """MongoClient 생성"""
        self.client: MongoClient = MongoClient(
            self.connection_string,
            serverSelectionTimeoutMS=self.timeout_ms,
            connectTimeoutMS=self.timeout_ms,
            socketTimeoutMS=self.timeout_ms,
            server_api=ServerApi('1'),
        )

    def _connect_to_database(self):
        """데이터베이스 연결"""
        if not self.client:
            raise ConnectionError('MongoClient is not initialized')
        self._db = self.client[self.database_name]

    def _verify_connection(self):
        """연결 상태 검증"""
        try:
            # 간단한 ping 테스트
            self.client.admin.command('ping')

            # 데이터베이스 접근 테스트
            collection_count = len(self._db.list_collection_names())
            logger.info(f'Database verified: {collection_count} collections found')

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise ConnectionError(f'Connection verification failed: {e}')

    def get_collection(self):
        if not hasattr(self, '_db') or self._db is None:
            raise ConnectionError('Database connection not established')
        return self._db[self.collection_name]

    def is_connected(self):
        if not self._connection_status or self.client is None:
            return False
        try:
            self.client.admin.command('ping')
            return True
        except:
            self._connection_status = False
            return False

    def reset_connection(self):
        self.client.close()
        self.client = self._initialize_connection()

    def close(self):
        if self.client:
            self.client.close()
            logger.info('MongoDB client closed')
        self._connection_status = False

    def __enter__(self):
        if not self.is_connected():
            self.reset_connection()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()
        logger.info('All contexts closed, MongoDB client closed')

    # def is_connected(self):
    #     """연결 상태 확인"""
    #     return self._client is not None and self.__test_connection()
