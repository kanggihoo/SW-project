#TODO : 쿼리에 대한 결과 반환 메서드 추가 (find 매서드)
#TODO : VectorSearch를 위한 메서드 추가 (sample_mflix.movies로 테스트 해보기) 벡터 서치를 위한 미리 생성된 
import logging
from typing import List, Dict , Callable
logger = logging.getLogger(__name__)

class FashionQueryBuilder:
    """MongoDB Atlas Search 를 사용한 쿼리/벡터 검색 파이프라인 생성
    Fashion 관련 쿼리/파이프라인 생성
    """
    
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
    def get_pipeline_for_vector_search(self, user_query:str, embedding_factory:Callable[[str], list[float]], config:Dict):
        embedding = embedding_factory(user_query)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": config["vector_index_name"],
                    "queryVector": embedding,
                    "exact": False,
                    "path": "plot_embedding",
                    "numCandidates": 100,
                    "limit": 5,
                }
            },
            {
                "$project":{
                    "fullplot": 1,
                    "type": 1,
                    "score":{
                        "$meta" : "vectorSearchScore"
                    }
                }
            }
        ]
        return pipeline 
        # results = collection.aggregate(pipeline)
        # for result in results:
        #     logger.info(result)