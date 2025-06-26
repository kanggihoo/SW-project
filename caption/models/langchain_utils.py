"""
Langchain과 VLM 모델 통합을 위한 유틸리티 함수들
"""

from typing import Type, Any, Dict
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from .master_data import DeepCaptioningOutput, SimpleAttributeOutput


def create_vlm_parser(model_class: Type[BaseModel]) -> PydanticOutputParser:
    """
    VLM 출력을 위한 Pydantic 파서를 생성합니다.
    
    Args:
        model_class: 파싱할 Pydantic 모델 클래스
        
    Returns:
        PydanticOutputParser: 설정된 파서 객체
    """
    return PydanticOutputParser(pydantic_object=model_class)


def create_deep_captioning_prompt() -> PromptTemplate:
    """
    딥 캡셔닝을 위한 프롬프트 템플릿을 생성합니다.
    """
    parser = create_vlm_parser(DeepCaptioningOutput)
    
    template = """
    당신은 패션 상품 이미지를 분석하는 전문가입니다.
    
    주어진 이미지를 보고 색상을 제외한 모든 상품 정보를 상세히 분석해주세요.
    특히 다음 사항들에 집중해주세요:
    
    1. 카테고리 (상의, 하의, 원피스 등)
    2. 디자인 디테일 (넥라인, 소매길이, 패턴, 여밈방식 등)
    3. 핏과 실루엣
    4. 스타일과 무드 (캐주얼, 포멀, 미니멀 등)
    5. TPO (착용 상황과 목적)
    
    중요: 색상 관련 정보는 절대 포함하지 마세요.
    
    이미지: {image_data}
    
    {format_instructions}
    """
    
    return PromptTemplate(
        template=template,
        input_variables=["image_data"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )


def create_simple_attribute_prompt() -> PromptTemplate:
    """
    단순 속성 추출 (색상)을 위한 프롬프트 템플릿을 생성합니다.
    """
    parser = create_vlm_parser(SimpleAttributeOutput)
    
    template = """
    당신은 상품 이미지에서 색상 정보를 정확히 추출하는 전문가입니다.
    
    주어진 이미지들을 보고 각 SKU의 색상 정보만 분석해주세요:
    
    1. 주 색상과 부 색상 식별
    2. 정확한 색상명과 HEX 코드
    3. 색상 속성 (밝기, 채도, 톤감 등)
    4. 해당 색상에 맞는 간단한 설명문
    
    중요: 색상 정보만 추출하고, 디자인이나 스타일 정보는 포함하지 마세요.
    
    상품 그룹 ID: {product_group_id}
    이미지 데이터: {image_data}
    SKU 정보: {sku_info}
    
    {format_instructions}
    """
    
    return PromptTemplate(
        template=template,
        input_variables=["product_group_id", "image_data", "sku_info"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )


def validate_and_fix_vlm_output(
    raw_output: str, 
    target_model: Type[BaseModel]
) -> BaseModel:
    """
    VLM 원시 출력을 검증하고 필요시 수정하여 Pydantic 모델로 변환합니다.
    
    Args:
        raw_output: VLM의 원시 출력 텍스트
        target_model: 목표 Pydantic 모델 클래스
        
    Returns:
        BaseModel: 검증된 모델 인스턴스
        
    Raises:
        ValueError: 파싱에 실패한 경우
    """
    parser = create_vlm_parser(target_model)
    
    try:
        # 직접 파싱 시도
        return parser.parse(raw_output)
    except Exception as e:
        # 파싱 실패시 후처리 로직 적용
        # 여기에 일반적인 VLM 출력 오류 수정 로직을 추가
        cleaned_output = _clean_vlm_output(raw_output)
        try:
            return parser.parse(cleaned_output)
        except Exception as e2:
            raise ValueError(f"VLM 출력 파싱 실패: {e2}") from e2


def _clean_vlm_output(raw_output: str) -> str:
    """
    VLM 출력에서 일반적인 오류를 수정합니다.
    """
    # JSON 코드 블록 마커 제거
    cleaned = raw_output.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    
    # 불필요한 앞뒤 공백 제거
    cleaned = cleaned.strip()
    
    # 기타 일반적인 정리 작업들...
    
    return cleaned


def get_model_schema_description(model_class: Type[BaseModel]) -> str:
    """
    Pydantic 모델의 스키마를 사람이 읽기 쉬운 형태로 반환합니다.
    """
    schema = model_class.model_json_schema()
    
    def format_property(name: str, prop: Dict[str, Any], level: int = 0) -> str:
        indent = "  " * level
        prop_type = prop.get("type", "unknown")
        description = prop.get("description", "")
        
        result = f"{indent}- {name} ({prop_type})"
        if description:
            result += f": {description}"
        result += "\n"
        
        # 중첩된 객체 처리
        if "properties" in prop:
            for sub_name, sub_prop in prop["properties"].items():
                result += format_property(sub_name, sub_prop, level + 1)
                
        return result
    
    description = f"모델: {model_class.__name__}\n\n"
    description += "필드 구조:\n"
    
    for prop_name, prop_info in schema.get("properties", {}).items():
        description += format_property(prop_name, prop_info)
    
    return description 