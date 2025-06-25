import requests
from langchain_community.embeddings import JinaEmbeddings
from numpy import dot
from numpy.linalg import norm
from PIL import Image

from dotenv import load_dotenv

load_dotenv()


# multimodal_embeddings = JinaEmbeddings(
#     model_name="jina-clip-v2",
#     dimensions=1020,         # 원하는 차원 설정
#     normalized=False,  
    
# )


# import requests
# import json

# url = 'https://api.jina.ai/v1/embeddings'
# headers = {
#     'Content-Type': 'application/json',
#     'Authorization': 'Bearer jina_23824b8c443f414daf25f87a02ab249cyoU8pzmqQc-bI4DqKeT3y3VZa935'
# }
# data = {
#     "model": "jina-clip-v2",
#     "dimensions": 1020,
#     "normalized": False,
#     "input": [
#         {
#             "text": "A beautiful sunset over the beach"
#         },
#         {
#             "text": "Un beau coucher de soleil sur la plage"
#         },
#     ]
# }

# response = requests.post(url, headers=headers, json=data)
# embeddings = response.json()['data']
# print(len(embeddings))
# e = embeddings[0]["embedding"]
# print(len(e))
# print(e[:10])






