from pymongo import MongoClient
from pymongo.database import Database
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from .config import Config
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """DB 연결 관리 클래스 - 싱글톤 패턴과 컨텍스트 매니저 지원"""
    _instance = None
    _initialized = False
    
    # def __new__(cls, *args, **kwargs):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #     return cls._instance
    
    def __init__(self, connection_string: str, database_name: str = None, collection_name: str = None, timeout_ms: int = 5000):
        if self._initialized:
            return
        self.config = Config()
        self.connection_string = connection_string 
        self.database_name = database_name if database_name else self.config["MONGODB_LOCAL_DATABASE_NAME"]
        self.collection_name = collection_name if collection_name else self.config["MONGODB_LOCAL_COLLECTION_NAME"]
        self.timeout_ms = timeout_ms
        self._initialized = True
        self.__initialize_connection()
        
    def get_collection(self):
        if not hasattr(self, 'db') or self.db is None:
            raise ConnectionError("Database connection not established")
        return self.db[self.collection_name]
    
    def __initialize_connection(self):
        try:
            if not self.connection_string:
                raise ValueError("Connection string is required")
         
            self._client:MongoClient = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=self.timeout_ms,
                connectTimeoutMS=self.timeout_ms,
                socketTimeoutMS=self.timeout_ms,
                server_api=ServerApi('1')
            )
                 
            self.db:Database = self._client[self.database_name]
            is_connected = self.__test_connection()
            if not is_connected:
                raise ConnectionError("Failed to connect to MongoDB")
            logger.info(f"Connected to MongoDB: {self.database_name}")
            
        except Exception as e :
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    
    def __test_connection(self):
        try:
            self._client.admin.command('ping')
            collections = self.db.list_collection_names()
            logger.info(f"Connected to MongoDB: {self.database_name}. {len(collections)} collections found")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to test connection: {e}")
            return False
        except Exception as e:
            logger.error(f"예상치 못한 연결 오류: {e}")
            return False
    
    def __enter__(self):
        try:            
            if self._client is None:
                logger.warning("Connection not initialized in __enter__, attempting to reconnect...")
                self.__initialize_connection()
                # 연결 상태 재확인
                if not self.__test_connection():
                    raise ConnectionError("Failed to establish connection in context manager")
            return self
        except Exception as e:
            logger.error(f"Failed to enter context: {e}")
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        self._client.close()
        logger.info("All contexts closed, MongoDB client closed")
    
    
    def is_connected(self):
        """연결 상태 확인"""
        return self._client is not None and self.__test_connection()


