import asyncio
from .image_downloader import ImageDownloader
from aws.product_models import ImageManager


async def download_images(images:list[ImageManager]):
    """
    비동기 환경에서 여러 제품의 이미지들을 한번에 다운로드
    
    Args:
        products: ProductManager 객체 리스트
    """
    async with ImageDownloader() as downloader:
        await downloader.download_images(images)


def download_images_sync(images:list[ImageManager]):
    """
    동기 환경에서 여러 제품의 이미지들을 다운로드하는 래퍼 함수
    
    Args:
        products: ProductManager 객체 리스트
    """
    asyncio.run(download_images(images))
    
        
        
        
        
        
        
        
            