"""
Langchain Gemini 모델을 사용한 패션 상품 이미지 분석 및 캡션 생성
"""

from pathlib import Path
import logging
from typing import List, Optional, Dict, Any
from langchain.schema.runnable import RunnableParallel , RunnableLambda


from dotenv import load_dotenv
from processing.utils import images_to_base64 
from .langchain_utils import setup_langsmith_tracing, setup_gemini_model
from .models import DeepCaptioningTopOutput, SimpleAttributeOutput
from .models.product import ImageManager, Base64DataForLLM
from .prompt import ColorCaptionPrompt, DeepImageCaptionPrompt
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
        self.model_name = self.config.get("DEFAULT_CAPTION_MODEL")
        self.temperature = self.config.get("DEFAULT_TEMPERATURE")


        # langsmith tracing 설정 
        if self.config.get("DEFAULT_TRACING_ENABLED"):
            setup_langsmith_tracing(
                enable_tracing=self.config.get("DEFAULT_TRACING_ENABLED"),
                project_name=self.config.get("DEFAULT_LANGCHAIN_PROJECT_NAME")
            )

    def _load_model(self, model_name: str):
        """Gemini 모델 로드"""
        return setup_gemini_model(model_name, temperature=self.temperature)

    def _setup_chains(self):
        """Chain 초기화 및 설정"""
        # Deep Captioning Chain 설정
        deep_model = self._load_model(self.model_name)
        deep_structured_model = deep_model.with_structured_output(DeepCaptioningTopOutput)
        deep_prompt = DeepImageCaptionPrompt()
        self.deep_chain = deep_prompt | deep_structured_model

        # Color Analysis Chain 설정
        color_model = self._load_model(self.model_name)
        color_structured_model = color_model.with_structured_output(SimpleAttributeOutput)
        color_prompt = ColorCaptionPrompt()
        self.color_chain = color_prompt | color_structured_model

        # Parallel Chain 설정
        self.parallel_chain = RunnableParallel(
            deep_caption=RunnableLambda(deep_prompt.extract_chain_input) | self.deep_chain,
            color_images=RunnableLambda(color_prompt.extract_chain_input) | self.color_chain
        )

    def invoke(
        self,
        base64_data_for_llm: Base64DataForLLM,
        category: str = "상의",
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
            results = self.parallel_chain.invoke(llm_input)
            self.logger.info("이미지 분석 완료")

            return results

        except Exception as e:
            self.logger.error(f"이미지 분석 중 오류 발생: {e}")
            raise

    #TODO : LLM 반환 결과 대해서 데이터 저장을 위해 parsing 하는 코드 필요. 


# if __name__ == "__main__":
#     main() 


# def main():
#     # 환경변수 로드
#     load_dotenv()
    
#     # LangSmith tracing 설정
#     # setup_langsmith_tracing(
#     #     enable_tracing=True,  # 필요에 따라 False로 변경
#     #     project_name="fashion-caption-analysis"  # 원하는 프로젝트 이름으로 변경
#     # )
    
#     # """메인 실행 함수"""
#     print("🚀 Langchain Gemini를 사용한 패션 이미지 분석 시작\n")

    
#     # DATA_DIR = Path(__file__).parent / "data"
#     # sample_images = [
#     #     DATA_DIR / "front.jpg",  # 정면 누끼 이미지
#     #     DATA_DIR / "back.jpg",   # 후면 누끼 이미지  
#     #     DATA_DIR / "model.jpg"   # 모델 착용 이미지
#     # ]
    
#     # # 실제 테스트용 이미지가 있는지 확인
#     existing_images = []
#     for img_path in sample_images:
#         if os.path.exists(img_path):
#             existing_images.append(img_path)
#         else:
#             print(f"⚠️  이미지 파일이 없습니다: {img_path}")
    
    
#     try:
#         # 1. 딥 캡셔닝 분석
#         # gemini-2.5-flash-lite-preview-06-17
#         # gemini-2.5-pro-preview-06-05
#         # gemini-2.5-flash
#         # print(f"\n1️⃣ 딥 캡셔닝 분석 ({len(existing_images)}개 이미지)")
#         # deep_result = analyze_fashion_images_deep_captioning(
#         #     image_paths=existing_images,
#         #     target_size=384,
#         #     category="상의",
#         #     model_name="gemini-2.5-flash-lite-preview-06-17"
#         # )
#         # print(deep_result)
        
        
#         # 2. 색상 속성 분석
#         print(f"\n\n2️⃣ 색상 속성 분석")
#         color_result = analyze_fashion_images_simple_attributes(
#             image_paths=existing_images[:2],
#             target_size=224,
#             product_group_id="TEST_001",
#             category="상의",
#             model_name="gemini-2.0-flash"
#         )
#         print(color_result)
        
#         # print(f"\n✅ 모든 분석이 완료되었습니다!")
        
#     except Exception as e:
#         print(f"\n❌ 분석 중 오류 발생: {e}")
#         import traceback
#         traceback.print_exc()


# if __name__ == "__main__":
#     # main()
#     import logging
#     from processing.image_processor import download_images_sync
#     from aws.aws_manager import AWSManager
#     logging.basicConfig(level=logging.INFO)
#     logger = logging.getLogger(__name__)
    
#     aws_manager = AWSManager()
#     pagenator = aws_manager.dynamodb_manager.get_product_pagenator(sub_category=1005 , condition={"curation_status":"COMPLETED"})
#     for page in pagenator:
#         items = page.get('Items')
#         logger.info(f"현재 총 제품 수 : {page.get('Count')}")
#         if items:
#             for item in items:
#                 print(item.get('product_id') , item.get('sub_category') , item.get('main_category') , item.get('representative_assets') , item.get('text') )
#                 images = aws_manager.get_product_images_from_paginator(item)
#                 logger.info(f"이미지 정보 리스트 : {images}")   
#                 download_images_sync(images)
#                 print(images)
#                 break
#         break
    