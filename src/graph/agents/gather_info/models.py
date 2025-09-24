from pydantic import BaseModel , Field
from typing import List, Optional


class UserProfile(BaseModel):
    """사용자 프로필 - 개인화된 추천을 위한 정보"""
    user_id: str
    preferred_style: Optional[str] = Field(default=None, description="선호하는 기본 스타일")
    preferred_colors: Optional[List[str]] = Field(default_factory=list, description="선호 색상 목록")
    excluded_colors: Optional[List[str]] = Field(default_factory=list, description="기피 색상 목록")
    size: Optional[str] = Field(default=None, description="사이즈 정보")


