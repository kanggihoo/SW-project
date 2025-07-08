import aiohttp
import asyncio
import logging
from io import BytesIO
from typing import Optional
from PIL import Image
from aws.product_models import ImageManager
from aiohttp import ClientTimeout

class ImageDownloader:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        }
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_pil_image_from_s3_url(self, image: ImageManager, timeout: int = 30) -> None:
        """
        Asynchronously downloads an image from a URL and sets it to the image.pil_image attribute.
        Args:
            image: ImageManager instance containing the image URL
            timeout: Request timeout in seconds
        """
        try:
            if image.s3_url is None:
                self.logger.warning(f"No S3 URL provided for image: {image}")
                return

            if not self.session:
                self.logger.error("No active session. Please use context manager or initialize session.")
                return

            timeout_obj = ClientTimeout(total=timeout)
            async with self.session.get(image.s3_url, headers=self.headers, timeout=timeout_obj) as response:
                response.raise_for_status()
                content = await response.read()
                
                image_stream = BytesIO(content)
                try:
                    pil_image = Image.open(image_stream).convert("RGB")
                    image.pil_image = pil_image
                finally:
                    image_stream.close()

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout while downloading image: {image.s3_url}")
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error while downloading image: {image.s3_url}, error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while downloading image: {image.s3_url}, error: {e}", exc_info=True)

    async def download_images(self, images: list[ImageManager], timeout: int = 30) -> None:
        """
        Downloads multiple images in parallel and sets them to their respective ImageManager instances.
        Args:
            images: List of ImageManager instances
            timeout: Request timeout in seconds
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        tasks = [self._get_pil_image_from_s3_url(image, timeout) for image in images]
        await asyncio.gather(*tasks)  # We don't need to return anything since we modify images in place

    async def close(self):
        """Explicitly close the session if not using context manager"""
        if self.session:
            await self.session.close()
            self.session = None

# async def download_image(images: list, timeout: int = 30) -> Optional[BytesIO]:
#     """
#     비동기적으로 이미지를 다운로드하고 BytesIO 객체로 반환합니다.
    
#     Args:
#         url (str): 다운로드할 이미지의 URL
#         timeout (int): 요청 타임아웃 시간(초), 기본값 30초
        
#     Returns:
#         Optional[BytesIO]: 성공시 이미지가 담긴 BytesIO 객체, 실패시 None
#     """
#     try:
#         timeout_obj = ClientTimeout(total=timeout)
#         async with aiohttp.ClientSession(timeout=timeout_obj) as session:
#             async with session.get(url) as response:
#                 if response.status == 200:
#                     image_data = await response.read()
#                     return BytesIO(image_data)
#                 else:
#                     print(f"Failed to download image. Status code: {response.status}")
#                     return None
#     except Exception as e:
#         print(f"Error downloading image from {url}: {str(e)}")
#         return None

# async def download_multiple_images(urls: list[str], timeout: int = 30) -> list[Optional[BytesIO]]:
#     """
#     여러 이미지를 동시에 비동기적으로 다운로드합니다.
    
#     Args:
#         urls (list[str]): 다운로드할 이미지 URL들의 리스트
#         timeout (int): 각 요청의 타임아웃 시간(초), 기본값 30초
        
#     Returns:
#         list[Optional[BytesIO]]: 다운로드된 이미지들의 BytesIO 객체 리스트
#     """
#     tasks = [download_image(url, timeout) for url in urls]
#     return await asyncio.gather(*tasks)

# 사용 예시
# from processing.image_downloader import ImageDownloader
# from aws.product_models import ImageManager

# async def process_images(image_list: list[ImageManager]):
#     # async with 구문을 사용하면 세션이 자동으로 생성되고 정리됩니다
#     async with ImageDownloader() as downloader:
#         await downloader.download_images(image_list)
#         # 이 시점에서 image_list의 각 ImageManager 객체에 pil_image가 설정되어 있습니다
        
#     # 여기서 image_list를 사용할 수 있습니다
#     for image in image_list:
#         if hasattr(image, 'pil_image') and image.pil_image is not None:
#             # 이미지 처리 작업 수행
#             process_pil_image(image.pil_image)