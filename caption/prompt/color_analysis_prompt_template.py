"""
의류 색상 분석을 위한 VLM 프롬프트 템플릿 모듈
"""
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from typing import Any

# System Prompt for Color Analysis
system_template = """

    당신은 의류 이미지의 색상을 정확하게 분석하는 전문가입니다. 
    주어진 이미지는 {count} 개의 {category} 이미지로써 각 의류 이미지를 개별적으로 분석하여 다음 정보를 정확히 추출해야 합니다:

    ## 분석 기준

    ### 1. 대표 색상 선택
    - 의류 이미지에서 가장 넓은 면적을 차지하는 색상을 선택
    - 다음 15개 색상 중 가장 적합한 것을 선택:
    - 화이트, 그레이, 블랙, 레드, 핑크, 옐로우, 오렌지, 그린, 블루, 퍼플, 브라운, 베이지, 데님, 메탈릭, 멀티컬러

    ### 2. HEX 코드 결정
    - 선택한 대표 색상의 **정확한 HEX 코드**를 6자리 16진수로 표현
    - 실제 이미지에서 보이는 색상과 최대한 일치하도록 설정
    - 형식: #RRGGBB (예: #4A90E2, #FF0000, #FFFFFF)

    ### 3. 색상 속성 평가
    - **명도(Brightness)**: 아주 밝음, 밝음, 중간 밝기, 어두움, 아주 어두움
    - **채도(Saturation)**: 아주 낮음, 낮음, 중간 채도, 높음, 아주 높음

    ## 분석 원칙
    1. 패턴이나 프린트가 있는 경우 의류의 주된 색상을 기준으로 판단
    2. 멀티컬러의 경우 색상이 3개 이상 비슷한 비율로 섞여있을 때만 선택
    3. 의류 자체의 색상에만 집중하고 장식, 액세서리, 배경은 분석에서 제외
    4. 각 이미지에 대해 독립적으로 분석하여 {count} 개의 색상 정보를 추출
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

class ColorCaptionPrompt:
    def __init__(self):
        self.prompt = self._make_prompt()
    
    def _make_prompt(self):
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])

    def create_color_captioning_chain(self, model):
        """
        이미지 캡셔닝을 위한 체인 생성
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
    "ColorCaptionPrompt"
    ]