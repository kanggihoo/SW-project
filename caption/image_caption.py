import base64
import os
from pprint import pprint
from typing import List, Optional, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI

# 이미지 전처리 모듈 import
from .image_preprocessing import preprocess_and_concat_images, pil_to_base64

# --- 1. Pydantic 클래스 설계 (데이터 구조의 Python 표현) ---
# JSON 구조를 Pydantic 모델로 변환하여 VLM의 출력 형식을 강제합니다.
# 각 필드에 description을 추가하여 VLM에게 의도를 더 명확히 전달합니다.

class SleeveLength(str, Enum):
    SLEEVELESS = "민소매"
    SHORT_SLEEVE = "반소매"
    FIVE_QUARTER_SLEEVE = "5부"
    SEVEN_QUARTER_SLEEVE = "7부"
    LONG_SLEEVE = "긴소매"

class BodyLength(str, Enum):
    CROP = "크롭"
    REGULAR = "레귤러(골반선)"
    LONG = "롱(힙 덮음)"
    MAXI = "맥시"
    
class NecklineType(str, Enum):
    ROUND_NECK = "라운드넥"
    V_NECK = "V넥"
    U_NECK = "U넥"
    SQUARE_NECK = "스퀘어넥"
    SHIRT_COLLAR = "셔츠 칼라"
    HIGH_NECK = "하이넥"

class PatternType(str, Enum):
    NONE = "없음"
    STRIPE = "스트라이프"
    DOT = "도트"
    CHECK = "체크"
    FLORAL = "플로럴"
    GRAPHIC = "그래픽"

class FitType(str, Enum):
    SLIM = "슬림핏"
    REGULAR = "레귤러핏"
    OVERSIZED = "오버핏"
    RELAXED = "릴렉스핏"

class SilhouetteType(str, Enum):
    A_LINE = "A라인"
    H_LINE = "H라인"
    I_LINE = "I라인"
    X_LINE = "X라인"
    MERMAID = "머메이드"

class ColorDetail(BaseModel):
    name: str = Field(description="색상의 한글 이름")
    hex: str = Field(description="예상되는 HEX 코드. 예: #4A90E2")

class PatternInfo(BaseModel):
    type: PatternType = Field(description="패턴의 종류")
    description: Optional[str] = Field(description="패턴에 대한 시각적인 상세 설명")

class EmbellishmentDetail(BaseModel):
    type: str = Field(description="장식/여밈의 종류. 예: 버튼, 지퍼, 포켓, 리본, 프릴, 자수, 플리츠")
    position: str = Field(description="해당 디테일의 위치. 예: 중앙 여밈, 왼쪽 가슴, 등 중앙")
    description: Optional[str] = Field(description="디테일에 대한 추가적인 설명")

class CommonAttributes(BaseModel):
    category_l1: str = Field(description="상품의 대분류. 예: 상의, 하의, 아우터")
    category_l2: str = Field(description="상품의 세부 분류. 예: 셔츠, 티셔츠, 블라우스")
    color: dict[Literal["primary", "secondary"], ColorDetail | List[ColorDetail]] = Field(description="주요 색상과 보조 색상 정보")
    sleeve_length: SleeveLength = Field(description="소매 기장")
    body_length: BodyLength = Field(description="전체 기장")

class FrontAttributes(BaseModel):
    neckline: NecklineType = Field(description="넥라인 형태")
    pattern: PatternInfo = Field(description="정면에서 보이는 패턴 정보")
    closures_and_embellishments: List[EmbellishmentDetail] = Field(description="정면의 여밈 및 장식 요소 정보 리스트")

class BackAttributes(BaseModel):
    pattern: PatternInfo = Field(description="후면에서 보이는 패턴 정보")
    closures_and_embellishments: List[EmbellishmentDetail] = Field(description="후면의 장식 요소 정보 리스트")

class SubjectiveAttributes(BaseModel):
    fit: FitType = Field(description="모델 착용샷 기반의 핏감")
    silhouette: SilhouetteType = Field(description="전체적인 실루엣")
    style_tags: List[str] = Field(description="느껴지는 스타일 키워드 리스트 (최대 3개)")
    mood_tags: List[str] = Field(description="느껴지는 분위기 키워드 리스트 (최대 3개)")
    tpo_tags: List[str] = Field(description="추천 TPO 키워드 리스트 (최대 3개)")

class StructuredAttributes(BaseModel):
    common: CommonAttributes
    front: FrontAttributes
    back: BackAttributes
    subjective: SubjectiveAttributes

class EmbeddingCaptions(BaseModel):
    clip_text_front: str = Field(description="CLIP 모델 학습용. 정면 이미지의 객관적 시각 특징을 상세히 묘사한 캡션.")
    design_details_description: str = Field(description="다중 임베딩(디자인)용. 의류의 구조와 디자인 특징을 설명하는 캡션.")
    style_vibe_description: str = Field(description="다중 임베딩(스타일)용. 이 옷이 연출하는 스타일과 감성을 설명하는 캡션.")
    tpo_context_description: str = Field(description="다중 임베딩(TPO)용. 이 옷의 추천 활용 상황을 설명하는 캡션.")
    comprehensive_description: str = Field(description="단일 임베딩(초기)용. 모든 정보를 종합한 최종 상품 설명문.")

class MasterCaption(BaseModel):
    """VLM으로부터 추출할 의류 정보의 전체 마스터 데이터 구조"""
    structured_attributes: StructuredAttributes = Field(description="필터링 및 UI 구성을 위한 구조화된 속성 정보")
    embedding_captions: EmbeddingCaptions = Field(description="벡터 검색 임베딩에 사용될 다양한 목적의 자연어 캡션")

# --- 2. LangChain 프롬프트 및 체인 구성 ---

# Pydantic 파서 생성: VLM이 이 구조에 맞춰 출력하도록 강제
parser = PydanticOutputParser(pydantic_object=MasterCaption)

# VLM 모델 초기화 (Gemini 1.5 Pro Vision 모델 사용)
# temperature=0으로 설정하여 더 일관성 있고 사실에 기반한 출력을 유도
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-001",
    temperature=0,
    # project="YOUR_GCP_PROJECT_ID" # 필요한 경우 프로젝트 ID 지정
)

# 프롬프트 템플릿 정의
prompt_template = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""당신은 고도로 숙련된 패션 전문 MD이자 AI 콘텐츠 생성 전문가입니다. 당신의 임무는 주어진 1개의 복합 의류 이미지를 정밀하게 분석하여, 사용자가 요청한 JSON 형식에 맞춰 모든 정보를 최대한 정확하게 추출하고 생성하는 것입니다.
- 제공되는 이미지는 의류의 '정면(누끼컷)', '후면(누끼컷)', '모델 착용샷(정면)' 3가지 뷰가 하나로 합쳐져 있습니다. 모든 뷰의 정보를 종합적으로 활용하여 답변해야 합니다.
- 모든 정보는 제공된 이미지에서 시각적으로 확인할 수 있는 내용에 기반해야 합니다.
- 특정 필드에 해당하는 정보가 없거나 판단이 불가능할 경우, 해당 필드의 값은 `null`을 사용하십시오.
- 모든 텍스트 설명과 태그 값은 반드시 한국어로 작성해야 합니다."""
        ),
        HumanMessage(
            content=[
                {"type": "text", "text": "아래 지침에 따라, 주어진 이미지를 분석하고 전체 JSON 객체를 완성해 주십시오.\n{format_instructions}"},
                {"type": "image_url", "image_url": "data:image/jpeg;base64,{image_data}"},
            ]
        ),
    ]
)

# LCEL을 이용한 체인 구성
# 프롬프트 -> 모델 -> 파서 순서로 파이프라인을 연결
chain = prompt_template | model | parser


# --- 3. 체인 실행 (Invoke) ---

def encode_image(image_path):
    """이미지 파일을 Base64로 인코딩하는 함수"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# def get_caption_from_image(image_path):
#     """이미지 경로를 받아 캡션 정보를 추출하는 메인 함수"""
#     try:
#         # 이미지를 Base64로 인코딩
#         base64_image = encode_image(image_path)
        
#         # 체인 실행
#         print("VLM 모델을 호출하여 캡션 정보를 추출합니다...")
#         result = chain.invoke({
#             "image_data": base64_image,
#             "format_instructions": parser.get_format_instructions()
#         })
#         print("정보 추출이 완료되었습니다.")
#         return result
        
#     except FileNotFoundError:
#         print(f"오류: 이미지 파일을 찾을 수 없습니다. 경로를 확인하세요: {image_path}")
#         return None
#     except Exception as e:
#         print(f"오류가 발생했습니다: {e}")
#         return None


def get_caption_from_multiple_images(image_paths, target_size=224, concat_direction='horizontal'):
    """
    여러 이미지를 전처리하고 합쳐서 VLM에 전달하는 함수
    
    Args:
        image_paths: 이미지 파일 경로 리스트
        target_size: 각 이미지의 목표 크기
        concat_direction: 'horizontal' 또는 'vertical'
    
    Returns:
        VLM 분석 결과 (MasterCaption 객체)
    """
    try:
        # 이미지 전처리 및 합치기
        combined_image = preprocess_and_concat_images(
            image_paths, 
            target_size, 
            concat_direction
        )
        
        # PIL Image를 base64로 변환
        base64_image = pil_to_base64(combined_image)
        
        # VLM 체인 호출
        print("VLM 모델을 호출하여 캡션 정보를 추출합니다...")
        result = chain.invoke({
            "image_data": base64_image,
            "format_instructions": parser.get_format_instructions()
        })
        print("정보 추출이 완료되었습니다.")
        return result
        
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        return None


def get_caption_from_multiple_images(image_paths, target_size=224, concat_direction='horizontal'):
    """
    여러 이미지를 전처리하고 합쳐서 VLM에 전달하는 함수
    
    Args:
        image_paths: 이미지 파일 경로 리스트
        target_size: 각 이미지의 목표 크기
        concat_direction: 'horizontal' 또는 'vertical'
    
    Returns:
        VLM 분석 결과 (MasterCaption 객체)
    """
    try:
        # 이미지 전처리 및 합치기
        combined_image = preprocess_and_concat_images(
            image_paths, 
            target_size, 
            concat_direction
        )
        
        # PIL Image를 base64로 변환
        base64_image = pil_to_base64(combined_image)
        
        # VLM 체인 호출
        print("VLM 모델을 호출하여 캡션 정보를 추출합니다...")
        result = chain.invoke({
            "image_data": base64_image,
            "format_instructions": parser.get_format_instructions()
        })
        print("정보 추출이 완료되었습니다.")
        return result
        
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        return None


# --- 실행 예시 ---
if __name__ == "__main__":
    # # 방법 1: 단일 복합 이미지 사용 (기존 방식)
    # single_image_path = "path/to/your/composite_image.jpg"
    # result1 = get_caption_from_image(single_image_path)
    
    # 방법 2: 여러 개별 이미지를 합쳐서 사용 (신규 방식)
    multiple_images = [
        "path/to/front_image.jpg",
        "path/to/back_image.jpg", 
        "path/to/model_wearing.jpg"
    ]
    '''
    여기서 모델 이미지만 존재할 수도 있고, 의류 이미지만 존재할 수도 있어서 
    케이스 분리해서 prompt 메세지 변경해야하고, 상의, 하의에 따라서 다르게 작업하고 

    
    '''
    result2 = get_caption_from_multiple_images(
        multiple_images, 
        target_size=224, 
        concat_direction='horizontal'
    )
    
    # 결과 출력 (방법 2 사용)
    if result2:
        print("\n--- 추출된 마스터 캡션 데이터 ---")
        pprint(result2.model_dump())
        
        # 추출된 데이터 활용 예시
        print("\n--- 데이터 활용 예시 ---")
        print(f"스타일 태그: {result2.structured_attributes.subjective.style_tags}")
        print(f"초기 임베딩용 통합 캡션: {result2.embedding_captions.comprehensive_description}")