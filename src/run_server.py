import logging
import sys

import uvicorn
from loguru import logger

from app.config.settings import settings

# 로그 설정을 uvicorn.run() 이전에 배치
logger.remove()  # 기본 핸들러 제거

# 콘솔 출력 설정
logger.add(
    sys.stderr,
    format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <5}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> \n <level>{message}</level>',
    level='INFO',
    colorize=True,
)

# # 파일 출력 설정 (선택사항)
# logger.add(
#     'logs/app.log',
#     rotation='1 day',
#     retention='30 days',
#     format='{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | {name}:{function}:{line} - {message}',
#     level='DEBUG',
# )


# uvicorn과 FastAPI의 로그를 loguru로 리다이렉트
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # uvicorn과 FastAPI의 로그를 loguru로 전달
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# uvicorn과 FastAPI 로거에 InterceptHandler 설정
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# 특정 로거들의 레벨 설정
for name in ['uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi']:
    logging.getLogger(name).handlers = [InterceptHandler()]
    logging.getLogger(name).propagate = False

if __name__ == '__main__':
    logger.info('Starting FastAPI server...')
    uvicorn.run(
        'app:app',
        host='0.0.0.0',
        port=8000,
        reload=settings.is_dev(),
        log_config=None,  # uvicorn의 기본 로그 설정 비활성화
    )
