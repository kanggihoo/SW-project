"""
Langchain Gemini 모델을 사용한 패션 상품 이미지 분석 및 캡션 생성
"""

from pathlib import Path
import logging
from typing import List, Optional, Dict, Any
from langchain.schema.runnable import RunnableParallel , RunnableLambda
from langchain_core.runnables import RunnableConfig


from dotenv import load_dotenv
from processing.utils import images_to_base64 
from .langchain_utils import setup_langsmith_tracing, setup_gemini_model
from .models import DeepCaptioningTopOutput, DeepCaptioningBottomOutput, SimpleAttributeOutput, TextImageOCROutput_Full, TextImageOCROutput_NoSize
from .models.product import ImageManager, Base64DataForLLM
from .prompt import ColorCaptionPrompt, DeepImageCaptionPrompt, TextImageOCRPrompt
from .config import Config, LLMInputKeys
import logging 
logger = logging.getLogger(__name__)
class FashionCaptionGenerator:
    def __init__(self, config: Config = None):
        """패션 이미지 캡션 생성기 초기화"""
        self._init(config)
        self._setup_chains()

    # =============================================================================
    # 초기화 함수 
    # =============================================================================
    def _init(self, config: Config = None):
        load_dotenv()
        if config is None:
            self.config = Config()
        else:
            self.config = config
        # self.model_name = self.config.get("DEFAULT_CAPTION_MODEL")
        self.caption_temperature = self.config.get("DEFAULT_CAPTION_TEMPERATURE")
        self.ocr_temperature = self.config.get("DEFAULT_OCR_TEMPERATURE")


        # langsmith tracing 설정 
        if self.config.get("DEFAULT_TRACING_ENABLED"):
            setup_langsmith_tracing(
                enable_tracing=self.config.get("DEFAULT_TRACING_ENABLED"),
                project_name=self.config.get("DEFAULT_LANGCHAIN_PROJECT_NAME")
            )
        else:
           logger.info("LangSmith tracing is disabled")

    def _load_model(self, model_name: str , temperature: float = 0.0):
        """Gemini 모델 로드"""
        return setup_gemini_model(model_name, temperature=temperature)

    def _setup_chains(self):
        """Chain 초기화 및 설정"""
        # Deep Captioning Chain 설정
        self.deep_model = self._load_model(self.config.get("DEFAULT_CAPTION_MODEL") , self.caption_temperature)
        self.deep_prompt = DeepImageCaptionPrompt()

        # deep_structured_model = deep_model.with_structured_output(DeepCaptioningTopOutput)
        # self.deep_prompt = DeepImageCaptionPrompt()
        # self.deep_chain = self.deep_prompt | deep_structured_model

        # Color Analysis Chain 설정
        color_model = self._load_model(self.config.get("DEFAULT_COLOR_MODEL") , self.caption_temperature)
        color_structured_model = color_model.with_structured_output(SimpleAttributeOutput)
        self.color_prompt = ColorCaptionPrompt()
        self.color_chain = self.color_prompt | color_structured_model

        # OCR Chain 설정 (동적으로 생성하므로 기본 모델만 로드 )
        self.ocr_model = self._load_model(self.config.get("DEFAULT_OCR_MODEL"), self.ocr_temperature)

    
    def _validate_image_data(self, image_data: str, data_type: str) -> bool:
        """base64 이미지 데이터 유효성 검증"""
        if not image_data or image_data.strip() == "":
            logger.warning(f"{data_type} 이미지 데이터가 비어있습니다.")
            return False
        return True

    def _build_dynamic_chain(self , llm_input:dict[str , Any] , category: str, has_size: bool = True )-> RunnableParallel:
        """동적 체인 생성"""
        chain_components = {}
        if self._validate_image_data(llm_input[LLMInputKeys.DEEP_CAPTION]["image_data"] , "Deep Caption"):
            if category == "상의":
                deep_structured_model = self.deep_model.with_structured_output(DeepCaptioningTopOutput)
                deep_chain = self.deep_prompt | deep_structured_model
                chain_components[LLMInputKeys.DEEP_CAPTION] = RunnableLambda(self.deep_prompt.extract_chain_input) | deep_chain
            elif category == "하의":
                deep_structured_model = self.deep_model.with_structured_output(DeepCaptioningBottomOutput)
                deep_chain = self.deep_prompt | deep_structured_model
                chain_components[LLMInputKeys.DEEP_CAPTION] = RunnableLambda(self.deep_prompt.extract_chain_input) | deep_chain
            else:
                raise ValueError(f"Invalid category(Deep Caption을 위한 카테고리 값 오류) : {category}")
        else:
            raise ValueError("Deep Caption 이미지 데이터가 비어있습니다.")
        
        if self._validate_image_data(llm_input[LLMInputKeys.COLOR_IMAGES]["image_data"] , "Color Images"):
            chain_components[LLMInputKeys.COLOR_IMAGES] = RunnableLambda(self.color_prompt.extract_chain_input) | self.color_chain
        else:
            raise ValueError("Color Images 이미지 데이터가 비어있습니다.")
        
        if self._validate_image_data(llm_input[LLMInputKeys.TEXT_IMAGES]["image_data"] , "Text Images"):
            include_size = not has_size
            ocr_chain , ocr_prompt = self._create_ocr_chain(include_size)
            chain_components[LLMInputKeys.TEXT_IMAGES] = RunnableLambda(ocr_prompt.extract_chain_input) | ocr_chain


        return RunnableParallel(**chain_components)

    def _create_ocr_chain(self , include_size: bool = True)-> tuple[RunnableLambda, RunnableLambda]:
        """OCR 체인 생성 및 프롬프트 반환

        Args:
            has_size (bool, optional): 사이즈 정보 포함 여부. Defaults to True.
        Returns:
            tuple[RunnableLambda, RunnableLambda]: (OCR 체인 , OCR 프롬프트)
        """
        
        output_model = TextImageOCROutput_Full if include_size else TextImageOCROutput_NoSize
        prompt = TextImageOCRPrompt(include_size=include_size)
        structured_model = self.ocr_model.with_structured_output(output_model)

        return prompt | structured_model , prompt

    def invoke(
        self,
        base64_data_for_llm: Base64DataForLLM,
        category: str,
        has_size: bool = True,
        config: RunnableConfig = None
    ) -> Dict[str, Any]:
        """상품 이미지 분석 실행"""
        llm_input = {
            LLMInputKeys.DEEP_CAPTION: {
                "category": category,
                "image_data": base64_data_for_llm.deep_caption,
            },
            LLMInputKeys.COLOR_IMAGES: {
                "count": base64_data_for_llm.color_count,
                "category": category,
                "image_data": base64_data_for_llm.color_images,
            },
            LLMInputKeys.TEXT_IMAGES: {
                "image_data": base64_data_for_llm.text_images,
            }
        }
        try:
            # 병렬 실행 및 결과 반환
            dynamic_parallel_chain = self._build_dynamic_chain(llm_input , has_size=has_size , category=category)
            logger.info("이미지 분석 시작...")
            results = dynamic_parallel_chain.invoke(llm_input , config=config)
            logger.info("이미지 분석 완료")

            return results

        except Exception as e:
            logger.error(f"이미지 분석 중 오류 발생: {e}")
