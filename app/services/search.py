# from app.config.dependencies import S3ManagerDep , RepositoryDep
import logging
from typing import Any

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self , s3_manager , repository):
        self.s3_manager = s3_manager
        self.repository = repository

    def vector_search_one(self, query: str)->dict:
        """
        벡터 검색 결과 중 가장 유사도가 높은 데이터를 반환
        Args:
            query (str): 검색 쿼리
            limit (int, optional): 검색 결과 개수. Defaults to 5.
        Returns:
            result : dict
                query : str
                data : dict
                total_count : int
                message : str

        """
        result = {"query" : query , "data" : {} , "total_count" : 0 , "message" : "Search completed successfully"}
        try:
            max_similarity_data= self.repository.vector_search(query , limit = 1)[0]
            representative_image_url = self._generate_representative_image_url(max_similarity_data)
            max_similarity_data["image_url"] = representative_image_url
            result["data"] = max_similarity_data
            result["total_count"] = 1
            result["message"] = "Search completed successfully"
            return result
        except Exception as e:
            logger.error(f"Vector search failed for query '{query}': {e}")
            result["message"] = "Search failed"
            return result
        
    # def vector_search_multiple(self, query: str, limit: int = None) -> dict[str, Any]:
    #     """
    #     벡터 검색으로 여러 결과 반환
        
    #     Args:
    #         query: 검색 쿼리
    #         limit: 결과 개수 제한
            
    #     Returns:
    #         검색 결과 딕셔너리 (여러 결과 포함)
    #     """
    #     results = {"query" : query , "data" : [] , "total_count" : 0 , "message" : "Search completed successfully"}
    #     try:
    #         search_results = self.repository.vector_search(query, limit)
            
    #         # 모든 결과 처리
    #         processed_results = []
    #         for result in search_results:
    #             result["image_url"] = self._generate_representative_image_url(result)
    #             result["query"] = query
    #             processed_results.append(result)
            
    #         results["data"] = processed_results
    #         results["total_count"] = len(processed_results)
    #         return results
            
    #     except Exception as e:
    #         logger.error(f"Multiple vector search failed for query '{query}': {e}")
    #         results["message"] = "Search failed"
    #         return results

    #TODO : 비동기 처리, 및 어떤 이미지를 대표 이미지로 선정할 것인지 고민해보기 
    def _generate_representative_image_url(self , data:dict)->str:
        try:
            
    
            representative_image = data.get("representative_assets")["color_variant"][0]
            product_id = data.get("product_id")
            main_category = data.get("category_main")
            sub_category = data.get("category_sub")
            if not all([main_category , sub_category , product_id , representative_image]):
                logger.warning("Missing required fields for S3 key generation")
                return None
            
            s3_key = f"{main_category}/{sub_category}/{product_id}/{representative_image}"
            return self._generate_s3_url(s3_key)
        
        except Exception as e:
            logger.error(f"Error parsing representative image: {e}")
            return None


    def _generate_s3_url(self , s3_key:str):
        s3_url = self.s3_manager.generate_presigned_url(s3_key)
        return s3_url
        
    
    
