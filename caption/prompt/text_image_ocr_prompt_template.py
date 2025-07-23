# 텍스트 ocr 관련 pormpt 템플릿 생성

"""
의류 색상 분석을 위한 VLM 프롬프트 템플릿 모듈
"""
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from typing import Any, Optional
from langchain_core.runnables import RunnableConfig, Runnable
from caption.config import LLMInputKeys

#TODO : 사이즈 , fit 관련 정보는 이미 존재하는지 여부에 따라서 프롬프트 조정되도록 
# System Prompt for Color Analysis
system_template = """
당신은 의류 상품관련 텍스트 이미지에서 필요한 상품 정보를 정확하게 추출하는 전문가입니다.

주어진 이미지는 의류 상품의 상세 정보가 포함된 텍스트 이미지입니다. 
이미지에서 텍스트를 읽고 다음 정보들을 구조화하여 추출해주세요. 단, 추출하려는 정보가 없는경우 null로 설정해주세요.
## 추출 대상 정보
1. 소재 정보 (material_info)
2. 사이즈 정보 (size_info) 
**주의사항**:
- 사이즈명은 이미지에 표시된 그대로 사용 (S, M, L, FREE, 55, 66 등)
- 측정 항목명도 이미지에 표시된 그대로 사용 (총장, 가슴단면, 어깨너비, 소매길이 등)
- 데이터 추출시 데이터 형식을 준수해주세요.
3. 의류를 관리 시 주의 사항에 대한 정보 (care_info)
4. 의류의 소개 문구, 주요특징을 종합하여 요약한 상품 설명 (product_description)

## 추출 제외 정보
다음 정보들은 추출하지 마세요!
- 회사 소개 및 브랜드 철학
- 배송/교환/환불 정책
- 고객 서비스(CS) 정보
- 연락처, 운영시간 등

## 데이터 추출 원칙
1. **정확성 우선**: 명확하게 읽히는 정보만 추출
2. **구조화**: 각 정보를 지정된 필드에 정확히 매핑
3. **null 처리**: 해당 정보가 없는 경우 null로 설정
이미지에서 텍스트를 정확히 읽고, 위 구조에 맞춰 의류 정보를 체계적으로 추출해주세요.
"""
system_template_no_size = """
당신은 의류 상품관련 텍스트 이미지에서 필요한 상품 정보를 정확하게 추출하는 전문가입니다.

주어진 이미지는 의류 상품의 상세 정보가 포함된 텍스트 이미지입니다. 
이미지에서 텍스트를 읽고 다음 정보들을 구조화하여 추출해주세요. 단, 추출하려는 정보가 없는경우 null로 설정해주세요.
## 추출 대상 정보
1. 소재 정보 (material_info)
2. 의류를 관리 시 주의 사항에 대한 정보 (care_info)
3. 의류의 소개 문구, 주요특징을 종합하여 요약한 상품 설명 (product_description)

## 추출 제외 정보
다음 정보들은 추출하지 마세요!
- 회사 소개 및 브랜드 철학
- 배송/교환/환불 정책
- 고객 서비스(CS) 정보
- 연락처, 운영시간 등

## 데이터 추출 원칙
1. **정확성 우선**: 명확하게 읽히는 정보만 추출
2. **구조화**: 각 정보를 지정된 필드에 정확히 매핑
3. **null 처리**: 해당 정보가 없는 경우 null로 설정
이미지에서 텍스트를 정확히 읽고, 위 구조에 맞춰 의류 정보를 체계적으로 추출해주세요.
"""

human_template = [
    {
        "type": "text",
        "text": "분석할 이미지를 보고 지정된 구조에 맞춰 상세한 분석 결과를 제공해주세요."
    },
    {
        "type": "image_url",
        "image_url": "data:image/jpeg;base64,{image_data}"
    }
]

class TextImageOCRPrompt(Runnable):
    def __init__(self , include_size:bool = True):
        self.include_size = include_size
        self.prompt = self._make_prompt()
    
    def _get_system_template(self):
        if self.include_size:
            return system_template
        else:
            return system_template_no_size
        
    def _make_prompt(self):
        system_template = self._get_system_template()
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])
    
    def invoke(self, input: dict[str, Any], config: Optional[RunnableConfig] = None, **kwargs: Any) -> Any:
        return self.prompt.invoke(input, config, **kwargs)

    def extract_chain_input(self, kwargs: dict) -> dict[str, Any]:
        llm_input = kwargs.get(LLMInputKeys.TEXT_IMAGES)
        image_data = llm_input.get("image_data")
        if image_data is None:
            raise ValueError("image_data 가필요합니다.")
        return {
            "image_data": image_data
        }

    
__all__ = [
    "TextImageOCRPrompt"
    ]