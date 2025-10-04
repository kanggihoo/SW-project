from contextlib import AbstractAsyncContextManager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..settings import DatabaseType, settings
from .postgres import get_postgres_saver
from .sqlite import get_sqlite_saver


def initialize_database() -> AbstractAsyncContextManager[AsyncSqliteSaver | AsyncPostgresSaver]:
    if settings.DATABASE_TYPE == DatabaseType.POSTGRES:
        return get_postgres_saver()
    elif settings.DATABASE_TYPE == DatabaseType.SQLITE:
        return get_sqlite_saver()
    else:
        raise ValueError(f'Invalid database type: {settings.DATABASE_TYPE}')
