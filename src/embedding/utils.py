import numpy as np 
from numpy.linalg import norm

def normalize_vector(vector: list[float]) -> np.ndarray:
    embedding_np = np.array(vector)
    return embedding_np / norm(embedding_np , axis=1)[:, np.newaxis]



# TODO: 벡터값 Binary 형태로 저장
from bson.binary import Binary 
from bson.binary import BinaryVectorDtype
def generate_bson_vector(vector, vector_dtype):
    """벡터값을 BSON 형태로 변환"""
    # Generate BSON vector from the sample float32 embedding
    return Binary.from_vector(vector, vector_dtype)
