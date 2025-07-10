import pytest
import logging
import sys
from PIL import Image
import matplotlib.pyplot as plt
from pathlib import Path
from aws.aws_manager import AWSManager
from caption.models.product import ImageManager, ProductManager
from processing.image_processor import download_images_sync
from processing import utils 

logger = logging.getLogger(__name__)

# 기존 로깅 설정 fixture 유지
@pytest.fixture(autouse=True , scope="session")
def setup_logging():
    root = logging.getLogger()
    root.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)

# AWS Manager fixture
@pytest.fixture(scope="session")
def aws_manager():
    return AWSManager()

class TestImagePipeline:
    @pytest.fixture
    def first_item(self, aws_manager: AWSManager, item_index: int)->dict:
        """제품 데이터를 가져오는 fixture
        
        Args:
            item_index (int, optional): 가져올 아이템의 인덱스. Defaults to 0.
        """
        paginator = aws_manager.dynamodb_manager.get_product_pagenator(
            sub_category=1005, 
            condition={"curation_status": "COMPLETED"}
        )
        
        first_page = next(iter(paginator))
        item = first_page['Items'][item_index]
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
        download_images_sync(product_images_url)
        return product_images_url
    
    # def test_1_paginator_validation(self, aws_manager: AWSManager):
    #     """1단계: DynamoDB 페이지네이터 검증 테스트"""
    #     paginator = aws_manager.dynamodb_manager.get_product_pagenator(
    #         sub_category=1005, 
    #         condition={"curation_status": "COMPLETED"}
    #     )
        
    #     assert paginator is not None
    #     first_page = next(iter(paginator))
    #     assert first_page is not None
    #     assert 'Items' in first_page
    #     assert 'Count' in first_page
    #     assert first_page['Count'] > 0
        
    #     first_item = first_page['Items'][1]
    #     assert 'product_id' in first_item
    #     assert 'representative_assets' in first_item

    # def test_2_dynamodb_product_fetch(self, first_item):
    #     """2단계: DynamoDB에서 제품 데이터 조회 테스트"""
    #     assert first_item is not None
    #     assert 'product_id' in first_item
    #     assert 'representative_assets' in first_item

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

    # @pytest.mark.parametrize("item_index", [2])
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

    #TODO : 캡션 모듈을 이용한 테스트 코드 작성 필요 
    def test_caption(self , product_pil_images:list[ImageManager]):
        ...


