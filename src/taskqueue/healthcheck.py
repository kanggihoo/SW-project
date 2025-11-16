# import asyncio

# from arq.cli import check  # CLI에서 사용하는 바로 그 함수를 가져옵니다.
# from arq.connections import RedisSettings


# # 헬스 체크를 수행할 워커 설정 클래스를 정의합니다.
# # 실제 워커와 동일한 redis_settings와 queues를 사용해야 합니다.
# class WorkerSettings:
#     queues = ['high_priority', 'default']
#     redis_settings = RedisSettings()  # Redis 접속 정보 (기본: localhost:6379)


# async def perform_health_check():
#     """
#     Python 코드 내에서 프로그래밍 방식으로 헬스 체크를 수행합니다.
#     """
#     print('Performing health check...')

#     # arq.cli.check 함수는 워커 클래스(설정)를 인자로 받습니다.
#     # 이 함수는 내부적으로 Redis에 연결하여 활성 워커 정보를 조회하고 출력합니다.
#     # 성공적으로 모든 워커가 건강하면 True를 반환합니다.
#     is_healthy = await check(WorkerSettings)

#     print('-' * 20)
#     if is_healthy:
#         print('✅ Health check passed: All workers are running correctly.')
#     else:
#         print('❌ Health check failed: Some workers might be down.')

#     return is_healthy


# if __name__ == '__main__':
#     asyncio.run(perform_health_check())
