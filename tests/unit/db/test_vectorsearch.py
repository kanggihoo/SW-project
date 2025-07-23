
from pymongo.operations import SearchIndexModel
from db.config.database import DatabaseManager
from db import create_fashion_repo
from embedding import get_embedding_with_jina
import logging 
from dotenv import load_dotenv
import os
import pytest
import sys

import numpy as np
from typing import List, Tuple
import math

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """두 벡터 간의 코사인 유사도 계산"""
    # 벡터를 numpy 배열로 변환
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    # 코사인 유사도 공식: (A·B) / (|A| * |B|)
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    # 0으로 나누기 방지
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    
    return dot_product / (norm_v1 * norm_v2)


@pytest.fixture(scope="session" , autouse=True)
def setup():
    load_dotenv()
    root = logging.getLogger()
    root.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def config():
    return {
        "vector_index_name": "tmp",
        "database_name": "fashion_db",
        "collection_name": "products"
    }

@pytest.fixture(scope="session")
def db(config):
    return create_fashion_repo(use_atlas=True)

# @pytest.fixture()
# def embedding_factory():
#     def _create_embedding(text):
#         from openai import OpenAI
#         client = OpenAI()
#         response = client.embeddings.create(
#             input=text,
#             model="text-embedding-3-small"
#         )
#         embedding = response.data[0].embedding
#         return embedding
#     return _create_embedding


# def test_connection(client):
#     assert client.is_connected()
#     logger.info(f"Connected to MongoDB: {client.database_name}")

# def test_create_vector_index(client , config):
#     collection = client.get_collection()
#     search_index_model = SearchIndexModel(
#         definition = {
#         "fields":[
#             {
#                 "type": "vector",
#                 "path": "plot_embedding",
#                 "numDimensions": 1536,
#                 "similarity": "cosine",
#                 "quantization": "none",
#                 "hnswOptions": {
#                     "numEdgeCandidates": 100
#                 }
#             }
#         ]
#         },
#         name=config["vector_index_name"],
#         type="vectorSearch"
#     )
#     collection.create_search_index(model=search_index_model)

# def test_drop_vector_index(client , config):
#     collection = client.get_collection()
#     collection.drop_search_index(config["vector_index_name"])

# def test_update_embedding(client , embedding_factory , config):
#     from bson.objectid import ObjectId
#     collection = client.get_collection()
#     _id = ObjectId("573a1390f29313caabcd5293")
#     plot = "부드러운 아이보리/베이지 톤의 플리츠 미디 스커트입니다. 허리 밴딩 처리로 편안하며, 가볍고 통기성 좋은 소재로 봄여름 시즌에 시원하게 착용하기 좋습니다. 자연스러운 주름 디테일이 여성스러운 실루엣을 연출하며, 안감이 있어 비침 걱정 없이 활동하기 편합니다. 다양한 상의와 매치하여 데일리룩부터 오피스룩까지 활용하기 좋습니다."
#     document = collection.find_one({"_id": _id})
#     old_plot = document.get("fullplot")
#     logger.info(old_plot)
#     new_embedding = embedding_factory(plot)
#     collection.update_one(
#         {"_id": _id},
#         {
#             "$set": {
#                 "plot_embedding": new_embedding,
#                 "fullplot": plot
#             }
#         }
#     )
    


def test_vector_qeury(db ):
    results = db.vector_search("부드러운 아이보리 , 허리 밴딩 처리 , 시원하게 착용하기")
    print(results)
    





