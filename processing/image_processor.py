import asyncio
from .image_downloader import ImageDownloader
from caption.models.product import ImageManager
from .utils import images_to_base64
from caption.models.product import Base64DataForLLM

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
    
        
        
def parsing_data_for_llm(images:list[ImageManager] , target_size:int )->Base64DataForLLM:
    """
    이미지 데이터를 LLM에 전달하기 위한 데이터 파싱
    
    Args:
        images: ImageManager 객체 리스트
        target_size: 이미지 크기
        
    Returns:
        Base64DataForLLM: 딥캡션, 색상, 텍스트 이미지 데이터를 Base64로 변환한 데이터
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
        result["deep_caption"] = images_to_base64(deep_caption_images, target_size=target_size , type="image")
        result["color_images"] = images_to_base64(color_images, target_size=target_size, type="image")
        if text_images:
            result["text_images"] = images_to_base64(text_images, target_size=target_size, type="text")
        else:
            result["text_images"] =""
        result["success"] = True
        result["color_count"] = len(color_images)
    else:
        result["success"] = False
    return Base64DataForLLM(**result)
        
        
        
# TODO : 하나의 page에 있는 모든 이미지를 처리하는 코드 추가 
'''
한 페이지에 있는 모든 이미지를 한번에 비동기로 s3로 부터 메모리에 업로드 하고 
이제 다시 동기코드(PIL) 이용해서 threadPoolExecutor 이용해서 이미지 처리 후 처

'''