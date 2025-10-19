from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# from langgraph.store.postgres import AsyncPostgresStore
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from graph.settings import settings


def validate_postgres_config() -> None:
    """
    Validate that all required PostgreSQL configuration is present.
    Raises ValueError if any required configuration is missing.
    """
    if settings.is_local():
        required_vars = [
            'LOCAL_POSTGRES_USER',
            'LOCAL_POSTGRES_PASSWORD',
            'LOCAL_POSTGRES_HOST',
            'LOCAL_POSTGRES_PORT',
            'LOCAL_POSTGRES_DB',
        ]
    else:
        required_vars = [
            'POSTGRES_USER',
            'POSTGRES_PASSWORD',
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'POSTGRES_DB',
        ]

    missing = [var for var in required_vars if not getattr(settings, var, None)]
    if missing:
        raise ValueError(
            f'Missing required PostgreSQL configuration: {", ".join(missing)}. These environment variables must be set to use PostgreSQL persistence.'
        )

    if settings.POSTGRES_MIN_CONNECTIONS_PER_POOL > settings.POSTGRES_MAX_CONNECTIONS_PER_POOL:
        raise ValueError(
            f'POSTGRES_MIN_CONNECTIONS_PER_POOL ({settings.POSTGRES_MIN_CONNECTIONS_PER_POOL}) '
            f'must be less than or equal to POSTGRES_MAX_CONNECTIONS_PER_POOL ({settings.POSTGRES_MAX_CONNECTIONS_PER_POOL})'
        )


def get_postgres_connection_string() -> str:
    if settings.is_local():
        user = settings.LOCAL_POSTGRES_USER
        password = settings.LOCAL_POSTGRES_PASSWORD
        host = settings.LOCAL_POSTGRES_HOST
        port = settings.LOCAL_POSTGRES_PORT
        db = settings.LOCAL_POSTGRES_DB
    else:
        user = settings.POSTGRES_USER
        password = settings.POSTGRES_PASSWORD
        host = settings.POSTGRES_HOST
        port = settings.POSTGRES_PORT
        db = settings.POSTGRES_DB

    if password is None:
        raise ValueError('PostgreSQL password is not set')

    return f'postgresql://{user}:{password.get_secret_value()}@{host}:{port}/{db}'


@asynccontextmanager
async def get_postgres_saver():
    """Initialize and return a PostgreSQL saver instance based on a connection pool for more resilent connections."""
    validate_postgres_config()
    application_name = settings.POSTGRES_APPLICATION_NAME + '-' + 'saver'
    async with AsyncConnectionPool(
        get_postgres_connection_string(),
        min_size=settings.POSTGRES_MIN_CONNECTIONS_PER_POOL,
        max_size=settings.POSTGRES_MAX_CONNECTIONS_PER_POOL,
        # Langgraph requires autocommmit=true and row_factory to be set to dict_row.
        # Application_name is passed so you can identify the connection in your Postgres database connection manager.
        kwargs={'autocommit': True, 'row_factory': dict_row, 'application_name': application_name, 'prepare_threshold': None},
        # makes sure that the connection is still valid before using it
        # 사용이 끝난 connection을 반환할때 다시 풀에 넣기 전에 해당 연결이 여전히 유효하고 건강한지 검사를 진행해서 True가 반환되면 정상반납, False가 반환되면 connection을 버리고 새로운 연결을 만듭니다.  # noqa: E501
        check=AsyncConnectionPool.check_connection,
    ) as pool:
        try:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            yield checkpointer
        finally:
            await pool.close()


# @asynccontextmanager
# async def get_postgres_connection_pool() -> AsyncPostgresSaver:
#     validate_postgres_config()
#     application_name = settings.POSTGRES_APPLICATION_NAME + '-' + 'store'
#     async with AsyncConnectionPool(
#         get_postgres_connection_string(),
#         min_size=settings.POSTGRES_MIN_CONNECTIONS_PER_POOL,
#         max_size=settings.POSTGRES_MAX_CONNECTIONS_PER_POOL,
#         kwargs={'autocommit': True, 'row_factory': dict_row, 'application_name': application_name, 'prepare_threshold': None},
#         check=AsyncConnectionPool.check_connection,
#     ) as pool:
#         yield pool


# @asynccontextmanager
# async def get_postgres_store():
#     """
#     Get a PostgreSQL store instance based on a connection pool for more resilent connections.

#     Returns an AsyncPostgresStore instance that can be used with async context manager pattern.

#     """
#     validate_postgres_config()
#     application_name = settings.POSTGRES_APPLICATION_NAME + "-" + "store"

#     async with AsyncConnectionPool(
#         get_postgres_connection_string(),
#         min_size=settings.POSTGRES_MIN_CONNECTIONS_PER_POOL,
#         max_size=settings.POSTGRES_MAX_CONNECTIONS_PER_POOL,
#         # Langgraph requires autocommmit=true and row_factory to be set to dict_row
#         # Application_name is passed so you can identify the connection in your Postgres database connection manager.
#         kwargs={"autocommit": True, "row_factory": dict_row, "application_name": application_name, "prepare_threshold": None},
#         # makes sure that the connection is still valid before using it
#         check=AsyncConnectionPool.check_connection,
#     ) as pool:
#         try:
#             store = AsyncPostgresStore(pool)
#             await store.setup()
#             yield store
#         finally:
#             await pool.close()
