"""
MongoDB 데이터 비정규화 스크립트

기존의 product-centric 구조를 SKU-centric 구조로 변환합니다.
- 소스: products 컬렉션 (상품 중심)
- 타겟: products_by_sku 컬렉션 (SKU 중심)
"""

import asyncio
from typing import Any

from loguru import logger
from pymongo.errors import BulkWriteError

from db.config.config import Config
from db.repository.fashion_async import AsyncFashionRepository

# 로깅 설정


class DenormalizationService:
    """데이터 비정규화 서비스"""

    def __init__(self):
        self.config = Config()
        self.atlas_config = self.config.get_atlas_config()
        self.atlas_sku_config = self.config.get_atlas_sku_config()

        # 소스와 타겟 Repository 초기화
        self.source_repo = AsyncFashionRepository(
            connection_string=self.atlas_config['MONGODB_ATLAS_CONNECTION_STRING'],
            database_name=self.atlas_config['MONGODB_ATLAS_DATABASE_NAME'],
            collection_name=self.atlas_config['MONGODB_ATLAS_COLLECTION_NAME'],
        )

        self.target_repo = AsyncFashionRepository(
            connection_string=self.atlas_sku_config['MONGODB_ATLAS_CONNECTION_STRING'],
            database_name=self.atlas_sku_config['MONGODB_ATLAS_DATABASE_NAME'],
            collection_name=self.atlas_sku_config['MONGODB_ATLAS_COLLECTION_NAME'],
        )

        self.batch_size = 50  # 배치 크기
        self.processed_count = 0
        self.error_count = 0

    async def connect(self):
        """데이터베이스 연결"""
        try:
            await self.source_repo.connect()
            await self.target_repo.connect()
            logger.info('Successfully connected to source and target databases')
        except Exception as e:
            logger.error(f'Failed to connect to databases: {e}')
            raise

    async def close(self):
        """데이터베이스 연결 종료"""
        await self.source_repo.close()
        await self.target_repo.close()
        logger.info('Database connections closed')

    def transform_product_to_sku_documents(self, product_doc: dict) -> list[dict]:
        """
        단일 상품 문서를 여러 SKU 문서로 변환

        Args:
            product_doc: 원본 상품 문서

        Returns:
            List[Dict]: 변환된 SKU 문서 리스트
        """
        if not product_doc:
            return []

        # 공통 데이터 추출
        common_data = {
            'products': product_doc.get('products', {}),
            'embedding': product_doc.get('embedding', {}),
            'reviews': product_doc.get('reviews', []),
            'images': product_doc.get('images', {}),
        }

        # product_skus 데이터 추출
        product_skus = product_doc.get('product_skus', {})
        if not product_skus:
            logger.warning(f'No product_skus found in document {product_doc.get("_id")}')
            return []

        # 배열 필드들 추출
        sku_ids = product_skus.get('sku_id', [])
        color_names = product_skus.get('color_name', [])
        color_hexes = product_skus.get('color_hex', [])
        color_brightnesses = product_skus.get('color_brightness', [])
        color_saturations = product_skus.get('color_saturation', [])
        image_urls = product_skus.get('image_urls', [])

        # 배열 길이 확인
        array_length = len(sku_ids)
        if array_length == 0:
            logger.warning(f'No SKU IDs found in document {product_doc.get("_id")}')
            return []

        # SKU 문서들 생성
        sku_documents = []
        for i in range(array_length):
            try:
                # SKU ID가 없으면 건너뛰기
                if i >= len(sku_ids) or not sku_ids[i]:
                    continue

                # 개별 SKU 데이터 생성
                product_sku = {
                    'sku_id': sku_ids[i],
                    'color_name': color_names[i] if i < len(color_names) else None,
                    'color_hex': color_hexes[i] if i < len(color_hexes) else None,
                    'color_brightness': color_brightnesses[i] if i < len(color_brightnesses) else None,
                    'color_saturation': color_saturations[i] if i < len(color_saturations) else None,
                    'image_urls': [image_urls[i]] if i < len(image_urls) and image_urls[i] else [],
                    'main_category': product_skus.get('main_category'),
                    'sub_category': product_skus.get('sub_category'),
                    'gender': product_skus.get('gender'),
                    'fit': product_skus.get('fit'),
                    'style_tags': product_skus.get('style_tags', []),
                    'tpo_tags': product_skus.get('tpo_tags', []),
                    'common': product_skus.get('common', {}),
                }

                # SKU 문서 생성
                sku_document = {
                    '_id': sku_ids[i],  # SKU ID를 문서 ID로 사용
                    **common_data,  # 공통 데이터 복사
                    'product_skus': product_sku,  # 단일 SKU 객체
                }

                sku_documents.append(sku_document)

            except Exception as e:
                logger.error(f'Error creating SKU document for index {i} in product {product_doc.get("_id")}: {e}')
                continue

        return sku_documents

    async def process_batch(self, batch_documents: list[dict]) -> int:
        """
        배치 단위로 문서 처리

        Args:
            batch_documents: 처리할 문서 배치

        Returns:
            int: 성공적으로 처리된 문서 수
        """
        if not batch_documents:
            return 0

        try:
            # 배치 삽입
            result = await self.target_repo.collection.insert_many(batch_documents, ordered=False)
            return len(result.inserted_ids)
        except BulkWriteError as e:
            # 일부 문서는 성공했을 수 있음
            success_count = e.details.get('nInserted', 0)
            logger.warning(f'Bulk write error: {success_count} documents inserted successfully')
            return success_count
        except Exception as e:
            logger.error(f'Error processing batch: {e}')
            return 0

    async def migrate_data(self, limit: int | None = None) -> dict[str, int]:
        """
        데이터 마이그레이션 실행

        Args:
            limit: 처리할 최대 문서 수 (None이면 모든 문서)

        Returns:
            Dict[str, int]: 마이그레이션 결과 통계
        """
        logger.info('Starting data denormalization migration...')

        try:
            # 소스 컬렉션에서 모든 문서 조회
            cursor = self.source_repo.collection.find({})
            if limit:
                cursor = cursor.limit(limit)

            batch_documents = []
            total_processed = 0
            total_created = 0
            total_errors = 0

            async for product_doc in cursor:
                try:
                    # 상품 문서를 SKU 문서들로 변환
                    sku_documents = self.transform_product_to_sku_documents(product_doc)

                    if not sku_documents:
                        logger.warning(f'No SKU documents created for product {product_doc.get("_id")}')
                        continue

                    # 배치에 추가
                    batch_documents.extend(sku_documents)

                    # 배치 크기에 도달하면 처리
                    if len(batch_documents) >= self.batch_size:
                        created_count = await self.process_batch(batch_documents)
                        total_created += created_count
                        total_errors += len(batch_documents) - created_count
                        batch_documents = []

                    total_processed += 1

                    # 진행 상황 로깅
                    if total_processed % 100 == 0:
                        logger.info(f'Processed {total_processed} products, created {total_created} SKU documents')

                except Exception as e:
                    logger.error(f'Error processing product {product_doc.get("_id")}: {e}')
                    total_errors += 1
                    continue

            # 남은 배치 처리
            if batch_documents:
                created_count = await self.process_batch(batch_documents)
                total_created += created_count
                total_errors += len(batch_documents) - created_count

            result_stats = {'total_products_processed': total_processed, 'total_sku_documents_created': total_created, 'total_errors': total_errors}

            logger.info(f'Migration completed: {result_stats}')
            return result_stats

        except Exception as e:
            logger.error(f'Migration failed: {e}')
            raise

    async def verify_migration(self, sample_size: int = 10) -> dict[str, Any]:
        """
        마이그레이션 결과 검증

        Args:
            sample_size: 검증할 샘플 크기

        Returns:
            Dict[str, Any]: 검증 결과
        """
        logger.info(f'Verifying migration with sample size: {sample_size}')

        try:
            # 소스 컬렉션 문서 수
            source_count = await self.source_repo.collection.count_documents({})

            # 타겟 컬렉션 문서 수
            target_count = await self.target_repo.collection.count_documents({})

            # 샘플 검증
            sample_products = []
            async for doc in self.source_repo.collection.find({}).limit(sample_size):
                sample_products.append(doc)

            verification_results = {'source_collection_count': source_count, 'target_collection_count': target_count, 'sample_verification': []}

            for product in sample_products:
                product_id = product.get('_id')
                sku_ids = product.get('product_skus', {}).get('sku_id', [])

                # 각 SKU가 타겟 컬렉션에 존재하는지 확인
                sku_verification = {'product_id': product_id, 'expected_sku_count': len(sku_ids), 'found_sku_documents': []}

                for sku_id in sku_ids:
                    sku_doc = await self.target_repo.collection.find_one({'_id': sku_id})
                    if sku_doc:
                        sku_verification['found_sku_documents'].append(sku_id)

                verification_results['sample_verification'].append(sku_verification)

            logger.info(f'Verification completed: {verification_results}')
            return verification_results

        except Exception as e:
            logger.error(f'Verification failed: {e}')
            raise


async def main():
    """메인 실행 함수"""
    denormalization_service = DenormalizationService()

    try:
        # 데이터베이스 연결
        await denormalization_service.connect()

        # 마이그레이션 실행 (테스트를 위해 처음 10개 문서만 처리)
        # 실제 운영에서는 limit=None으로 설정하여 모든 문서 처리
        migration_stats = await denormalization_service.migrate_data(limit=10)

        # 결과 검증
        verification_results = await denormalization_service.verify_migration(sample_size=5)

        print('\n=== Migration Results ===')
        print(f'Products processed: {migration_stats["total_products_processed"]}')
        print(f'SKU documents created: {migration_stats["total_sku_documents_created"]}')
        print(f'Errors: {migration_stats["total_errors"]}')

        print('\n=== Verification Results ===')
        print(f'Source collection count: {verification_results["source_collection_count"]}')
        print(f'Target collection count: {verification_results["target_collection_count"]}')

    except Exception as e:
        logger.error(f'Migration process failed: {e}')
        raise
    finally:
        # 연결 종료
        await denormalization_service.close()


if __name__ == '__main__':
    # 비동기 실행
    asyncio.run(main())
