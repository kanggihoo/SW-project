"""
Langchain과 VLM 모델 통합을 위한 유틸리티 함수들
"""

from typing import Annotated
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .models.master_data import DeepCaptioningTopOutput, SimpleAttributeOutput
import os
import logging

logger = logging.getLogger(__name__)

def setup_langsmith_tracing(
    enable_tracing: bool = True,
    project_name: str|None = None,
    # api_key: Optional[str] = None
) -> None:
    """
    LangSmith tracing 설정
    
    Args:
        enable_tracing: tracing 활성화 여부 (기본값: True)
        project_name: LangSmith 프로젝트 이름 (기본값: None - 환경변수 사용)
    """
    
    if enable_tracing:
        # LangSmith tracing 활성화
        os.environ["LANGSMITH_TRACING"] = "true"
        
        # 프로젝트 이름 설정
        if project_name:
            os.environ["LANGSMITH_PROJECT"] = project_name
        elif not os.getenv("LANGSMITH_PROJECT"):
            # 기본 프로젝트 이름 설정
            os.environ["LANGSMITH_PROJECT"] = "fashion-image-analysis"
        
        current_project = os.getenv("LANGSMITH_PROJECT")
        logger.info(f"✅ LangSmith tracing 활성화됨 - 프로젝트: {current_project}")
        
    else:
        # LangSmith tracing 비활성화
        os.environ["LANGSMITH_TRACING"] = "false"
        logger.info("🔒 LangSmith tracing 비활성화됨")



def setup_gemini_model(model_name: str = "gemini-2.0-flash-001", temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    """Gemini 모델 설정"""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
    
    model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature
    )
    logger.info(f"✅ Gemini 모델 설정 완료: {model_name}")
    return model


def create_vlm_parser(model_class: BaseModel) -> PydanticOutputParser:
    """
    VLM 출력을 위한 Pydantic 파서를 생성합니다.
    """
    return PydanticOutputParser(pydantic_object=model_class)



def create_simple_attribute_prompt() -> ChatPromptTemplate:
    """
    단순 속성 추출 (색상)을 위한 프롬프트 템플릿을 생성합니다.
    """
    parser = create_vlm_parser(SimpleAttributeOutput)
    
    system_message = SystemMessage(content="""
    당신은 상품 이미지에서 색상 정보를 정확히 추출하는 전문가입니다.
    
    주어진 이미지들을 보고 각 SKU의 색상 정보만 분석해주세요:
    
    1. 주 색상과 부 색상 식별
    2. 정확한 색상명과 HEX 코드
    3. 색상 속성 (밝기, 채도, 톤감 등)
    4. 해당 색상에 맞는 간단한 설명문
    
    중요: 색상 정보만 추출하고, 디자인이나 스타일 정보는 포함하지 마세요.
    
    {format_instructions}
    """)
    
    human_message = HumanMessage(content="""
    상품 그룹 ID: {product_group_id}
    이미지 데이터: {image_data}
    SKU 정보: {sku_info}
    """)
    
    return ChatPromptTemplate.from_messages([
        system_message,
        human_message
    ]).partial(format_instructions=parser.get_format_instructions())


# def validate_and_fix_vlm_output(
#     raw_output: str, 
#     target_model: Type[BaseModel]
# ) -> BaseModel:
#     """
#     VLM 원시 출력을 검증하고 필요시 수정하여 Pydantic 모델로 변환합니다.
    
#     Args:
#         raw_output: VLM의 원시 출력 텍스트
#         target_model: 목표 Pydantic 모델 클래스
        
#     Returns:
#         BaseModel: 검증된 모델 인스턴스
        
#     Raises:
#         ValueError: 파싱에 실패한 경우
#     """
#     parser = create_vlm_parser(target_model)
    
#     try:
#         # 직접 파싱 시도
#         return parser.parse(raw_output)
#     except Exception as e:
#         # 파싱 실패시 후처리 로직 적용
#         # 여기에 일반적인 VLM 출력 오류 수정 로직을 추가
#         cleaned_output = _clean_vlm_output(raw_output)
#         try:
#             return parser.parse(cleaned_output)
#         except Exception as e2:
#             raise ValueError(f"VLM 출력 파싱 실패: {e2}") from e2


# def _clean_vlm_output(raw_output: str) -> str:
#     """
#     VLM 출력에서 일반적인 오류를 수정합니다.
#     """
#     # JSON 코드 블록 마커 제거
#     cleaned = raw_output.strip()
#     if cleaned.startswith("```json"):
#         cleaned = cleaned[7:]
#     if cleaned.endswith("```"):
#         cleaned = cleaned[:-3]
    
#     # 불필요한 앞뒤 공백 제거
#     cleaned = cleaned.strip()
    
#     # 기타 일반적인 정리 작업들...
    
#     return cleaned


# def get_model_schema_description(model_class: Type[BaseModel]) -> str:
#     """
#     Pydantic 모델의 스키마를 사람이 읽기 쉬운 형태로 반환합니다.
#     """
#     schema = model_class.model_json_schema()
    
#     def format_property(name: str, prop: Dict[str, Any], level: int = 0) -> str:
#         indent = "  " * level
#         prop_type = prop.get("type", "unknown")
#         description = prop.get("description", "")
        
#         result = f"{indent}- {name} ({prop_type})"
#         if description:
#             result += f": {description}"
#         result += "\n"
        
#         # 중첩된 객체 처리
#         if "properties" in prop:
#             for sub_name, sub_prop in prop["properties"].items():
#                 result += format_property(sub_name, sub_prop, level + 1)
                
#         return result
    
#     description = f"모델: {model_class.__name__}\n\n"
#     description += "필드 구조:\n"
    
#     for prop_name, prop_info in schema.get("properties", {}).items():
#         description += format_property(prop_name, prop_info)
    
#     return description


# def normalize_vlm_enum_values(data: dict) -> dict:
#     """
#     VLM 출력에서 enum 값들을 정규화하는 함수
#     """
#     # 스타일 태그 매핑
#     style_tag_mapping = {
#         "레트로": "빈티지/레트로",
#         "빈티지": "빈티지/레트로",
#         "모던": "모던/미니멀",
#         "미니멀": "모던/미니멀",
#         "베이직": "심플 베이직",
#         "심플": "심플 베이직",
#         "포멀": "포멀/클래식",
#         "클래식": "포멀/클래식",
#         "스포티": "스포티/애슬레저",
#         "애슬레저": "스포티/애슬레저",
#         "레귤러": "레귤러 핏/스탠다드 핏",
#         "스탠다드": "레귤러 핏/스탠다드 핏",
#         "레귤러 핏": "레귤러 핏/스탠다드 핏",
#         "스탠다드 핏": "레귤러 핏/스탠다드 핏"
#     }
    
#     # TPO 태그 매핑
#     tpo_tag_mapping = {
#         "오피스": "오피스/비즈니스",
#         "비즈니스": "오피스/비즈니스",
#         "격식": "격식/하객",
#         "하객": "격식/하객",
#         "데이트": "데이트/주말",
#         "주말": "데이트/주말",
#         "여행": "여행/휴가",
#         "휴가": "여행/휴가",
#         "파티": "파티/모임",
#         "모임": "파티/모임",
#         "홈웨어": "홈웨어/라운지",
#         "라운지": "홈웨어/라운지"
#     }
    
#     def normalize_tags(tags: list, mapping: dict) -> list:
#         """태그 리스트를 정규화"""
#         if not isinstance(tags, list):
#             return tags
        
#         normalized = []
#         for tag in tags:
#             if isinstance(tag, str):
#                 # 정확한 매핑이 있으면 사용
#                 if tag in mapping:
#                     normalized.append(mapping[tag])
#                 else:
#                     normalized.append(tag)
#             else:
#                 normalized.append(tag)
#         return normalized
    
#     # 데이터 정규화
#     if isinstance(data, dict):
#         # 중첩된 딕셔너리 처리
#         for key, value in data.items():
#             if key == "style_tags" and isinstance(value, list):
#                 data[key] = normalize_tags(value, style_tag_mapping)
#             elif key == "tpo_tags" and isinstance(value, list):
#                 data[key] = normalize_tags(value, tpo_tag_mapping)
#             elif key == "fit" and isinstance(value, str):
#                 # 핏 타입 정규화
#                 if value in style_tag_mapping:
#                     data[key] = style_tag_mapping[value]
#             elif isinstance(value, dict):
#                 data[key] = normalize_vlm_enum_values(value)
#             elif isinstance(value, list):
#                 data[key] = [normalize_vlm_enum_values(item) if isinstance(item, dict) else item for item in value]
    
#     return data 