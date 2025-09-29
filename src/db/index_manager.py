from typing import Any

from loguru import logger
from pymongo.collection import Collection
from pymongo.operations import ASCENDING, SearchIndexModel


def create_indexes(collection: Collection):
    """검색 성능 향상을 위한 인덱스 생성"""
    try:
        # 기본 인덱스들
        indexes = [
            # # 상품 ID - 유니크 인덱스
            # ("product_id", ASCENDING),
            # 카테고리 필터링용
            [('category_main', ASCENDING), ('category_sub', ASCENDING)],
            # # 성별 필터링용
            # ("gender", ASCENDING),
            # # 가격 범위 검색용
            # ("product_price", ASCENDING),
            # # 평점 정렬용
            # ("avg_rating", DESCENDING),
            # # 리뷰 수 정렬용
            # ("review_count", DESCENDING),
            # # 좋아요 수 정렬용
            # ("num_likes", DESCENDING),
            # # 생성 시간 정렬용
            # ("created_at", DESCENDING),
            # 크롤링 상태 확인용
            # ("success_status", ASCENDING),
        ]

        for index in indexes:
            if isinstance(index, tuple):
                collection.create_index([index])
            else:
                collection.create_index(index)

        # # 상품 ID를 유니크 인덱스로 설정
        # self.collection.create_index("product_id", unique=True)

        logger.info('인덱스 생성 완료')

    except Exception as e:
        logger.warning(f'인덱스 생성 중 오류: {e}')


class IndexManager:
    """인덱스 관리"""

    def __init__(self, collection):
        self.collection = collection

    def create_unique_indexes(self):
        # 이메일 유니크 인덱스
        self.collection.create_index('email', unique=True)

    def create_compound_indexes(self):
        # 복합 인덱스
        self.collection.create_index([('status', 1), ('created_at', -1)])

    # 멀티 필드 인덱스 생성
    def create_multi_field_indexes(self, fields: list[str]):
        pass


class VectorIndexManager:
    """벡터 인덱스 관리"""

    def __init__(self, collection: Collection):
        self.collection: Collection = collection

    def create_vector_index(
        self,
        index_name: str,
        field_names: list[str] | str,
        dimensions: int,
        similarity: str = 'cosine',
        quantization: str = 'None',
        num_edge_candidates: int = 100,
    ):
        search_index_model = SearchIndexModel(
            definition={
                'fields': [
                    {
                        'type': 'vector',
                        'path': 'plot_embedding',
                        'numDimensions': 1536,
                        'similarity': 'cosine',
                        'quantization': 'none',
                        'hnswOptions': {'numEdgeCandidates': 100},
                    }
                ]
            },
            name=index_name,
            type='vectorSearch',
        )

        self.collection.create_search_index(model=search_index_model)

    def drop_vector_index(self, index_name: str) -> dict[str, Any]:
        """벡터 인덱스 삭제

        Args:
            index_name (str): 삭제할 인덱스 이름

        Returns:
            dict[str, Any]: 작업 결과 정보
            {
                "success": bool,
                "message": str,
                "error_code": Optional[int],
                "error_type": Optional[str]
            }
        """

        result = {
            'success': False,
            'message': '',
            'error_type': None,
        }

        try:
            # 입력 검증
            if not index_name or not isinstance(index_name, str):
                result['message'] = '인덱스 이름이 유효하지 않습니다.'
                result['error_type'] = 'ValidationError'
                logger.error(f'Invalid index name: {index_name}')
                return result

            # 인덱스 존재 여부 확인 (선택사항)
            if not self._index_exists(index_name):
                result['message'] = f"인덱스 '{index_name}'이 존재하지 않습니다."
                result['error_type'] = 'IndexNotFound'
                logger.warning(f"Index '{index_name}' does not exist")
                return result

            # 인덱스 삭제 실행
            logger.info(f"인덱스 '{index_name}' 삭제를 시작합니다...")
            self.collection.drop_search_index(index_name)

            result['success'] = True
            result['message'] = f"인덱스 '{index_name}'이 성공적으로 삭제되었습니다."
            logger.info(f'Successfully dropped index: {index_name}')

        except Exception as e:
            # 예상치 못한 기타 오류
            result['error_type'] = 'UnexpectedError'
            result['message'] = f'예상치 못한 오류가 발생했습니다: {str(e)}'
            logger.error(f'Unexpected error dropping index {index_name}: {e}', exc_info=True)

        return result

    def _index_exists(self, index_name: str) -> bool:
        """
        인덱스가 존재하는지 확인합니다.

        Args:
            index_name (str): 확인할 인덱스 이름

        Returns:
            bool: 인덱스 존재 여부
        """
        try:
            # MongoDB Atlas Search 인덱스 목록 조회
            indexes = list(self.collection.list_search_indexes())
            return any(idx.get('name') == index_name for idx in indexes)
        except Exception as e:
            logger.warning(f'인덱스 존재 여부 확인 중 오류: {e}')
            return True  # 확인할 수 없으면 삭제 시도

    def drop_vector_index_safe(self, index_name: str, ignore_if_not_exists: bool = True) -> bool:
        """
        안전하게 벡터 인덱스를 삭제합니다 (간단한 버전).

        Args:
            index_name (str): 삭제할 인덱스 이름
            ignore_if_not_exists (bool): 인덱스가 없어도 오류로 처리하지 않음

        Returns:
            bool: 삭제 성공 여부
        """
        result = self.drop_vector_index(index_name)

        if result['success']:
            return True

        # 인덱스가 없는 경우 무시할지 결정
        if ignore_if_not_exists and result['error_type'] in ['IndexNotFound', 'OperationFailure']:
            if result.get('error_code') == 27:  # IndexNotFound
                logger.info(f"인덱스 '{index_name}'이 이미 존재하지 않습니다. 무시합니다.")
                return True

        return False

    def drop_multiple_vector_indexes(self, index_names: list, continue_on_error: bool = True) -> dict[str, Any]:
        """
        여러 벡터 인덱스를 일괄 삭제합니다.

        Args:
            index_names (list): 삭제할 인덱스 이름 목록
            continue_on_error (bool): 오류 발생 시 계속 진행할지 여부

        Returns:
            Dict[str, Any]: 전체 작업 결과
        """
        results = {'total': len(index_names), 'success_count': 0, 'failed_count': 0, 'results': [], 'failed_indexes': []}

        for index_name in index_names:
            result = self.drop_vector_index(index_name)
            results['results'].append(result)

            if result['success']:
                results['success_count'] += 1
            else:
                results['failed_count'] += 1
                results['failed_indexes'].append({'name': index_name, 'error': result['message']})

                if not continue_on_error:
                    logger.error(f"인덱스 '{index_name}' 삭제 실패로 작업을 중단합니다.")
                    break

        logger.info(f'일괄 삭제 완료: {results["success_count"]}/{results["total"]} 성공')
        return results

    def update_vector_index(
        self,
        index_name: str,
        field_names: list[str] | str,
        dimensions: int,
        similarity: str = 'cosine',
        quantization: str = 'None',
        num_edge_candidates: int = 100,
    ):
        pass
