import os
import aiohttp
from typing import Any
class JinaEmbedding:
    def __init__(self,
                 model_name:str="jina-embeddings-v3" ,
                 task:str="retrieval.query" ,
                 dimensions:int=1024,
                 embedding_type :str = "float" ,
                 api_key:str|None=None):
        self.model_name = model_name
        self.task = task
        self.dimensions = dimensions
        self.embedding_type = embedding_type
        self._init_data()
        
    def _init_data(self):
        """주어진 text를 임베딩 하는 함수
        Args:
            dimensions (int, optional): 임베딩 차원. Defaults to 1024.(32~1024)
            embedding_type (str, optional): 임베딩 타입. Defaults to "float", ["ubinary" , "binary" ]
            model_name (str, optional): 임베딩 모델 이름. Defaults to "jina-embeddings-v3".
            api_key (str | None, optional): _description_. Defaults to None.
        Returns:
            list[float]: 임베딩 결과 리스트
        """
        api_key = os.getenv("JINA_API_KEY")
        
        self._url = 'https://api.jina.ai/v1/embeddings'

        self._headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        self._data = {
            "model": self.model_name,
            "task": self.task,
            "embedding_type": self.embedding_type,
            "dimensions": self.dimensions,
        }
        
    async def get_embedding(self, texts: list[str]|str ,  session:aiohttp.ClientSession) -> dict[str , Any]:
        """주어진 text를 임베딩 하는 함수
        Args:
            texts (list[str]|str): 임베딩 할 텍스트 리스트 또는 문자열
            session (aiohttp.ClientSession): 세션
        Returns:
            dict[str , Any]: 임베딩 결과 딕셔너리
            - model_version (str): 모델 이름
            - dimensions (int): 임베딩 차원
            - embeddings (list[float]): 임베딩 결과 리스트
        """
        data = {**self._data, "input": texts}
        async with session.post(self._url, json=data, headers=self._headers, timeout=30) as response:
            response.raise_for_status()
            response_json = await response.json()
            model_name = response_json.get("model")
            embeddings = [emb.get("embedding") for emb in response_json.get("data")]
            
            return {
                "model_name": model_name,
                "dimensions": self.dimensions,
                "embeddings": embeddings,
            }
                    
    
async def main():
    jina_embedding = JinaEmbedding()
    async with aiohttp.ClientSession() as session:
        embedding = await jina_embedding.get_embedding(["Hello, world!"], session)
        print(embedding)

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
    