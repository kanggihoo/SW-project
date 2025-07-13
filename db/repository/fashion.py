from .base import BaseRepository

import os
class FashionRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_string=os.getenv("MONGODB_COLLECTION_NAME"))
    #TODO : 데이터 삽입 , 임베딩 벡터를 새로운 필드명으로 추가(업데이트) , 
    def find_by_id(self, doc_id: str) -> Optional[Dict]:
        return self.collection.find_one({"_id": doc_id})
    
    def find_all(self, filter_dict: Dict = None) -> Any:
        filter_dict = filter_dict or {}
        return self.collection.find(filter_dict)