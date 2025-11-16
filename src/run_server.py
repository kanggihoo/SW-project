import uvicorn
from loguru import logger

from app.config.settings import settings

if __name__ == '__main__':
    logger.info('Starting FastAPI server...')
    uvicorn.run(
        'app:app',
        host='0.0.0.0',
        port=8000,
        reload=settings.is_dev(),
        log_config=None,  # uvicorn의 기본 로그 설정 비활성화
    )
