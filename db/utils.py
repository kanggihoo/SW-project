import requests
import os
from pymongo.collection import Collection

def get_embedding_with_jina(texts: list[str] ,
                            model_name:str="jina-embeddings-v3" ,
                            task="retrieval.query",
                            dimensions:int=1024,
                            embedding_type :str = "float" ,
                            api_key:str|None=None) -> list[float|int]:
    """주어진 text를 임베딩 하는 함수
    Args:
        texts (list[str]): 임베딩 할 텍스트 리스트
        dimensions (int, optional): 임베딩 차원. Defaults to 1024.(32~1024)
        embedding_type (str, optional): 임베딩 타입. Defaults to "float", ["ubinary" , "binary" ]
        model_name (str, optional): 임베딩 모델 이름. Defaults to "jina-embeddings-v3".
        api_key (str | None, optional): _description_. Defaults to None.

    Returns:
        list[float]: 임베딩 결과 리스트
    """
    url = 'https://api.jina.ai/v1/embeddings'
    if not api_key:
        api_key = os.getenv("JINA_API_KEY")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    data = {
        "model": model_name,
        "task": task,
        "embedding_type": embedding_type,
        "dimensions": dimensions,
        "input": texts
    }
    response = requests.post(url, json=data, headers=headers)
    print(response.json())
    return [emb.get("embedding") for emb in response.json().get("data")]


class IndexManager:
    """인덱스 관리"""
    
    def __init__(self, collection):
        self.collection = collection
    
    def create_unique_indexes(self):
        # 이메일 유니크 인덱스
        self.collection.create_index("email", unique=True)
        
    def create_compound_indexes(self):
        # 복합 인덱스
        self.collection.create_index([("status", 1), ("created_at", -1)])
    
    #멀티 필드 인덱스 생성 
    def create_multi_field_indexes(self, fields: list[str]):
        pass
    
class VectorIndexManager:
    """벡터 인덱스 관리"""
    
    def __init__(self, collection):
        self.collection = collection
    
    def create_vector_index(self, fields: list[str]):
        pass


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(get_embedding_with_jina(dimensions=32,texts="heell@@"))
