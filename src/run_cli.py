import os
from typing import Annotated

import typer
import uvicorn
from loguru import logger

from app.config.settings import Environment, FastAPIMode, settings
from graph.settings import DatabaseType, EnvType, MonitoringType

app = typer.Typer(no_args_is_help=True)


@app.command()
def main(
    database_type: Annotated[DatabaseType, typer.Option('--database-type', '-db', help='Database type')] = DatabaseType.POSTGRES,
    monitoring_type: Annotated[MonitoringType, typer.Option('--monitoring-type', '-mt', help='Monitoring type')] = MonitoringType.LANGFUSE,
    environment: Annotated[Environment, typer.Option('--environment', '-e', help='mock data 사용여부')] = Environment.PRODUCTION,
    log_level: Annotated[str, typer.Option('--log-level', '-l', help='Log level')] = 'info',
    mode: Annotated[FastAPIMode, typer.Option('--mode', '-m', help='fastapi reload mode')] = FastAPIMode.DEVELOPMENT,
    db_env: Annotated[EnvType, typer.Option('--db-env', '-de', help='Database environment [local, cloud]')] = EnvType.LOCAL,
):
    """
    Run the FastAPI server with dynamic settings from CLI arguments.
    These arguments set environment variables that override settings from .env file.
    """
    logger.info('Overriding settings with CLI arguments...')
    logger.info(f'  - Database Type: {database_type}')
    logger.info(f'  - Monitoring Type: {monitoring_type}')
    logger.info(f'  - Log Level: {log_level.upper()}')
    logger.info(f'  - Environment: {environment}')
    logger.info(f'  - Mode: {mode}')

    # # Set environment variables from CLI options
    # # These will be picked up by pydantic's BaseSetting
    os.environ['DATABASE_TYPE'] = database_type
    os.environ['MONITORING_TYPE'] = monitoring_type
    os.environ['LOG_LEVEL'] = log_level.upper()
    os.environ['ENV'] = environment
    os.environ['MODE'] = mode
    os.environ['DB_ENV'] = db_env

    # # Import settings *after* setting environment variables.
    # # This ensures that pydantic loads the settings from the environment variables we just set.
    # from app.config.settings import settings

    logger.info('Starting FastAPI server...')
    uvicorn.run(
        'app:app',
        host='0.0.0.0',
        port=8000,
        reload=settings.is_dev(),
        log_config=None,  # Disable uvicorn's default logging config to use loguru
    )


if __name__ == '__main__':
    app()
