# 텍스트 ocr 관련 pormpt 템플릿 생성

"""
의류 색상 분석을 위한 VLM 프롬프트 템플릿 모듈
"""
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from typing import Any

# System Prompt for Color Analysis
system_template = """

   
"""

human_template = [
    {
        "type": "text",
        "text": "분석할 {count} 개의 의류 이미지를 보고 지정된 구조에 맞춰 상세한 분석 결과를 제공해주세요."
    },
    {
        "type": "image_url",
        "image_url": "data:image/jpeg;base64,{image_data}"
    }
]

class TextImageOCRPrompt:
    def __init__(self):
        self.prompt = self._make_prompt()
    
    def _make_prompt(self):
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])

    def create_text_image_ocr_chain(self, model):
        """
        이미지 ocr 체인 생성
        Returns:
            체인 객체
        """
        return self.prompt | model

    def get_chain_input(self, count: int, category: str, image_data: str) -> dict[str, Any]:
        """
        체인 입력 데이터 생성
        
        Args:
            count: 분석할 이미지 개수
            category: 상품 카테고리 (예: "상의", "하의")
            image_data: Base64 인코딩된 이미지 데이터
            
        Returns:
            체인 호출을 위한 입력 딕셔너리
        """
        return {
            "count": count,
            "category": category,
            "image_data": image_data
        }

__all__ = [
    "TextImageOCRPrompt"
    ]