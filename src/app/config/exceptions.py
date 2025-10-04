import json

from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.exception(
        f'HTTPException: RequestURL:{request.url}\n \
            Method:{request.method}\n \
            StatusCode:{exc.status_code}\n \
            Detail:{exc.detail}'
    )
    return JSONResponse(status_code=exc.status_code, content={'success': False, 'message': 'Internal Server Error'})


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    FastAPI의 RequestValidationError를 처리하여 커스텀 로그를 남기고
    클라이언트에게 일관된 형식의 에러 메시지를 반환합니다.
    """
    # 에러의 상세 내용을 로그로 남깁니다.
    # exc.errors()는 각 유효성 검사 실패에 대한 상세 정보를 담고 있습니다.

    # 요청 본문을 읽어 로그에 추가합니다.
    body = await request.body()
    decoded_body = body.decode('utf-8')

    try:
        # JSON 형식으로 파싱하여 보기 좋게 만듭니다.
        body_json = json.loads(decoded_body)
        log_body = json.dumps(body_json, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # JSON이 아닌 경우, 원본 텍스트를 그대로 사용합니다.
        log_body = decoded_body

    logger.exception(
        f'422 Unprocessable Entity: {exc.errors()} \n \
            Request URL: {request.method} {request.url}\n \
            Request Body:\n{log_body}'
    )

    return JSONResponse(
        status_code=422, content={'success': False, 'message': 'The data you submitted is invalid. Please correct the fields below', 'data': {}}
    )
