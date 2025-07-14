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


def get_embedding_with_openai(texts: list[str] ,
                              model_name:str="text-embedding-3-small" ,
                              api_key:str|None=None) -> list[float]:
    """주어진 text를 임베딩 하는 함수
    """
    from openai import OpenAI
    client = OpenAI()
    response = client.embeddings.create(
        input=texts,
        model=model_name
    )
    return [emb.embedding for emb in response.data] 

def get_embedding_with_gemini(texts: str|list[str] ,
                              model_name:str="text-embedding-004" ,
                              api_key:str|None=None) -> list[float]:
    """genai의 github 참조 , 반환값은 result.embeddings 하면 리스트 형태로 pydantic으로 정의된 클래스 반환 (ContentEmbedding)
     - 실제 list에 담긴 벡터값 접근하려면 .values 로접근
     - 768 차원벡터 반환 
    """
    from google import genai
    client = genai.Client()

    result = client.models.embed_content(
            model=model_name,
            contents=texts,
            # config=types.EmbedContentConfig(
            #   task_type="retrieval_document",
            #   title=title
            # )
    )
    return [emb.values for emb in result.embeddings]


# TODO: 벡터값 Binary 형태로 저장
from bson.binary import Binary 
from bson.binary import BinaryVectorDtype

# Define a function to generate BSON vectors
def generate_bson_vector(vector, vector_dtype):
    """벡터값을 BSON 형태로 변환"""
    # Generate BSON vector from the sample float32 embedding
    # bson_float32_embedding = generate_bson_vector(embedding, BinaryVectorDtype.FLOAT32)
    return Binary.from_vector(vector, vector_dtype)


