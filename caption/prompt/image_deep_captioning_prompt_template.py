from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from typing import Any
from langchain_core.runnables import Runnable
from typing import Optional
from langchain_core.runnables import RunnableConfig
from caption.config import LLMInputKeys
#TODO 프롬프트 수정 입력으로 들어오는 이미지가 1개 혹은 2개인 경우에 따른 system_template 수정
system_template = """
당신은 패션 상품 이미지를 전문적으로 분석하는 AI입니다.

주어진 이미지는 {category}에 대한 이미지들로써 상품의 정면/후면 누끼 이미지와 모델 착용 이미지로 구성되어 있습니다.

**이미지 구성:**
- 첫 번째: 의류 정면 누끼 이미지
- 두 번째: 의류 후면 누끼 이미지  
- 세 번째: 모델 착용 이미지

**분석 방법:**
1. 누끼 이미지에서 구조적 디테일과 디자인 요소 파악
2. 모델 착용 이미지에서 {category}의 핏, 스타일, TPO 정보 분석

**구조적 속성:**
- 공통: 소매길이, 넥라인
- 정면: 패턴, 여밈/장식 요소 
- 후면: 패턴, 여밈/장식 요소

**주관적 속성:**
- 핏 타입 (단일 선택) : 상의, 하의에 따라 핏 타입이 다름
- 스타일 태그 (다중 선택, 정확한 값 사용): "모던", "심플 베이직", "캐주얼", "스트릿", "포멀", "스포티", "아웃도어", "레트로", "유니크"
- TPO 태그 (다중 선택, 정확한 값 사용): "데일리", "오피스", "격식", "데이트", "여행", "파티", "운동", "홈웨어"

**캡션 정보:**
- front_text_specific: 의류의 색상정보를 포함한 정면 누끼 이미지에서 보이는 전체적인 특징과 핵심 디자인 요소 설명
- back_text_specific: 의류의 색상 정보를 포함한 후면 누끼 이미지에서 보이는 전체적인 특징과 뒷면의 디자인 요소 설명
- design_details_description: 의류의 색상 정보를 포함한 특징적인 디테일한 정보에 대해 구체적으로 설명
- style_description: 주어진 모든 이미지를 활용하여 의류의 색상정보를 제외한 디테일한 스타일에 대해 구체적으로 설명 
- tpo_context_description: 주어진 모든 이미지를 활용하여 색상정보를 제외한 해당 의류를 착용하기 좋은 구체적인 설명
- comprehensive_description: 위 모든 정보를 종합하여, 의류 이미지에 대한 전반적인 특징을 포괄적이고 자연스러운 문장으로 작성

**분석 원칙:**
- 정확한 패션 용어 사용
- 객관적이고 구체적인 설명
- 색상 정보는 지정된 필드에서만 사용
- 모델 착용 이미지에서는 모델과 배경이 반영되지 않은 {category}에 집중하여 분석
- 태그는 미리 정의된 목록에서 선택
- 캡션 작업시에는 앞서 분류한 구조적 속성과 주관적 속성 외에, 이미지에서 추가적으로 발견되는 모든 디테일을 포괄적으로 담아서 완결된 문장으로 작성, 단 각 캡션 항목은 독립적인 문장으로 구성
"""

human_template = [

    {
        "type": "text", 
        "text": "분석할 {category} 제품 이미지를 보고 지정된 구조에 맞춰 상세한 분석 결과를 제공해주세요."
    },
    {
        "type": "image_url",
        "image_url": "data:image/jpeg;base64,{image_data}"
    }
]

class DeepImageCaptionPrompt(Runnable):
    def __init__(self):
        self.prompt = self._make_prompt()
    
    
    def _make_prompt(self):
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])
    
    def invoke(self, input: dict[str, Any], config: Optional[RunnableConfig] = None, **kwargs: Any) -> Any:
        return self.prompt.invoke(input, config, **kwargs)

    def extract_chain_input(self, kwargs: dict) -> dict[str, Any]:
        """
        체인 입력 데이터 생성
        
        Args:
            category: 상품 카테고리 (예: "상의", "하의")
            image_data: Base64 인코딩된 이미지 데이터
            
        Returns:
            체인 호출을 위한 입력 딕셔너리
        """
        llm_input = kwargs.get(LLMInputKeys.DEEP_CAPTION)
        category = llm_input.get("category")
        image_data = llm_input.get("image_data")
        if category is None or image_data is None:
            raise ValueError("category, image_data 모두 필요합니다.")
        return {
            "category": category,
            "image_data": image_data
        }

__all__ = [
    "DeepImageCaptionPrompt"
    ]