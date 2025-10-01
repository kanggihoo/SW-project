import logging
import sys
from typing import Annotated

import typer
from loguru import logger

from app.config.settings import DatabaseType, MonitoringType

# logger setup from run_server.py
logger.remove()  # remove default handler

# console output settings
logger.add(
    sys.stderr,
    format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <5}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> \n <level>{message}</level>',
    level='INFO',
    colorize=True,
)


# Redirect uvicorn and FastAPI logs to loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Pass uvicorn and FastAPI logs to loguru
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

# Set levels for specific loggers
for name in ['uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi']:
    logging.getLogger(name).handlers = [InterceptHandler()]
    logging.getLogger(name).propagate = False


app = typer.Typer(no_args_is_help=True)


# @app.command()
def main(
    database_type: Annotated[DatabaseType, typer.Option('--database-type', '-db', help='Database type')],
    monitoring_type: Annotated[MonitoringType, typer.Option('--monitoring-type', '-mt', help='Monitoring type')],
):
    """
    Run the FastAPI server with dynamic settings from CLI arguments.
    These arguments set environment variables that override settings from .env file.
    """
    logger.info('Overriding settings with CLI arguments...')
    # logger.info(f'  - Database Type: {database_type.value}')
    # logger.info(f'  - Monitoring Type: {monitoring_type.value}')

    # # Set environment variables from CLI options
    # # These will be picked up by pydantic's BaseSetting
    # os.environ['DATABASE_TYPE'] = database_type.value
    # os.environ['MONITORING_TYPE'] = monitoring_type.value
    # os.environ['USE_ATLAS'] = str(use_atlas)

    # # Import settings *after* setting environment variables.
    # # This ensures that pydantic loads the settings from the environment variables we just set.
    # from app.config.settings import settings

    # logger.info('Starting FastAPI server...')
    # uvicorn.run(
    #     'app:app',
    #     host=host,
    #     port=port,
    #     reload=settings.is_dev(),
    #     log_config=None,  # Disable uvicorn's default logging config to use loguru
    # )


if __name__ == '__main__':
    main()
