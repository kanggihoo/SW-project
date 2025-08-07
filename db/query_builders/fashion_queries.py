import logging
from typing import List, Dict , Callable, Optional
from db.config.config import Config


'''
원하는 데이터를 가져오기 위해서 mongodb 쿼리로 변환
'''
class FashionQueryBuilder:
    """MongoDB Atlas Search 를 사용한 쿼리/벡터 검색 파이프라인 생성
    Fashion 관련 쿼리/파이프라인 생성
    """
    def __init__(self):
        self.config = Config()
        self.vector_search_config = self.config.get_vector_search_config()
        

    # def caption_status_filter(self , caption_status: str="COMPLETED") -> dict:
    #     return {"caption_info.caption_status": caption_status}

    def data_status_filter(self , data_status:str) -> dict:
        if data_status not in ["CR_SUB", "CR_DET", "IMG_DOWN", "AWS_UPL", "RE_COMP", "CA_COMP", "EB_COMP"]:
            raise ValueError(f"data_status의 값이 올바르지 않습니다. : {data_status} \
                             \n 허용된 값 : CR_SUB, CR_DET, IMG_DOWN, AWS_UPL, RE_COMP, CA_COMP, EB_COMP")
        return {"data_status": data_status}
    
    #TODO : 벡터 검색 효율성 및 정확성을 위한 사전 필터링 인자 추가 
    def vector_search_pipeline(self,
                               embedding:list[float],
                               limit:Optional[int],
                               pre_filter: Optional[Dict] = None,
                               num_candidates:Optional[int]=None,
                               index_name:Optional[str] = None,
                               embedding_field_path:Optional[str] = None)->List[Dict]:
        """
        Vector Search 파이프라인 생성

        Args:
            embedding list[float]]): 사용자 쿼리에 대한 임베딩 벡터 
            pre_filter (Optional[Dict], optional): 사전 필터링 조건. Defaults to None.
            num_candidates (int, optional): 후보 개수. Defaults to 100.
            index_name (str, optional): 인덱스 이름. Defaults to None.
            embedding_field_path (str, optional): 임베딩 필드 경로. Defaults to None.
            limit (int, optional): 결과 개수. Defaults to 10.

        Returns:
            List[Dict]: 검색 결과(유사도 점수 높은 순)
        """
        
        # 기본 설정값 설정
        index_name = index_name or self.vector_search_config.get("DEFAULT_VECTOR_INDEX")
        embedding_field_path = embedding_field_path or self.vector_search_config.get("EMBEDDING_FIELD_PATH")
        num_candidates = num_candidates or self.vector_search_config.get("DEFAULT_NUM_CANDIDATES")
        if len(embedding) != self.vector_search_config.get("EMBEDDING_DIMENSIONS"):
            raise ValueError(f"embedding 의 차원이 올바르지 않습니다. : {len(embedding)} \
                             \n 허용된 차원 : {self.vector_search_config.get('EMBEDDING_DIMENSIONS')}")

        vector_search_stage = {
            "index": index_name,
            "queryVector": embedding,
            "exact": False,
            "path": embedding_field_path,
            "numCandidates": num_candidates,
            "limit": limit,
        }

        if pre_filter:
            vector_search_stage["filter"] = pre_filter

        pipeline = [
            {
                "$vectorSearch": vector_search_stage
            }
        ]
        # 기본 프로젝션값 설정 
        project = {
            "$project":self.vector_search_config.get("DEFAULT_PROJECT_FIELDS")
        }
        # 유사도 점수 추가 
        project["$project"]["score"] = {
            "$meta" : "vectorSearchScore"
        }
        pipeline.append(project)
        return pipeline

    def hybrid_search_pipeline(self,
                               user_query:str,
                               embedding_factory:Callable[[str], list[float]],
                               num_candidates:int=100,
                               index_name:str = None,
                               embedding_field_path:str = None,
                               limit:int=10)->List[Dict]:
        ...