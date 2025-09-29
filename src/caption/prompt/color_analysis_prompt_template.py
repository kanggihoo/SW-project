"""
의류 색상 분석을 위한 VLM 프롬프트 템플릿 모듈
"""

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from typing import Any
from langchain_core.runnables import Runnable
from typing import Optional
from langchain_core.runnables import RunnableConfig
from caption.config import LLMInputKeys

# System Prompt for Color Analysis
system_template = """
당신은 여러 의류 이미지를 분석하여 지정된 JSON 형식으로 색상 정보를 추출하는 전문 AI입니다.
주어진 이미지를 분석하여 각 의류의 색상 정보를 정확히 추출하고, 반드시 요청된 JSON 구조에 맞춰 응답해야 합니다.

# 입력 이미지 정보 
- **입력 이미지**: 의류에 대한 이미지를 가로로 이어붙힌 단일 이미지 입니다.
- **구성**: 이미지는 **{count}개**의 개별 {category} 이미지로 구성되어 있습니다.
- **구분**: 각 개별 이미지는 **회색 배경**으로 구분되며 각 이미지의 좌측 상단에는 1부터 시작하는 인덱스 숫자가 표시됩니다.

# 분석 방법
왼쪽 첫 번째(인덱스 1) 이미지부터 순서대로 다음 분석을 수행하여, {count}개의 결과 객체를 포함하는 JSON 배열을 만드세요.
1. **HEX 코드 추출**: 각 이미지에서 가장 넓은 면적을 차지하는 의류의 **대표 색상을 HEX 코드로 먼저 정확하게 추출**합니다. (`#RRGGBB` 형식)
2. **대표 색상 매칭**: **추출된 HEX 코드**를 기준으로, '대표 색상 목록'에 있는 15개 색상 중 **가장 시각적으로 유사한 색상의 이름(name)을 선택**합니다.
3. **속성 평가**: **추출된 HEX 코드**를 기준으로, 해당 색상의 **명도(Brightness)와 채도(Saturation)를** '속성 목록'의 5단계 기준에 따라 각각 평가합니다.
4. **결과 통합**: 위 3단계의 결과(**`hex`, `name`, `attributes`**)를 하나의 JSON 객체로 통합합니다.

# 분석 규칙 
- **분석 대상**: 의류 자체의 색상에만 집중합니다. 배경, 액세서리, 로고, 그림자 등은 분석에서 **제외**합니다.
- **면적 기준**: 하나의 이미지에 여러 의류가 보여도, **가장 큰 면적을 차지하는 의류**를 기준으로 분석합니다.
- **패턴 처리**: 패턴이나 프린트가 있는 경우, 전체적인 인상을 주는 **지배적인 색상**을 선택합니다.
- **'멀티컬러' 조건**: 3가지 이상의 색상이 뚜렷하고 비슷한 비율로 섞여 단일 색상 식별이 어려울 때만 '멀티컬러'를 사용합니다.
- **순서 유지**: 최종 출력되는 JSON 배열의 순서는 **입력 이미지의 인덱스 순서(1, 2, 3, ...)**와 반드시 일치해야 합니다.
- **수량 일치**: 각 이미지에 대해 독립적으로 분석하여 **총 {count}개의 색상 정보를 추출**해야 합니다.

# DEFINITIONS
### 1. 대표 색상 목록 (PrimaryColor)
- 화이트, 그레이, 블랙, 레드, 핑크, 옐로우, 오렌지, 그린, 블루, 퍼플, 브라운, 베이지, 데님, 메탈릭, 멀티컬러
"""

human_template = [
    {'type': 'text', 'text': '분석할 {count} 개의 의류 이미지를 보고 지정된 구조에 맞춰 상세한 분석 결과를 제공해주세요.'},
    {'type': 'image_url', 'image_url': 'data:image/jpeg;base64,{image_data}'},
]


class ColorCaptionPrompt(Runnable):
    def __init__(self):
        self.prompt = self._make_prompt()

    def _make_prompt(self):
        return ChatPromptTemplate.from_messages(
            [SystemMessagePromptTemplate.from_template(system_template), HumanMessagePromptTemplate.from_template(human_template)]
        )

    def invoke(self, input: dict[str, Any], config: Optional[RunnableConfig] = None, **kwargs: Any) -> Any:
        return self.prompt.invoke(input, config, **kwargs)

    def extract_chain_input(self, kwargs: dict) -> dict[str, Any]:
        """
        체인 입력 데이터 생성

        Args:
            count: 분석할 이미지 개수
            category: 상품 카테고리 (예: "상의", "하의")
            image_data: Base64 인코딩된 이미지 데이터

        Returns:
            체인 호출을 위한 입력 딕셔너리
        """
        llm_input = kwargs.get(LLMInputKeys.COLOR_IMAGES)
        count = llm_input.get('count')
        category = llm_input.get('category')
        image_data = llm_input.get('image_data')
        if count is None or category is None or image_data is None:
            raise ValueError('count, category, image_data 모두 필요합니다.')
        return {'count': count, 'category': category, 'image_data': image_data}


__all__ = ['ColorCaptionPrompt']
