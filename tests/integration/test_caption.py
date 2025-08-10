import pytest
import logging
import sys
from PIL import Image
import matplotlib.pyplot as plt
from pathlib import Path
import base64
from io import BytesIO
from langchain_core.runnables import RunnableLambda , RunnableConfig

from aws.aws_manager import AWSManager
from processing.image_processor import download_images , parsing_data_for_llm
from caption.models.product import ImageManager, ProductManager, Base64DataForLLM
from caption.fashion_caption_generator import FashionCaptionGenerator
from caption.prompt.text_image_ocr_prompt_template import TextImageOCRPrompt
from caption.config import Config
from db import create_fashion_repo
from db.repository.fashion_sync import FashionRepository
from dataclasses import dataclass
from caption_generation import parsing_caption_result , setup_dependencies , CaptionDependency

# logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - %(levelname)s - %(message)s : %(filename)s - %(lineno)d' , datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

@dataclass
class ImageSize:
    deep_caption_size : int 
    color_caption_size : int
    text_caption_size : int

# 기존 로깅 설정 fixture 유지
# @pytest.fixture(autouse=True , scope="session")
# def setup_logging():
#     root = logging.getLogger()
#     root.handlers = []
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setLevel(logging.DEBUG)
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s : %(filename)s - %(lineno)d')
#     handler.setFormatter(formatter)
    # root.addHandler(handler)
    
@pytest.fixture(scope="session")
def fashion_repo() -> FashionRepository:
    return create_fashion_repo()

# AWS Manager fixture
@pytest.fixture(scope="session")
def aws_manager() -> AWSManager:
    return AWSManager()

class TestImagePipeline:

    @pytest.fixture
    def caption_dependency(self):
        def _get_dependency(deep_caption_size:int=512, color_caption_size:int=224, text_caption_size:int=512):
            return setup_dependencies()
        return _get_dependency

    @pytest.fixture
    def first_item_from_dynamodb(self, aws_manager: AWSManager)->dict:
        """제품 데이터를 가져오는 fixture
        
        Args:
            item_index (int, optional): 가져올 아이템의 인덱스. Defaults to 0.
        """
        def _get_item(sub_category:int, product_id:str)->dict:
            item = aws_manager.dynamodb_manager.get_item(
                sub_category=sub_category,
                product_id=product_id
            )
            return item
        
        return _get_item
    
    @pytest.fixture
    def first_item_from_fashion_repo(self, fashion_repo:FashionRepository)->dict:
        def _get_item(product_id:str)->dict:
            return fashion_repo.find_by_id(product_id)
        return _get_item

    @pytest.fixture
    def product_images_url(self, aws_manager: AWSManager, first_item:dict)->list[ImageManager]:
        """제품 이미지 URL 정보를 가져오는 fixture"""
        images = aws_manager.get_product_images_from_paginator(first_item)
        assert images is not None and len(images) > 0
        return images
    
    # @pytest.fixture
    # async def product_pil_images(self, product_images_url:list[ImageManager])->list[ImageManager]:
    #     """s3 url로 부터 PIL 이미지 정보 ImageManager에 저장"""
        
    #     await download_images(product_images_url)
    #     return product_images_url
    
    # @pytest.fixture
    # def base64_data_for_llm(self, product_pil_images:list[ImageManager])->Base64DataForLLM:
    #     return parsing_data_for_llm(product_pil_images, ImageSize(deep_caption_size=512, color_caption_size=224, text_caption_size=512))
    

    # def test_3_image_url_extraction(self, product_images_url:list[ImageManager]):
    #     """3단계: 제품 데이터에서 이미지 URL 추출 테스트"""
    #     assert len(product_images_url) > 0
    #     for image in product_images_url:
    #         assert isinstance(image, ImageManager)
    #         assert image.s3_url is not None
    #         assert image.s3_url.startswith('https://')
    #         assert image.type in ['model', 'front', 'back', 'text' , 'color_variant']

    # @pytest.mark.parametrize("item_index", [1])
    # def test_4_image_download(self, product_images_url:list[ImageManager]):
    #     """4단계: S3 이미지 다운로드 테스트"""
    #     download_images_sync(product_images_url)
        
    #     for image in product_images_url:
    #         assert hasattr(image, 'pil_image')
    #         assert image.pil_image is not None
    #         assert isinstance(image.pil_image, Image.Image)

    # @pytest.mark.parametrize("item_index", [1])
    # def test_5_pil_image_check(self, product_pil_images:list[ImageManager]):
    #     plt.figure(figsize=(15, 5))
    #     for idx, image in enumerate(product_pil_images, 1):
    #         assert image.pil_image is not None
    #         assert isinstance(image.pil_image, Image.Image)

    #         plt.subplot(1, len(product_pil_images), idx)
    #         plt.imshow(image.pil_image)
    #         plt.title(f'Image Type: {image.type} , Image folder : {image.s3_key}')
    #         plt.axis('off')  # Hide axes for cleaner visualization

    #         logger.info(f'Image Type: {image.type} , Image folder : {image.s3_key}')
            

    #     plt.tight_layout()
    #     plt.show()

    #TODO : 지금은 하나의 pagenation을 통해 하나의 제품에 대한 테스트만 이루어져 있지만 실제 모든 pagenation을 통해 동작되는지 확인필요
    #TODO : page 맨 마지막에 에러 처리 해야 하는지 아니면 단순 for문으로 구현한다면 stopiteration 처리가 되지만 그래도 확인필요
    # def test_data_processing_for_llm(self , product_pil_images:list[ImageManager]):
    #     result:Base64DataForLLM = parsing_data_for_llm(product_pil_images, target_size=224)
    #     assert result.success is True
    #     assert result.fail == 0
    #     assert result.deep_caption is not None
    #     assert result.color_images is not None
    #     assert result.text_images is not None

    #     # Visualize the processed images
    #     image_types = {
    #         "Deep Caption Images": result.deep_caption,
    #         "Color Images": result.color_images,
    #         "Text Images": result.text_images
    #     }

    #     plt.figure(figsize=(20, 5))

    #     plot_idx = 1
    #     for type_name, img in image_types.items():
    #         # base64 디코딩 및 PIL 이미지로 변환
    #         if isinstance(img, str):
    #             # base64 문자열을 PIL 이미지로 변환
    #             img_data = base64.b64decode(img)
    #             img = Image.open(BytesIO(img_data))

    #         plt.subplot(1, len(image_types), plot_idx)
    #         plt.imshow(img)
    #         plt.title(type_name)
    #         plt.axis('off')
    #         plot_idx += 1

    #     plt.tight_layout()
    #     plt.show()

    #     logger.info(f"Deep caption image processed")
    #     logger.info(f"Color image processed")
    #     logger.info(f"Text image processed")
    @pytest.mark.asyncio
    async def test_caption_generation(self , caption_dependency:CaptionDependency , first_item_from_dynamodb , first_item_from_fashion_repo):
        # assert base64_data_for_llm.success is True
        dep = caption_dependency()
        # item = first_item_from_dynamodb(sub_category=1002, product_id="5121016")
        use_dynamodb = True
        try:
            if use_dynamodb:
                item = first_item_from_dynamodb(sub_category=1002, product_id="5047698")
                logger.info(f"item : {item}")
                
                main_category = item.get('main_category')
                sub_category = item.get('sub_category')
                product_id = item.get('product_id')
                representative_assets = item.get('representative_assets')
                logger.info(f"main_category : {main_category} , sub_category : {sub_category} , product_id : {product_id}")
                category = "상의" if main_category.lower() == "top" else "하의"
                images = dep.aws_manager.get_product_images_from_paginator(item)

                await download_images(images)
                base64_data_for_llm = parsing_data_for_llm(images, dep.size)
                has_size = True if item.get("size_detail_info") else False
                result = await dep.fashion_caption_generator.ainvoke(base64_data_for_llm , category=category , has_size=has_size)
            else:
                item = first_item_from_fashion_repo(product_id="3042516")
                converted_item = item
        except Exception as e:
            logger.error(f"Error caption generation: {e} , product_id : {product_id}")
            dep.fashion_repository_local.update_by_id(product_id, {"data_status": "CA_ERR", "error_message" : str(e)})
            # return False

        
        # caption_result = parsing_caption_result(result, representative_assets)
        # print(caption_result)


        

    # def test_fashion_caption_generator(self , base64_data_for_llm:Base64DataForLLM):
    #     fashion_caption_generator = FashionCaptionGenerator()
    #     assert base64_data_for_llm.success is True

    #     #TODO : 텍스트 이미지 없는 경우에는 ??? 
    #     result = fashion_caption_generator.invoke(base64_data_for_llm , category="상의" , has_size=False)
    #     assert result is not None
    #     assert result["deep_caption"] is not None
    #     assert result["color_images"] is not None
    #     print(result["deep_caption"].model_dump())
    #     print("*"*100)
    #     print(result["color_images"].model_dump())
    #     print("*"*100)
    #     print(result.get("text_images").model_dump() if result.get("text_images") else "no text image")
 

