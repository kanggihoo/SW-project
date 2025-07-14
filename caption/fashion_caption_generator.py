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
from .models import DeepCaptioningTopOutput, SimpleAttributeOutput, TextImageOCROutput
from .models.product import ImageManager, Base64DataForLLM
from .prompt import ColorCaptionPrompt, DeepImageCaptionPrompt, TextImageOCRPrompt
from .config import Config, LLMInputKeys
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
            
        self.logger = logging.getLogger(__name__)
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
            self.logger.info("LangSmith tracing is disabled")

    def _load_model(self, model_name: str , temperature: float = 0.0):
        """Gemini 모델 로드"""
        return setup_gemini_model(model_name, temperature=temperature)

    def _setup_chains(self):
        """Chain 초기화 및 설정"""
        # Deep Captioning Chain 설정
        deep_model = self._load_model(self.config.get("DEFAULT_CAPTION_MODEL") , self.caption_temperature)
        deep_structured_model = deep_model.with_structured_output(DeepCaptioningTopOutput)
        deep_prompt = DeepImageCaptionPrompt()
        self.deep_chain = deep_prompt | deep_structured_model

        # Color Analysis Chain 설정
        color_model = self._load_model(self.config.get("DEFAULT_COLOR_MODEL") , self.caption_temperature)
        color_structured_model = color_model.with_structured_output(SimpleAttributeOutput)
        color_prompt = ColorCaptionPrompt()
        self.color_chain = color_prompt | color_structured_model

        # OCR Chain 설정
        ocr_model = self._load_model(self.config.get("DEFAULT_OCR_MODEL"), self.ocr_temperature)
        ocr_structured_model = ocr_model.with_structured_output(TextImageOCROutput)
        ocr_prompt = TextImageOCRPrompt()
        self.ocr_chain = ocr_prompt | ocr_structured_model

        # Parallel Chain 설정
        self.parallel_chain = RunnableParallel(
            deep_caption=RunnableLambda(deep_prompt.extract_chain_input) | self.deep_chain,
            color_images=RunnableLambda(color_prompt.extract_chain_input) | self.color_chain,
            text_images=RunnableLambda(ocr_prompt.extract_chain_input) | self.ocr_chain
        )

    def invoke(
        self,
        base64_data_for_llm: Base64DataForLLM,
        category: str,
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
            self.logger.info("이미지 분석 시작...")
            results = self.parallel_chain.invoke(llm_input , config=config)
            self.logger.info("이미지 분석 완료")

            return results

        except Exception as e:
            self.logger.error(f"이미지 분석 중 오류 발생: {e}")
            raise
