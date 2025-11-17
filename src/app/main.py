# 로깅설정
import logging
import os
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from langfuse import get_client
from loguru import logger

# langgraph 관련 모듈 import
from graph.builders import get_agent, get_all_agent_info
from graph.memory import initialize_database
from graph.settings import DatabaseType, MonitoringType, settings

# Redis 관련 import
from redis_cache.client import RedisCacheClient

# TaskQueue 관련 import
from taskqueue.client import TaskQueueClient

from .api import api_router
from .api_docs import TAGS_METADATA
from .config.dependencies import get_async_repo_provider, get_aws_manager
from .config.exceptions import http_exception_handler, validation_exception_handler
from .services.musinsa import MusinsaAPIWrapper

EXCLUDED_ENDPOINTS = ['/health']


# Loguru 필터 함수 정의
def endpoint_filter(record):
    if record['name'] == 'logging':
        message = record['message']
        for endpoint in EXCLUDED_ENDPOINTS:
            if endpoint in message:
                return False
    return True  # 그 외 모든 로그는 포함 (True 반환)


# Configure logger when module is imported (for uvicorn worker processes)
def setup_app_logger():
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logger.remove()  # remove default handler

    # console output settings
    logger.add(
        sys.stderr,
        format=(
            '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <5}</level> | '
            '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>  <level>{message}</level>'
        ),
        level=log_level,
        colorize=True,
        filter=endpoint_filter,
    )

    # ERROR level logs to file with rotation, retention, and compression
    logger.add(
        'logs/error.log',
        format=('{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | {name}:{function}:{line} | {message}'),
        level='ERROR',
        rotation='10 MB',  # Rotate when file size reaches 10MB
        retention='30 days',  # Keep logs for 30 days
        compression='zip',  # Compress rotated files
        encoding='utf-8',
    )

    # Redirect uvicorn and FastAPI logs to loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # Set up InterceptHandler for uvicorn and FastAPI loggers
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for name in ['uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi']:
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False


# Setup logger when module is imported
setup_app_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 리소스 초기화
    logger.info('Lifespan started: Initializing resources...')
    if settings.LANGFUSE_TRACING and settings.MONITORING_TYPE == MonitoringType.LANGFUSE:
        try:
            # Langfuse 클라이언트 초기화 시 설정값 명시적으로 전달
            if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
                raise ValueError('Langfuse credentials are missing. Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY environment variables.')

            logger.info('Initializing Langfuse client')
            langfuse = get_client()
            if langfuse.auth_check():
                logger.info('Langfuse initialized successfully.')
            else:
                raise ValueError('Langfuse authentication failed')
        except Exception as e:
            logger.warning(f'Langfuse initialization error: {e}')
    try:
        http_session = httpx.AsyncClient()
        app.state.http_session = http_session
        logger.info('httpx.AsyncClient initialized.')

        app.state.db_repo = await get_async_repo_provider(is_sku=True)
        logger.info('MongoDB connection established.')

        app.state.aws_manager = get_aws_manager()
        logger.info('AWS Manager initialized.')

        # try:
        #     app.state.jina_embedding = get_jina_embedding(session=http_session)
        #     logger.info("Jina Embedding initialized.")
        # except Exception as e:
        #     logger.error(f"Jina Embedding initialization error: {e}")
        #     app.state.jina_embedding = None

        app.state.musinsa_api_wrapper = MusinsaAPIWrapper(http_session)
        logger.info('Musinsa API Wrapper initialized.')

        # Redis 클라이언트 초기화
        redis_client = RedisCacheClient()
        await redis_client.connect()
        app.state.redis_client = redis_client
        logger.info('Redis client initialized.')

        # TaskQueue Client 초기화
        taskqueue_client = TaskQueueClient()
        await taskqueue_client.connect()
        app.state.taskqueue_client = taskqueue_client
        logger.info('TaskQueue Client initialized.')
    except Exception as e:
        logger.error(f'fastapi lifespan initialization error: {e}')
        raise e from e
    try:
        async with initialize_database() as saver:
            if settings.DATABASE_TYPE == DatabaseType.POSTGRES:
                logger.info('PostgreSQL connection pool initialized.')
            elif settings.DATABASE_TYPE == DatabaseType.SQLITE:
                logger.info('SQLite connection initialized.')
            else:
                raise ValueError(f'Invalid database type: {settings.DATABASE_TYPE}')

            if hasattr(saver, 'setup'):
                await saver.setup()
            agent_names = get_all_agent_info()
            agents = {}
            for agent_name in agent_names:
                agent = get_agent(
                    agent_name,
                    client=app.state.http_session,
                    musinsa_api_wrapper=app.state.musinsa_api_wrapper,
                    cache_client=app.state.redis_client,
                    task_queue_client=app.state.taskqueue_client,
                    db_repository=app.state.db_repo,
                )
                # if agent_name == "llm_search":
                #     agent = builder(app.state.http_session, app.state.db_repo)
                # else:
                #     agent = builder(app.state.http_session)

                agent.checkpointer = saver
                agents[agent_name] = agent
            app.state.agents = agents
            app.state.checkpointer = saver
            logger.info('init finished')
            yield
    except Exception as e:
        logger.error(f'PostgreSQL connection pool initialization error: {e}')
    # 애플리케이션 종료 시 리소스 정리
    logger.info('Lifespan ended: Shutting down resources...')
    if app.state.db_repo:
        await app.state.db_repo.close()
        logger.info('MongoDB connection closed.')
    if app.state.aws_manager:
        # AWSManager에 close_connection 메서드가 있다면 호출
        # app.state.aws_manager.close_connection()
        logger.info('AWS resources cleaned up.')
    # if app.state.musinsa_api_wrapper:
    #     await app.state.musinsa_api_wrapper.close()
    #     logger.info("Musinsa API Wrapper closed.")
    if app.state.http_session:
        await app.state.http_session.aclose()
        logger.info('httpx.AsyncClient closed.')

    if hasattr(app.state, 'redis_client') and app.state.redis_client:
        await app.state.redis_client.close()
        logger.info('Redis client closed.')

    if hasattr(app.state, 'taskqueue_client') and app.state.taskqueue_client:
        await app.state.taskqueue_client.close()
        logger.info('TaskQueue Client closed.')


app = FastAPI(
    title='Clothing Recommendation API',
    description='An API for clothing recommendations using LangGraph',
    version='1.0.0',
    lifespan=lifespan,
    exception_handlers={RequestValidationError: validation_exception_handler, HTTPException: http_exception_handler},
    openapi_tags=TAGS_METADATA,
    root_path='/langgraph',
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # 개발 환경에서는 모든 origin 허용 (프로덕션에서는 특정 origin만 허용)
    allow_credentials=False,  # allow_origins=['*']일 때는 False로 설정해야 함
    allow_methods=['*'],  # 모든 HTTP 메서드 허용
    allow_headers=['*'],  # 모든 헤더 허용
)

# app.include_router(websocket.router)
app.include_router(api_router)


@app.get('/', tags=['root'])
async def root():
    return {'message': 'Welcome to the Clothing Recommendation API'}
