from pydantic import BaseModel, Field
from typing import Optional, List

# class AskQuestionAndUpdateState(BaseModel):
#     """
#     정보가 부족한 경우 호출되는 도구
#     사용자에게 질문하고 상태를 업데이트하는 역할
#     """
#     message_to_user: str = Field(description="사용자에게 전송할 질문 메시지")
#     criteria_update: dict = Field(description="기존의 정보와 사용자가 입력한 정보를 바탕으로 업데이트할 정보")



class SearchInfo(BaseModel):
    """검색 조건을 담는 모델 - 점진적으로 채워지는 퍼즐 조각"""
    tpo: Optional[str] = Field(default=None, description="언제 어느 상황에 입을 옷인지 (예: 봄 주말 데이트)")
    style: Optional[str] = Field(default=None, description="스타일 (캐주얼, 포멀, 스트릿 등)")
    color: Optional[str] = Field(default=None, description="선호 색상")
    excluded_colors: Optional[List[str]] = Field(default_factory=list, description="제외할 색상 목록") # -> 사용자가 선호하지 않는 정보 반영하도록
    
    def is_complete(self) -> bool:
        """필수 정보가 모두 수집되었는지 확인"""
        return self.tpo is not None and self.style is not None and self.color is not None
    
    def get_missing_fields(self) -> List[str]:
        """부족한 필수 필드 목록 반환"""
        missing = []
        if not self.tpo:
            missing.append("tpo")
        if not self.style:
            missing.append("style")
        if not self.color:
            missing.append("color")
        return missing