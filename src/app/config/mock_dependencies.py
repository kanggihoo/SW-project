# from typing import List
# from app.services.user_service import UserServiceInterface

# class MockUserService(UserServiceInterface):
#     """Mock 데이터를 반환하는 서비스"""

#     def __init__(self):
#         # Mock 데이터 정의
#         self.mock_users = [
#             {"id": 1, "name": "Mock User 1", "email": "mock1@example.com"},
#             {"id": 2, "name": "Mock User 2", "email": "mock2@example.com"},
#             {"id": 3, "name": "Mock User 3", "email": "mock3@example.com"}
#         ]

#     async def get_users(self) -> List[dict]:
#         return self.mock_users

#     async def get_user_by_id(self, user_id: int) -> dict:
#         user = next((u for u in self.mock_users if u["id"] == user_id), None)
#         if user:
#             return user
#         return {"id": user_id, "name": "Mock User Not Found", "email": "notfound@example.com"}

