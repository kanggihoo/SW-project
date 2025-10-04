import asyncio

from fastapi import APIRouter, HTTPException

from app.config.dependencies import DBConnectionDep
from app.services.db_meta import database_metadata_service

router = APIRouter(prefix='/api', tags=['postgre'])


@router.get('/test')
async def ping(db_connection: DBConnectionDep):
    """데이터베이스 연결 확인"""
    stat = await db_connection.execute('SELECT 1')
    result = await stat.fetchone()
    return result


@router.get('/health')
async def health_check(db_connection: DBConnectionDep):
    """데이터베이스 헬스체크"""
    return await database_metadata_service.health_check(db_connection)


@router.get('/connections')
async def get_connection_info(db_connection: DBConnectionDep):
    """데이터베이스 연결 정보 조회"""
    try:
        return await database_metadata_service.get_connection_info(db_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to get connection info: {str(e)}')


@router.get('/info')
async def get_database_info(db_connection: DBConnectionDep):
    """데이터베이스 기본 정보 조회"""
    try:
        return await database_metadata_service.get_database_info(db_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to get database info: {str(e)}')


@router.get('/tables/stats')
async def get_table_statistics(db_connection: DBConnectionDep):
    """테이블 통계 정보 조회"""
    try:
        return await database_metadata_service.get_table_statistics(db_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to get table statistics: {str(e)}')


@router.get('/size')
async def get_database_size_info(db_connection: DBConnectionDep):
    """데이터베이스 크기 정보 조회"""
    try:
        return await database_metadata_service.get_database_size_info(db_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to get database size info: {str(e)}')


# 종합 대시보드 엔드포인트
@router.get('/dashboard')
async def get_database_dashboard(db_connection: DBConnectionDep):
    """데이터베이스 종합 대시보드 정보"""
    try:
        # 여러 정보를 병렬로 수집
        health, connections, info, size = await asyncio.gather(
            database_metadata_service.health_check(db_connection),
            database_metadata_service.get_connection_info(db_connection),
            database_metadata_service.get_database_info(db_connection),
            database_metadata_service.get_database_size_info(db_connection),
            return_exceptions=True,
        )
        return {
            'health': health if not isinstance(health, Exception) else {'error': str(health)},
            'connections': connections if not isinstance(connections, Exception) else {'error': str(connections)},
            'info': info if not isinstance(info, Exception) else {'error': str(info)},
            'size': size if not isinstance(size, Exception) else {'error': str(size)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to get dashboard info: {str(e)}')
