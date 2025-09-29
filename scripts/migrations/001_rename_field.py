import asyncio
import logging
import sys
import os

# 프로젝트 루트를 Python 경로에 추가하여 모듈을 찾을 수 있도록 함

from db.config.database_async import AsyncDatabaseManager
from db.config.config import get_config

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def rename_field_in_products_by_sku():
    """
    # 'products_by_sku' 컬렉션에 연결하여 'product_skus.color_name' 필드를
    # 'product_skus.color'로 변경합니다.
    """
    # 변경할 필드 이름 정의
    old_field_name = 'product_sku'
    new_field_name = 'product_skus'

    db_manager = None
    try:
        # 1. 데이터베이스 설정 가져오기
        config = get_config().get_atlas_sku_config()
        connection_string = config['MONGODB_ATLAS_CONNECTION_STRING']
        db_name = config['MONGODB_ATLAS_DATABASE_NAME']
        collection_name = config['MONGODB_ATLAS_COLLECTION_NAME']

        # 설정된 컬렉션 이름이 'products_by_sku'인지 확인
        if collection_name != 'products_by_sku':
            logging.error(f"설정 오류: 'products_by_sku' 컬렉션이 필요하지만 '{collection_name}'이(가) 설정되었습니다.")
            return

        # 2. 데이터베이스에 연결
        db_manager = AsyncDatabaseManager(connection_string=connection_string, database_name=db_name, collection_name=collection_name)
        await db_manager.connect()
        collection = db_manager.get_collection()

        logging.info(f"컬렉션에 연결되었습니다: '{collection_name}'")
        logging.info(f"필드 이름 변경 시도: '{old_field_name}' -> '{new_field_name}'")

        # 3. 모든 문서에서 필드 이름 변경
        # $rename 연산자는 필드 이름을 변경합니다.
        # { $rename: { <기존_필드명_1>: <새_필드명_1>, ... } }
        result = await collection.update_many(
            {old_field_name: {'$exists': True}},  # 기존 필드가 있는 문서만 대상으로 함
            {'$rename': {old_field_name: new_field_name}},
        )

        # 4. 결과 로깅
        logging.info('마이그레이션 완료.')
        logging.info(f'일치하는 문서 수: {result.matched_count}')
        logging.info(f'수정된 문서 수: {result.modified_count}')

    except Exception as e:
        logging.error(f'마이그레이션 중 오류 발생: {e}')
    finally:
        # 5. 연결 종료
        if db_manager and await db_manager.is_connected():
            await db_manager.close()
            logging.info('데이터베이스 연결이 종료되었습니다.')


if __name__ == '__main__':
    # 'python -m migrations.001_rename_field' 명령으로 스크립트를 실행할 수 있도록 함
    asyncio.run(rename_field_in_products_by_sku())
