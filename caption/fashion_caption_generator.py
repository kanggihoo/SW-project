"""
Langchain Gemini 모델을 사용한 패션 상품 이미지 분석 및 캡션 생성
"""

from pathlib import Path
import logging
from typing import List, Optional, Dict, Any
from langchain.schema.runnable import RunnableParallel


from dotenv import load_dotenv
from processing.utils import images_to_base64 
from .langchain_utils import setup_langsmith_tracing, setup_gemini_model
from .models import DeepCaptioningTopOutput, SimpleAttributeOutput
from .models.product import ImageManager
from .prompt import ColorCaptionPrompt, DeepImageCaptionPrompt
from .config import Config

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
        prompt = DeepImageCaptionPrompt()
        self.deep_chain = prompt | deep_structured_model

        # Color Analysis Chain 설정
        color_model = self._load_model(self.model_name)
        color_structured_model = color_model.with_structured_output(SimpleAttributeOutput)
        prompt = ColorCaptionPrompt()
        self.color_chain = prompt | color_structured_model

        # Parallel Chain 설정
        self.parallel_chain = RunnableParallel(
            deep_captioning=self.deep_chain,
            color_analysis=self.color_chain
        )
        return self.parallel_chain

    def prepare_images_for_chains(self, images: List[ImageManager], target_size: int = 224) -> Dict[str, str]:
        """이미지 데이터를 체인에 맞게 전처리"""
        try:
            # 이미지 분류
            deep_images = []  # 모든 이미지 사용
            color_images = []  # front, back 이미지만 사용

            for img in images:
                if img.pil_image:
                    deep_images.append(img.pil_image)
                    if img.type.lower() in ['front', 'back']:
                        color_images.append(img.pil_image)

            # 이미지 병합 및 base64 변환
            deep_merged = images_to_base64(deep_images, target_size=target_size)
            color_merged = images_to_base64(color_images, target_size=target_size)

            return {
                "deep_image": images_to_base64([deep_merged], target_size=target_size),
                "color_image": images_to_base64([color_merged], target_size=target_size)
            }
        except Exception as e:
            self.logger.error(f"이미지 전처리 중 오류 발생: {e}")
            raise

    def analyze_product_images(
        self,
        images: List[ImageManager],
        category: str = "상의",
        target_size: int = 224
    ) -> Dict[str, Any]:
        """상품 이미지 분석 실행"""
        try:
            # 이미지 전처리
            processed_images = self.prepare_images_for_chains(images, target_size)

            # Chain 입력 데이터 준비
            chain_inputs = {
                "deep_captioning": {
                    "category": category,
                    "image_data": processed_images["deep_image"]
                },
                "color_analysis": {
                    "count": len([img for img in images if img.type.lower() in ['front', 'back']]),
                    "category": category,
                    "image_data": processed_images["color_image"]
                }
            }

            # 병렬 실행 및 결과 반환
            self.logger.info("이미지 분석 시작...")
            results = self.parallel_chain.invoke(chain_inputs)
            self.logger.info("이미지 분석 완료")

            return results

        except Exception as e:
            self.logger.error(f"이미지 분석 중 오류 발생: {e}")
            raise

    #TODO : LLM 반환 결과 대해서 데이터 저장을 위해 parsing 하는 코드 필요. 
    # =============================================================================
    # 주요 기능 함수  (chain 만들고=>RunnablePaller로 하고) , chain을 invoke 하는 코드 작성 
    # =============================================================================

    def analyze_deep_captioning(
        self,
        image_paths: List[str], 
        target_size: int = 224,
        category: str = "상의",
    ) -> DeepCaptioningTopOutput:
        """
        딥 캡셔닝을 위한 패션 이미지 분석
        
        Args:
            image_paths: 분석할 이미지 파일 경로 리스트
            category: 상품 카테고리 (상의, 하의 등)
            model_name: 사용할 Gemini 모델명
            target_size: 이미지 크기 조정 목표 크기
        
        Returns:
            DeepCaptioningOutput: 분석 결과
        """
        self.logger.info(f"딥 캡셔닝 분석 시작 - 카테고리: {category}")
        
        try:
            base64_image = images_to_base64(image_paths, target_size=target_size)
            self.logger.info(f"이미지 Base64 인코딩 완료 (길이: {len(base64_image)})")
            
            model = setup_gemini_model(model_name)
            structured_model = model.with_structured_output(DeepCaptioningTopOutput)
            
            deep_chain = DeepImageCaptionPrompt().create_image_captioning_chain(structured_model)
            deep_chain_input = DeepImageCaptionPrompt().get_chain_input(category=category, image_data=base64_image)
            
            self.logger.info("VLM 분석 시작...")
            response = deep_chain.invoke(deep_chain_input)
            self.logger.info("VLM 응답 수신 완료")
            
            return response
            
        except Exception as e:
            self.logger.error(f"VLM 분석 중 오류 발생: {e}")
            raise

    def analyze_simple_attributes(
        self,
        image_paths: List[str],
        target_size: int = 224,
        product_group_id: str = "",
        category: str = "상의",
        model_name: str = "gemini-2.5-flash-lite-preview-06-17"
    ) -> SimpleAttributeOutput:
        """
        단순 속성 추출 (색상)을 위한 패션 이미지 분석
        
        Args:
            image_paths: 분석할 이미지 파일 경로 리스트
            product_group_id: 상품 그룹 ID
            category: 상품 카테고리
            model_name: 사용할 Gemini 모델명
            target_size: 이미지 크기 조정 목표 크기
        
        Returns:
            SimpleAttributeOutput: 분석 결과
        """
        self.logger.info(f"색상 속성 분석 시작 - 상품 그룹: {product_group_id}")
        
        try:
            base64_image = images_to_base64(image_paths, target_size=target_size)
            self.logger.info("이미지 Base64 인코딩 완료")
            
            model = setup_gemini_model(model_name, temperature=0)
            structured_model = model.with_structured_output(SimpleAttributeOutput)
            
            color_chain = ColorCaptionPrompt().create_color_captioning_chain(structured_model)
            color_chain_input = ColorCaptionPrompt().get_chain_input(
                count=len(image_paths),
                category=category,
                image_data=base64_image
            )
            
            self.logger.info("VLM 분석 시작...")
            response = color_chain.invoke(color_chain_input)
            self.logger.info("VLM 응답 수신 완료")
            
            return response
            
        except Exception as e:
            self.logger.error(f"VLM 분석 중 오류 발생: {e}")
            raise

    # def process_product_batch(self, sub_category: int, condition: dict):
    #     """
    #     DynamoDB에서 제품 배치를 처리하고 이미지를 분석
        
    #     Args:
    #         sub_category: 서브 카테고리 ID
    #         condition: 필터링 조건
    #     """
    #     pagenator = self.aws_manager.dynamodb_manager.get_product_pagenator(
    #         sub_category=sub_category,
    #         condition=condition
    #     )
        
    #     for page in pagenator:
    #         items = page.get('Items')
    #         self.logger.info(f"현재 총 제품 수: {page.get('Count')}")
            
    #         if not items:
    #             continue
                
    #         for item in items:
    #             product_id = item.get('product_id')
    #             self.logger.info(f"제품 처리 중: {product_id}")
                
    #             images = self.aws_manager.get_product_images_from_paginator(item)
    #             self.logger.info(f"이미지 정보 리스트: {images}")
                
    #             downloaded_images = download_images_sync(images)
    #             if downloaded_images:
    #                 # 여기에 이미지 분석 로직 추가
    #                 pass


# def main():
#     logging.basicConfig(level=logging.INFO)
    
#     caption_generator = FashionCaptionGenerator()
    
#     # 예시: 제품 배치 처리
#     caption_generator.process_product_batch(
#         sub_category=1005,
#         condition={"curation_status": "COMPLETED"}
#     )

    

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
    