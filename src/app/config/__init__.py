# ⭐ 핵심: 환경에 따라 의존성을 라우팅하는 역할
# ============================================
# from app.config.settings import settings, Environment
# from app.config.dependencies import get_user_service as get_real_user_service
# from app.config.mock_dependencies import MockUserService
# from app.services.user_service import UserServiceInterface

# def get_user_service() -> UserServiceInterface:
#     """
#     환경 설정에 따라 실제 또는 Mock 의존성을 반환
#     """
#     # 환경변수로 제어
#     if settings.use_mock_data:
#         return MockUserService()

#     # 환경별로 제어하는 방법도 가능
#     # if settings.environment == Environment.TESTING:
#     #     return MockUserService()

#     return get_real_user_service()


# # 외부로 노출할 의존성만 export
# __all__ = ["get_user_service"]


# ============================================
# src/app/api/routes.py
# ============================================
# from fastapi import APIRouter, Depends
# from typing import List
# from app.config import get_user_service  # ⭐ __init__.py에서 import
# from app.services.user_service import UserServiceInterface

# router = APIRouter()

# @router.get("/users")
# async def list_users(
#     user_service: UserServiceInterface = Depends(get_user_service)
# ) -> List[dict]:
#     """
#     환경에 따라 자동으로 실제/Mock 데이터 반환
#     코드 변경 없이 환경변수만으로 제어 가능
#     """
#     return await user_service.get_users()

# @router.get("/users/{user_id}")
# async def get_user(
#     user_id: int,
#     user_service: UserServiceInterface = Depends(get_user_service)
# ) -> dict:
#     return await user_service.get_user_by_id(user_id)
