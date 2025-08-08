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
