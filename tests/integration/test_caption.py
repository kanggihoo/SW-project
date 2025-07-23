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
from processing.image_processor import download_images_sync , parsing_data_for_llm
from caption.models.product import ImageManager, ProductManager, Base64DataForLLM
from caption.fashion_caption_generator import FashionCaptionGenerator
from caption.prompt.text_image_ocr_prompt_template import TextImageOCRPrompt
from caption.config import Config


logger = logging.getLogger(__name__)

# 기존 로깅 설정 fixture 유지
@pytest.fixture(autouse=True , scope="session")
def setup_logging():
    root = logging.getLogger()
    root.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s : %(filename)s - %(lineno)d')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    

# AWS Manager fixture
@pytest.fixture(scope="session")
def aws_manager():
    return AWSManager()

class TestImagePipeline:
    @pytest.fixture
    def first_item(self, aws_manager: AWSManager, item_index: int=0)->dict:
        """제품 데이터를 가져오는 fixture
        
        Args:
            item_index (int, optional): 가져올 아이템의 인덱스. Defaults to 0.
        """
        paginator = aws_manager.dynamodb_manager.get_product_pagenator(
            partition={"key":"sub_category_curation_status","value":"1005#COMPLETED","type":"S"},
            GSI_NAME = "CurationStatus-SubCategory-GSI"
        )
        
        first_page = next(iter(paginator))
        item = first_page['Items'][item_index]
        item = aws_manager.dynamodb_manager._convert_dynamodb_item_to_python(item)
        logger.info(f"first_item product_id: {item['product_id']}")

        return item

    @pytest.fixture
    def product_images_url(self, aws_manager: AWSManager, first_item:dict)->list[ImageManager]:
        """제품 이미지 URL 정보를 가져오는 fixture"""
        images = aws_manager.get_product_images_from_paginator(first_item)
        assert images is not None and len(images) > 0
        return images
    
    @pytest.fixture
    def product_pil_images(self, product_images_url:list[ImageManager])->list[ImageManager]:
        """s3 url로 부터 PIL 이미지 정보 ImageManager에 저장"""
        #CHECK : 동기함수 말고 await 키워드로도 비동기함수 바로 호출하도록 가능할 수도 ?
        download_images_sync(product_images_url)
        return product_images_url
    
    @pytest.fixture
    def base64_data_for_llm(self, product_pil_images:list[ImageManager])->Base64DataForLLM:
        return parsing_data_for_llm(product_pil_images, target_size=512)
    
   
    def test_1_paginator_validation(self, aws_manager: AWSManager):
        """1단계: DynamoDB 페이지네이터 검증 테스트"""
        paginator = aws_manager.dynamodb_manager.get_product_pagenator(
            partition={"key":"sub_category_curation_status","value":"1005#COMPLETED","type":"S"},
            GSI_NAME = "CurationStatus-SubCategory-GSI"
        )
        
        assert paginator is not None
        first_page = next(iter(paginator))
        assert first_page is not None
        assert 'Items' in first_page
        assert 'Count' in first_page
        assert first_page['Count'] > 0
        
        # first_item = first_page['Items'][1]
        # assert 'product_id' in first_item
        # assert 'representative_assets' in first_item

    def test_2_dynamodb_product_fetch(self, first_item):
        """2단계: DynamoDB에서 제품 데이터 조회 테스트"""
        print(first_item)
        assert first_item is not None
        assert 'product_id' in first_item
        assert 'representative_assets' in first_item

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
    def test_data_processing_for_llm(self , product_pil_images:list[ImageManager]):
        result:Base64DataForLLM = parsing_data_for_llm(product_pil_images, target_size=224)
        assert result.success is True
        assert result.fail == 0
        assert result.deep_caption is not None
        assert result.color_images is not None
        assert result.text_images is not None

        # Visualize the processed images
        image_types = {
            "Deep Caption Images": result.deep_caption,
            "Color Images": result.color_images,
            "Text Images": result.text_images
        }

        plt.figure(figsize=(20, 5))

        plot_idx = 1
        for type_name, img in image_types.items():
            # base64 디코딩 및 PIL 이미지로 변환
            if isinstance(img, str):
                # base64 문자열을 PIL 이미지로 변환
                img_data = base64.b64decode(img)
                img = Image.open(BytesIO(img_data))

            plt.subplot(1, len(image_types), plot_idx)
            plt.imshow(img)
            plt.title(type_name)
            plt.axis('off')
            plot_idx += 1

        plt.tight_layout()
        plt.show()

        logger.info(f"Deep caption image processed")
        logger.info(f"Color image processed")
        logger.info(f"Text image processed")
    def test_text_image_ocr(self , base64_data_for_llm:Base64DataForLLM):
        # assert base64_data_for_llm.success is True
        fashion_caption_generator = FashionCaptionGenerator()
        model = fashion_caption_generator.ocr_chain
        config = Config()
        config = RunnableConfig(
            {
                "tags": [config.get("DEFAULT_OCR_MODEL")],
                "run_name": "test_text_image_ocr"
            }
        )
        result = model.invoke(base64_data_for_llm.text_images, config=config)
        print(result)

    def test_fashion_caption_generator(self , base64_data_for_llm:Base64DataForLLM):
        fashion_caption_generator = FashionCaptionGenerator()
        assert base64_data_for_llm.success is True

        #TODO : 텍스트 이미지 없는 경우에는 ??? 
        result = fashion_caption_generator.invoke(base64_data_for_llm , category="상의")
        assert result is not None
        assert result["deep_caption"] is not None
        assert result["color_images"] is not None
        print(result["deep_caption"].model_dump())
        print("*"*100)
        print(result["color_images"].model_dump())
        print("*"*100)
        print(result.get("text_images").model_dump() if result.get("text_images") else "no text image")
 

