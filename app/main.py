from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
from .router import websocket
from .api.v1.api import api_router
from .config.dependencies import get_fashion_repo , get_aws_manager
load_dotenv()


# 로깅설정
logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s : %(filename)s - %(lineno)d' , datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        fashion_repo = get_fashion_repo()
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
    try:
        aws_manager = get_aws_manager()
    except Exception as e:
        logger.error(f"AWS connection error: {e}")

    logger.info("lifespan started")
    yield

    logger.info("Shutting down...")
    fashion_repo.close_connection()
    aws_manager.close_connection()
    

app = FastAPI(
    title="Clothing Recommendation API",
    description="An API for clothing recommendations using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(websocket.router)
app.include_router(api_router)

@app.get("/" , tags=["root"])
async def root():
    return {"message": "Welcome to the Clothing Recommendation API"}





# #TODO : 문서화 추가 
# from fastapi.openapi.utils import get_openapi

# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
        
#     # 기본 OpenAPI 스키마 생성
#     openapi_schema = get_openapi(
#         title="Custom API with WebSocket",
#         version="1.0.0",
#         description="This is a very custom OpenAPI schema",
#         routes=app.routes,
#     )

#     # WebSocket 경로에 대한 정보 추가
#     # openapi_schema["paths"] 딕셔너리에 /ws 경로를 추가합니다.
#     openapi_schema["paths"]["/ws"] = {
#         "get": {  # WebSocket은 보통 GET 요청으로 시작되므로 'get'으로 표현합니다.
#             "summary": "Create WebSocket Connection",
#             "description": "이 엔드포인트는 WebSocket 연결을 생성합니다.",
#             "tags": ["websockets"],
#             "responses": {
#                 "101": {
#                     "description": "WebSocket connection established"
#                 }
#             },
#             "parameters": [], # WebSocket 연결 자체에는 파라미터가 없을 수 있습니다.
#         }
#     }
    
#     # x-aperture-replaces 필드를 사용하여 WebSocket 메시지에 대한 정보를 추가할 수 있습니다.
#     # 이는 표준 OpenAPI 사양은 아니지만, 일부 도구에서 활용될 수 있는 확장 필드입니다.
#     # 더 명확한 문서화를 위해 description에 직접 명시하는 것이 일반적입니다.

#     # Pydantic 모델을 사용한 메시지 스키마를 설명에 추가
#     openapi_schema["paths"]["/ws"]["get"]["description"] += """
        
#     ### 주고받는 메시지 형식:

#     - **클라이언트 -> 서버 (MessageIn):**
#     ```json
#     {
#         "text": "string"
#     }
#     - 서버 -> 클라이언트 (MessageOut):
#     ```json
#     {
#         "message": "string"
#     }
#     """
    
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema
    
# app.openapi = custom_openapi