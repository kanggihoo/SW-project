import asyncio
from .image_downloader import ImageDownloader
from caption.models.product import ImageManager
from .utils import images_to_base64

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
    
        
        
        
def parsing_data_for_llm(images:list[ImageManager] , target_size:int )->dict:
    """
    이미지 데이터를 LLM에 전달하기 위한 데이터 파싱
    
    Args:
        images: ImageManager 객체 리스트
        target_size: 이미지 크기
        
    Returns:
        dict: 각 key값에 맞는 이미지 데이터를 base64로 인코딩한 문자열
            example
            {
                "deep_caption_images": "base64_encoded_image",
                "color_images": "base64_encoded_image",
                "text_images": "base64_encoded_image",
                "success": True,
                "fail": 0
            }
    """
    result = {}
    deep_caption_images = [0]*3
    color_images = []
    text_images = []
    fail = 0
    for image in images:
        if image.pil_image is None:
            fail += 1
            continue
        if image.type == "front":
            deep_caption_images[0] = image.pil_image
        elif image.type == "back":
            deep_caption_images[1] = image.pil_image
        elif image.type == "model":
            deep_caption_images[2] = image.pil_image
        elif image.type == "color_variant":
            color_images.append((image.pil_image, image.folder_path))
        elif image.type == "text":
            text_images.append(image.pil_image)
    if color_images:
        color_images = [image[0] for image in sorted(color_images, key=lambda x: x[1])]
    result["fail"] = fail
    if len(deep_caption_images) == 3 and len(color_images): 
        result["deep_caption_images"] = images_to_base64(deep_caption_images, target_size=target_size , type="image")
        result["color_images"] = images_to_base64(color_images, target_size=target_size, type="image")
        if text_images:
            result["text_images"] = images_to_base64(text_images, target_size=target_size, type="text")
        else:
            result["text_images"] =[]
        result["success"] = True
    else:
        result["success"] = False
    return result
        
        
        
            