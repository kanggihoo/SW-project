import numpy as np 
from numpy.linalg import norm

def normalize_vector(vector: list[float]) -> np.ndarray:
    embedding_np = np.array(vector)
    return embedding_np / norm(embedding_np)

    