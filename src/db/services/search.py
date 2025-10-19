# from app.config.dependencies import S3ManagerDep , RepositoryDep
import asyncio
import time
from typing import TypedDict

from fastapi import HTTPException
from loguru import logger

from db.repository.fashion_async import AsyncFashionRepository

# from aws.aws_manager import S3Manager
from embedding.gemini import GeminiEmbedding
from query_analyzer.multi_step_analyzer import MultiStepAnalyzer


class SearchResult(TypedDict):
    product_id: str
    comprehensive_description: str
    main_category: str
    sub_category: str
    score: float


class SearchResultItem(TypedDict):
    query: str
    data: list[SearchResult]
    total_count: int
    message: str


class SearchService:
    def __init__(
        self,
        repository: AsyncFashionRepository,
        query_analyzer: MultiStepAnalyzer,
        embedding: GeminiEmbedding,
    ):
        self.repository = repository
        self.embedding = embedding
        self.query_analyzer = query_analyzer

    async def search_by_query(self, query: str, limit: int = 1) -> SearchResultItem:
        """
        쿼리를 분석하고, 분석된 결과를 기반으로 벡터 검색을 수행합니다.
        """
        try:
            # TODO: 에러 처리?
            # 1. Query Analyzer를 이용한 쿼리 분석
            start_time = time.perf_counter()
            analyzed_results = await self.query_analyzer.analyze_and_format(query)
            logger.info(f'쿼리 분석결과 analyzed_results: {analyzed_results}')
            logger.info(f'쿼리 분석결과 소요시간: {time.perf_counter() - start_time}')

            if analyzed_results:
                rewritten_query_list = [item['rewritten_query'] for item in analyzed_results]
                pre_filter_list = [{k: v for k, v in item.items() if k != 'rewritten_query' and v is not None and v} for item in analyzed_results]
            else:
                # 분석 결과가 없으면 원래 쿼리로 검색
                rewritten_query_list = [query]
                pre_filter_list = [None]

            logger.info(f'rewritten_query_list: {rewritten_query_list}')
            logger.info(f'pre_filter_list: {pre_filter_list}')

            # 2. 임베딩 생성
            start_time = time.perf_counter()
            embeddings = await self.embedding.get_embedding(rewritten_query_list)
            logger.info(f'임베딩 생성 소요시간: {time.perf_counter() - start_time}')

            if not embeddings:
                raise ValueError('Embedding generation failed')

            logger.debug(f'embeddings: {len(embeddings)} , dim: {len(embeddings[0])}')

            # 3. 병렬 벡터 검색 실행
            start_time = time.perf_counter()
            tasks = []
            for i, (emd, pf) in enumerate(zip(embeddings, pre_filter_list, strict=False)):
                logger.info(f'쿼리 : {rewritten_query_list[i]} 필터 : {pf} , limit : {limit} 으로 검색 시작')
                task = self.repository.vector_search(embedding=emd, limit=limit, pre_filter=pf)
                tasks.append(task)

            vector_search_results = await asyncio.gather(*tasks)
            logger.info(f'벡터 검색 소요시간: {time.perf_counter() - start_time}')
            logger.info('vector_search_results completed')

            processed_results: list[SearchResult] = self._parse_vector_search_result(vector_search_results)

            return {
                'query': query,
                'data': processed_results,
                'total_count': len(processed_results),
                'message': 'Search completed successfully',
            }

        except Exception as e:
            logger.error(f'Error in search_by_query: {e}')
            raise HTTPException(status_code=500, detail=f'An unexpected error occurred during search: {e}') from e

    async def search_by_single_query_skip_query_analysis(self, query: str, limit: int, filter: dict) -> dict:
        try:
            rewritten_query_list = [query]
            pre_filter_list = [filter]

            logger.info(f'rewritten_query_list: {rewritten_query_list}')
            logger.info(f'pre_filter_list: {pre_filter_list}')

            # 2. 임베딩 생성
            embeddings = await self.embedding.get_embedding(rewritten_query_list)

            if not embeddings:
                raise ValueError('Embedding generation failed')

            vector_search_result = await self.repository.vector_search(embedding=embeddings[0], limit=limit, pre_filter=filter)

            logger.info('vector_search_results completed')

            processed_results = self._parse_vector_search_result([vector_search_result])

            return {
                'query': query,
                'data': processed_results,
                'total_count': len(processed_results),
                'message': 'Search completed successfully',
            }
        except Exception as e:
            logger.error(f'Error in search_by_single_query_skip_query_analysis: {e}')
            raise HTTPException(status_code=500, detail=f'An unexpected error occurred during search: {e}') from e

    def _parse_vector_search_result(self, vector_search_results: list[dict]) -> list[SearchResult]:
        processed_results = []
        for vector_search_result in vector_search_results:  # 각 임베딩에 대한 벡터 검색결과 순환
            for item in vector_search_result:  # 벡터 검색으로 변환된 limit 만큼의 결과 순환
                processed_results.append(
                    {
                        'product_id': item['_id'],
                        'comprehensive_description': item['products']['captions']['comprehensive_description'],
                        'main_category': item['product_skus']['main_category'],
                        'sub_category': item['product_skus']['sub_category'],
                        'score': item['score'],
                    }
                )
        return processed_results

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
