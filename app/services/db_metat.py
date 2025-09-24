# app/services/db_metadata_service.py
from typing import Dict, List, Optional, Any
from psycopg import AsyncConnection
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DatabaseMetadataService:
    """데이터베이스 메타데이터 및 서버 정보를 관리하는 서비스 클래스 (dict_row 지원)"""
        
    
    async def health_check(self, connection: AsyncConnection) -> Dict[str, Any]:
        """데이터베이스 헬스체크"""
        try:
            start_time = datetime.now(timezone.utc)
            
            # 간단한 쿼리로 연결 확인
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT 1 as test_value")
                result = await cursor.fetchone()
            
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query_result": result.get("test_value") if result else None
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_connection_info(self, connection: AsyncConnection) -> Dict[str, Any]:
        """현재 연결 정보 조회"""
        try:
            queries = [
                ("active_connections", """
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """),
                ("total_connections", """
                    SELECT count(*) as total_connections
                    FROM pg_stat_activity
                """),
                ("max_connections", """
                    SELECT setting::int as max_connections
                    FROM pg_settings 
                    WHERE name = 'max_connections'
                """),
                ("idle_connections", """
                    SELECT count(*) as idle_connections
                    FROM pg_stat_activity 
                    WHERE state = 'idle'
                """)
            ]
            
            result = {}
            async with connection.cursor() as cursor:
                for key, query in queries:
                    await cursor.execute(query)
                    row = await cursor.fetchone()
                    # 딕셔너리에서 첫 번째 값 추출
                    result[key] = list(row.values())[0] if row else 0
            
            # 연결 사용률 계산
            if result.get('max_connections', 0) > 0:
                result['connection_usage_percent'] = round(
                    (result['total_connections'] / result['max_connections']) * 100, 2
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            raise
    
    async def get_database_info(self, connection: AsyncConnection) -> Dict[str, Any]:
        """데이터베이스 기본 정보 조회"""
        try:
            queries = [
                ("version", "SELECT version() as version"),
                ("current_database", "SELECT current_database() as current_database"),
                ("current_user", "SELECT current_user as current_user"),
                ("server_encoding", """
                    SELECT pg_encoding_to_char(encoding) as server_encoding 
                    FROM pg_database 
                    WHERE datname = current_database()
                """),
                ("timezone", "SELECT current_setting('timezone') as timezone"),
                ("uptime", """
                    SELECT date_trunc('second', current_timestamp - pg_postmaster_start_time()) as uptime
                """)
            ]
            
            result = {}
            async with connection.cursor() as cursor:
                for key, query in queries:
                    await cursor.execute(query)
                    row = await cursor.fetchone()
                    if row:
                        # 딕셔너리에서 해당 키의 값 추출
                        value = list(row.values())[0]
                        # datetime 객체는 ISO 형식으로 변환
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        result[key] = value
                    else:
                        result[key] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            raise
    
    async def get_table_statistics(self, connection: AsyncConnection) -> List[Dict[str, Any]]:
        """테이블 통계 정보 조회"""
        try:
            query = """
                SELECT 
                    schemaname,
                    relname,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_analyze
                FROM pg_stat_user_tables 
                ORDER BY n_live_tup DESC
                LIMIT 20
            """
            
            async with connection.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()
                
                # 각 row는 이미 딕셔너리이므로 datetime 처리만 필요
                result = []
                for row in rows:
                    processed_row = {}
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            processed_row[key] = value.isoformat()
                        else:
                            processed_row[key] = value
                    result.append(processed_row)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get table statistics: {e}")
            raise
    
    async def get_database_size_info(self, connection: AsyncConnection) -> Dict[str, Any]:
        """데이터베이스 크기 정보 조회"""
        try:
            # 단일 값 쿼리들
            single_queries = [
                ("database_size_bytes", """
                    SELECT pg_database_size(current_database()) as database_size_bytes
                """),
                ("database_size_pretty", """
                    SELECT pg_size_pretty(pg_database_size(current_database())) as database_size_pretty
                """)
            ]
            
            result = {}
            async with connection.cursor() as cursor:
                # 단일 값 쿼리들 처리
                for key, query in single_queries:
                    await cursor.execute(query)
                    row = await cursor.fetchone()
                    result[key] = list(row.values())[0] if row else None
                
                # 테이블 목록 쿼리
                table_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 10
                """
                await cursor.execute(table_query)
                rows = await cursor.fetchall()
                
                # rows는 이미 딕셔너리 리스트
                result["largest_tables"] = list(rows)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get database size info: {e}")
            raise
    

database_metadata_service = DatabaseMetadataService()