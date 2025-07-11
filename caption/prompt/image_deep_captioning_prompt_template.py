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
        - 핏 타입 (단일 선택): "슬림 핏", "레귤러 핏/스탠다드 핏", "오버사이즈 핏"
        - 스타일 태그 (다중 선택, 정확한 값 사용): "모던/미니멀", "심플 베이직", "캐주얼", "스트릿", "포멀/클래식", "스포티/애슬레저", "아웃도어", "빈티지/레트로", "유니크"
        - TPO 태그 (다중 선택, 정확한 값 사용): "데일리", "오피스/비즈니스", "격식/하객", "데이트/주말", "여행/휴가", "파티/모임", "운동", "홈웨어/라운지"
        
        **캡션 정보:**
        - front_text_specific: 색상정보를 포함한 의류 정면 누끼 이미지에 대한 캡션정보
        - back_text_specific: 색상정보를 포함한 의류 후면 누끼 이미지에 대한 캡션정보
        - design_details_description: 색상 정보를 포함한 의류 디자인 및 디테일 정보
        - style_description: 색상정보를 제외한 의류 스타일 정보
        - tpo_context_description: 색상정보를 제외한 TPO 상황 설명
        - comprehensive_description: 의류에 대한 종합적인 설명
        
        **분석 원칙:**
        - 정확한 패션 용어 사용
        - 객관적이고 구체적인 설명
        - 색상 정보는 지정된 필드에서만 사용
        - 모델 착용 이미지에서는 모델과 배경이 반영되지 않은 {category}에 집중하여 분석
        - 태그는 정확한 값만 사용
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