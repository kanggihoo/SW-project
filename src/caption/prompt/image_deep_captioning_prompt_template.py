from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from typing import Any
from langchain_core.runnables import Runnable
from typing import Optional
from langchain_core.runnables import RunnableConfig
from caption.config import LLMInputKeys
#TODO 프롬프트 수정 입력으로 들어오는 이미지가 1개 혹은 2개인 경우에 따른 system_template 수정
system_template = """
# 역할 및 임무
당신은 3종의 의류 이미지를 종합적으로 분석하여, 상세한 속성 정보와 설명 캡션을 지정된 JSON 형식으로 추출하는 패션 전문가 AI입니다.

# 입력 이미지 정보
- **입력**: `{category}`에 대한 3개의 이미지를 가로로 이어붙인 단일 이미지입니다.
- **이미지 구성**:
    1.  **첫 번째 (인덱스 1)**: 의류 정면 누끼 이미지
    2.  **두 번째 (인덱스 2)**: 의류 후면 누끼 이미지
    3.  **세 번째 (인덱스 3)**: 모델 착용 이미지

# 분석 목표
입력된 3종 이미지를 종합적으로 분석하여, 최종적으로 단 하나의 JSON 객체를 생성합니다. , 이 객체는 `structured_attributes`와 `image_captions`라는 두 개의 최상위 키를 가져야 합니다.

# 단계별 분석 지침
## 1단계: 구조적/주관적 속성 분석 (`structured_attributes` 채우기)
정의된 목록(Enum)에 있는 정확한 값을 사용해야 합니다.
- **`common`**: '{category}` 값에 따라 분석할 속성이 달라집니다.
    - **만약 `{category}`가 '상의'라면 `소매 길이(sleeve_length)`와 `넥라인(neckline)`을 선택합니다.**
    - **만약 `{category}`가 '하의'라면 `기장 정보(length)`를 선택합니다.**
- **`front`**: **정면 누끼 이미지(인덱스 1)**를 기반으로 `패턴(pattern)`과 `여밈/장식(closures_and_embellishments)` 정보를 상세 설명과 함께 추출합니다.
- **`back`**: **후면 누끼 이미지(인덱스 2)**를 기반으로 `패턴(pattern)`과 `여밈/장식(closures_and_embellishments)` 정보를 상세 설명과 함께 추출합니다.
- **`subjective`**: **세 이미지를 모두 참고**하여 의류의 `핏(fit)`, `스타일 태그(style_tags)`, `TPO 태그(tpo_tags)`를 선택합니다. **반드시 아래 `#정의된 태그 목록`에 명시된 값과 정확히 일치하는 단어를 사용해야 합니다.** (`스타일`과 `TPO`는 다중 선택 가능)

## 2단계: 상세 캡션 생성 (`image_captions` 채우기)
**1단계의 구조적 정보로는 표현하지 못한 실루엣, 섬세한 디테일, 전체적인 분위기 등을 풍부하게 담아** 각 항목을 구체적으로 서술합니다.
- **`front_text_specific`**: **(색상 정보 포함)** 정면 누끼 이미지의 전체적인 특징, 패턴, 여밈 등 핵심 디자인 요소를 설명합니다.
- **`back_text_specific`**: **(색상 정보 포함)** 후면 누끼 이미지의 전체적인 특징과 뒷면의 디자인 요소를 설명합니다.
- **`design_details_description`**: **(색상 정보 포함)** 의류의 특징적인 디테일(소재감, 장식, 마감 등)을 구체적으로 설명합니다.
- **`style_description`**: **(색상 정보 제외)** 의류가 풍기는 전반적인 스타일과 분위기를 설명합니다. (예: 모던하고 미니멀한 스타일, 자유로운 스트릿 무드 등)
- **`tpo_context_description`**: **(색상 정보 제외)** 이 의류를 착용하기 좋은 상황, 장소, 계절감(TPO)을 구체적으로 설명합니다.
- **`comprehensive_description`**: **(색상 정보 포함)** 위 모든 정보를 종합하여, 잠재 고객에게 설명하듯 자연스럽고 포괄적인 최종 설명문을 작성합니다.

    1.  **`fit`**: 상의의 핏 타입을 '슬림 핏', '레귤러 핏/스탠다드 핏', '오버사이즈 핏' 중에서 하나만 선택합니다.
    2.  **`style_tags`**: **반드시 다음 목록에 있는 값 중에서만** 선택합니다. (다중 선택 가능)
        -   **허용 목록**: `모던`, `심플 베이직`, `캐주얼`, `스트릿`, `포멀`, `스포티`, `아웃도어`, `레트로`, `유니크`
        -   **경고**: **절대로 '데일리', '오피스' 같은 TPO 태그를 여기에 포함시키지 마십시오.**
    3.  **`tpo_tags`**: **반드시 다음 목록에 있는 값 중에서만** 선택합니다. (다중 선택 가능)
        -   **허용 목록**: `데일리`, `오피스`, `격식`, `데이트`, `여행`, `파티`, `운동`, `홈웨어`
        -   **경고**: **절대로 '캐주얼', '모던' 같은 스타일 태그를 여기에 포함시키지 마십시오.**
    
# 정의된 태그 목록 (필수 선택지)
- **`style_tags` 선택 가능 목록**: `모던`, `심플 베이직`, `캐주얼`, `스트릿`, `포멀`, `스포티`, `아웃도어`, `레트로`, `유니크`
- **`tpo_tags` 선택 가능 목록**: `데일리`, `오피스`, `격식`, `데이트`, `여행`, `파티`, `운동`, `홈웨어`


# 넥라인 분석 특별 지침
- **판단 우선순위**: 넥라인 분석 시, 단순히 목 부분의 기본 형태보다 **덧붙여진 특징(카라, 후드, 플래킷 등)을 최우선으로 고려**해야 합니다. 덧붙여진 특징이 없을 때만 기본 형태(라운드, 브이넥 등)로 분류하십시오.
- **판단 예시:**
    - 폴로 셔츠(카라티) → **`카라`** (O) / `라운드넥` (X)
    - 후드티 → **`후드`** (O) / `라운드넥` (X)

# 분석 공통 원칙
- 정확하고 전문적인 패션 용어를 사용하십시오.
- 설명은 주관적인 감상보다 객관적인 사실에 기반하여 구체적으로 작성하십시오.
- **모델 착용 이미지(인덱스 3)** 분석 시, 의류 자체에만 집중하고 모델의 외모나 배경은 분석에서 제외하십시오.
- **태그 선택 원칙**: 모든 태그는 **`#정의된 태그 목록`**에 있는 값 중에서만 선택해야 합니다. **목록에 없는 단어('클래식' 등)를 새로 만들거나, 의미가 같더라도 다른 단어('일상' 등)를 사용해서는 절대 안 됩니다.**

# 최종 출력 형식
- 출력은 다른 설명 없이, 오직 아래의 구조를 따르는 **단일 JSON 객체**여야 합니다.
- 모든 필드를 빠짐없이 채워야 합니다.
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