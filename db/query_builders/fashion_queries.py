#TODO : 쿼리에 대한 결과 반환 메서드 추가 (find 매서드)
#TODO : VectorSearch를 위한 메서드 추가 (sample_mflix.movies로 테스트 해보기) 벡터 서치를 위한 미리 생성된 
import logging
from typing import List, Dict , Callable
logger = logging.getLogger(__name__)

'''
원하는 데이터를 가져오기 위해서 mongodb 쿼리로 변환

'''
class FashionQueryBuilder:
    """MongoDB Atlas Search 를 사용한 쿼리/벡터 검색 파이프라인 생성
    Fashion 관련 쿼리/파이프라인 생성
    """
    def __init__(self):
        pass

    def caption_status_filter(self , caption_status: str) -> dict:
        return {"caption_info.caption_status": caption_status}
    
    # def get_active_users_pipeline(self) -> List[Dict]:
    #     return [
    #         {"$match": {"status": "active"}},
    #         {"$sort": {"created_at": -1}},
    #         {"$limit": 100}
    #     ]
    
    # def get_user_stats_pipeline(self, user_id: str) -> List[Dict]:
    #     return [
    #         {"$match": {"_id": user_id}},
    #         {"$lookup": {
    #             "from": "orders",
    #             "localField": "_id",
    #             "foreignField": "user_id",
    #             "as": "orders"
    #         }},
    #         {"$addFields": {
    #             "order_count": {"$size": "$orders"},
    #             "total_spent": {"$sum": "$orders.amount"}
    #         }}
    #     ]
    def vector_search_pipeline(self, user_query:str, embedding_factory:Callable[[str], list[float]]):
        embedding = embedding_factory(user_query)[0]
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "tmp",
                    "queryVector": embedding,
                    "exact": False,
                    "path": "embedding.comprehensive_description.vector",
                    "numCandidates": 100,
                    "limit": 5,
                }
            },
            {
                "$project":{
                    "product_id":1,
                    "main_category":1,
                    "sub_category":1,
                    # "deep_caption":1,
                    "representative_assets":1,
                    # "caption_info":1,
                    "score":{
                        "$meta" : "vectorSearchScore"
                    },   
                }
            }
            # },
            # {
            #     "$replaceRoot": { "newRoot": { "$mergeObjects": ["$document", { "score": "$score" }] } }
            #     # 'document' 필드를 루트로 승격하고, 'score' 필드를 병합
            #     # 이렇게 하면 'score'가 최상위 필드로 포함된 원래 문서 형태가 됩니다.
            # }
        ]
        return pipeline 
        # results = collection.aggregate(pipeline)
        # for result in results:
        #     logger.info(result)