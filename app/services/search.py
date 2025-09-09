# from app.config.dependencies import S3ManagerDep , RepositoryDep
import logging
from typing import Any, Optional, List
from db.repository.fashion_async import AsyncFashionRepository
from aws.aws_manager import S3Manager
from embedding.embedding import JinaEmbedding
from query_analyzer.multi_step_analyzer import MultiStepAnalyzer
import asyncio
from fastapi import HTTPException
logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, s3_manager: S3Manager, repository: AsyncFashionRepository, jina_embedding: JinaEmbedding, query_analyzer: MultiStepAnalyzer):
        self.s3_manager = s3_manager
        self.repository = repository
        self.jina_embedding = jina_embedding
        self.query_analyzer = query_analyzer

    async def search_by_query(self, query: str, limit: int = 1) -> dict:
        """
        쿼리를 분석하고, 분석된 결과를 기반으로 벡터 검색을 수행합니다.
        """
        try:
            #TODO: 에러 처리? 
            # 1. Query Analyzer를 이용한 쿼리 분석
            analyzed_results = await self.query_analyzer.analyze_and_format(query)
            logger.info(f"analyzed_results: {analyzed_results}")

            if analyzed_results:
                rewritten_query_list = [item["rewritten_query"] for item in analyzed_results]
                pre_filter_list = [{k:v for k,v in item.items() if k != "rewritten_query" and v is not None and v} for item in analyzed_results]
            else:
                # 분석 결과가 없으면 원래 쿼리로 검색
                rewritten_query_list = [query]
                pre_filter_list = [None]

            logger.info(f"rewritten_query_list: {rewritten_query_list}")
            logger.info(f"pre_filter_list: {pre_filter_list}")
            
            # 2. 임베딩 생성
            embedding_data = await self.jina_embedding.get_embedding(rewritten_query_list)
            embeddings = embedding_data.get("embeddings", [])
            
            if not embeddings:
                raise ValueError("Embedding generation failed")

            logger.info(f"embeddings: {len(embeddings)} , dim: {len(embeddings[0])}")
            
            # 3. 병렬 벡터 검색 실행
            tasks = []
            for emd, pf in zip(embeddings, pre_filter_list):
                task = self.repository.vector_search(embedding=emd, limit=limit, pre_filter=pf)
                tasks.append(task)
            
            vector_search_results = await asyncio.gather(*tasks)
            
            logger.info(f"vector_search_results completed")
            
            # 4. 결과 처리 및 S3 URL 생성
            processed_results = []
            for result_list in vector_search_results:
                for item in result_list:

                    item["image_url"] = self._generate_representative_image_url(item)
                    processed_results.append(item)
            
            logger.info(f"Processed {len(processed_results)} results for query: '{query}'")

            return {
                "query": query,
                "data": processed_results,
                "total_count": len(processed_results),
                "message": "Search completed successfully"
            }

        except Exception as e:
            logger.error(f"Error in search_by_query: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred during search: {e}") from e
 
        
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
            
            '''
            대표이미지 : product_skus.image_urls[0]
            product_id = products.product_id or data.get("_id")
            main_category = products.skus.main_category 
            sub_category = products.skus.sub_category

            
            '''
            representative_image = data.get("product_skus")["image_urls"][0]
            product_id = data["_id"]
            main_category = data.get("product_skus")["main_category"]
            sub_category = data.get("product_skus")["sub_category"]
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