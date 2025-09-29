#!/usr/bin/env python3
"""
데이터 비정규화 실행 스크립트

사용법:
    python run_denormalization.py [--limit N] [--verify-only]

옵션:
    --limit N: 처리할 최대 상품 수 (기본값: None, 모든 상품 처리)
    --verify-only: 마이그레이션 없이 검증만 실행
"""

import asyncio
import argparse
import logging
from db.denormalization import DenormalizationService

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_denormalization(limit: int = None, verify_only: bool = False):
    """비정규화 프로세스 실행"""
    denormalization_service = DenormalizationService()

    try:
        # 데이터베이스 연결
        logger.info('Connecting to databases...')
        await denormalization_service.connect()

        if verify_only:
            # 검증만 실행
            logger.info('Running verification only...')
            verification_results = await denormalization_service.verify_migration(sample_size=10)

            print('\n=== Verification Results ===')
            print(f'Source collection count: {verification_results["source_collection_count"]}')
            print(f'Target collection count: {verification_results["target_collection_count"]}')

            print('\n=== Sample Verification ===')
            for verification in verification_results['sample_verification']:
                product_id = verification['product_id']
                expected_count = verification['expected_sku_count']
                found_count = len(verification['found_sku_documents'])
                print(f'Product {product_id}: Expected {expected_count} SKUs, Found {found_count}')

        else:
            # 마이그레이션 실행
            logger.info(f'Starting migration with limit: {limit}')
            migration_stats = await denormalization_service.migrate_data(limit=limit)

            # 결과 검증
            logger.info('Running verification...')
            verification_results = await denormalization_service.verify_migration(sample_size=5)

            print('\n=== Migration Results ===')
            print(f'Products processed: {migration_stats["total_products_processed"]}')
            print(f'SKU documents created: {migration_stats["total_sku_documents_created"]}')
            print(f'Errors: {migration_stats["total_errors"]}')

            print('\n=== Verification Results ===')
            print(f'Source collection count: {verification_results["source_collection_count"]}')
            print(f'Target collection count: {verification_results["target_collection_count"]}')

            print('\n=== Sample Verification ===')
            for verification in verification_results['sample_verification']:
                product_id = verification['product_id']
                expected_count = verification['expected_sku_count']
                found_count = len(verification['found_sku_documents'])
                print(f'Product {product_id}: Expected {expected_count} SKUs, Found {found_count}')

        logger.info('Process completed successfully!')

    except Exception as e:
        logger.error(f'Process failed: {e}')
        raise
    finally:
        # 연결 종료
        await denormalization_service.close()
        logger.info('Database connections closed')


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='MongoDB 데이터 비정규화 스크립트')
    parser.add_argument('--limit', type=int, default=None, help='처리할 최대 상품 수 (기본값: 모든 상품)')
    parser.add_argument('--verify-only', action='store_true', help='마이그레이션 없이 검증만 실행')

    args = parser.parse_args()

    # 비동기 실행
    asyncio.run(run_denormalization(limit=args.limit, verify_only=args.verify_only))


if __name__ == '__main__':
    main()
