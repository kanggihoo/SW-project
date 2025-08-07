import os
from dotenv import load_dotenv

load_dotenv()
class Config_(dict):
    def __init__(self):
        _mongodb_local_dict ={
            "MONGODB_LOCAL" : {
                "MONGODB_LOCAL_DATABASE_NAME": "fashion_db",
                "MONGODB_LOCAL_COLLECTION_NAME": "products",
                "MONGODB_LOCAL_CONNECTION_STRING": "mongodb://localhost:27017/"
            }
        }
        _mongodb_atlas_dict = {
            "MONGODB_ATLAS" : {
                "MONGODB_ATLAS_DATABASE_NAME": "fashion_db",
                "MONGODB_ATLAS_COLLECTION_NAME": "products",
                "MONGODB_ATLAS_CONNECTION_STRING": os.getenv("MONGODB_ATLAS_URI")
            }
        }

        # 연결 타임아웃 설정
        _connection_settings = {
            "CONNECTION_SETTINGS" : {
                "CONNECTION_TIMEOUT_MS":  5000,
                "SERVER_SELECTION_TIMEOUT_MS": 5000,
                "SOCKET_TIMEOUT_MS": 5000
            }
        }
        
        # 벡터 검색 설정
        _vector_search_settings = {
            "VECTOR_SEARCH_SETTINGS" : {
                "DEFAULT_VECTOR_INDEX": "tmp",
                "EMBEDDING_FIELD_PATH": "embedding.comprehensive_description.vector",
                "EMBEDDING_DIMENSIONS": 1024,
                "DEFAULT_SIMILARITY": "cosine",
                "DEFAULT_NUM_CANDIDATES": 100,
                "DEFAULT_LIMIT": 10,
                "DEFAULT_PROJECT_FIELDS": {
                    "product_id":1,
                    "category_main":1,
                    "category_sub":1,
                    "representative_assets":1,
                }
            }
        }
        
        # 모든 설정 통합
        self.update(_mongodb_local_dict)
        self.update(_mongodb_atlas_dict)
        self.update(_connection_settings)
        self.update(_vector_search_settings)
    
    def get_atlas_config(self):
        return self.get("MONGODB_ATLAS")
    
    def get_local_config(self):
        return self.get("MONGODB_LOCAL")
    
    def get_vector_search_config(self):
        return self.get("VECTOR_SEARCH_SETTINGS")
    
    def get_connection_config(self):
        return self.get("CONNECTION_SETTINGS")
    
# 싱글톤 패턴 적용

_config_instance = None

def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = Config_()
    return _config_instance

# 기존 코드와의 호환성 
Config = get_config

