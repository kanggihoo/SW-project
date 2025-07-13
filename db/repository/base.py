from abc import ABC
from typing import Dict, List, Optional, Any
from db.config.database import DatabaseManager
from db.config.config import Config
from pymongo.collection import Collection
import os 
class BaseRepository(ABC):
    """기본 Repository 클래스"""
    def __init__(self, collection_string: str):
        self.db_manager: DatabaseManager = DatabaseManager(connection_string=os.getenv("MONGODB_ATLAS_URI"))
        self.collection: Collection = self.db_manager.get_collection()
        self.collection_string = collection_string
    
    # 공통 CRUD 메서드들
    def find_by_id(self, doc_id: str) -> Optional[Dict]:
        return self.collection.find_one({"_id": doc_id})
    
    def find_all(self, filter_dict: Dict|None = None) -> Any:
        filter_dict = filter_dict or {}
        return self.collection.find(filter_dict)
    
    def create(self, document: Dict) -> str:
        result = self.collection.insert_one(document)
        return str(result.inserted_id)
    
    def update_by_id(self, doc_id: str, update_data: Dict) -> bool:
        result = self.collection.update_one(
            {"_id": doc_id}, 
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    def delete_by_id(self, doc_id: str) -> bool:
        result = self.collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0