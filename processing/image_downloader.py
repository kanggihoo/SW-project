import aiohttp
import asyncio
from io import BytesIO
from typing import Optional
from aiohttp import ClientTimeout

async def download_image(url: str, timeout: int = 30) -> Optional[BytesIO]:
    """
    비동기적으로 이미지를 다운로드하고 BytesIO 객체로 반환합니다.
    
    Args:
        url (str): 다운로드할 이미지의 URL
        timeout (int): 요청 타임아웃 시간(초), 기본값 30초
        
    Returns:
        Optional[BytesIO]: 성공시 이미지가 담긴 BytesIO 객체, 실패시 None
    """
    try:
        timeout_obj = ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return BytesIO(image_data)
                else:
                    print(f"Failed to download image. Status code: {response.status}")
                    return None
    except Exception as e:
        print(f"Error downloading image from {url}: {str(e)}")
        return None

async def download_multiple_images(urls: list[str], timeout: int = 30) -> list[Optional[BytesIO]]:
    """
    여러 이미지를 동시에 비동기적으로 다운로드합니다.
    
    Args:
        urls (list[str]): 다운로드할 이미지 URL들의 리스트
        timeout (int): 각 요청의 타임아웃 시간(초), 기본값 30초
        
    Returns:
        list[Optional[BytesIO]]: 다운로드된 이미지들의 BytesIO 객체 리스트
    """
    tasks = [download_image(url, timeout) for url in urls]
    return await asyncio.gather(*tasks)

# 사용 예시
async def main():
    # 단일 이미지 다운로드
    image_url = "https://example.com/image.jpg"
    image_data = await download_image(image_url)
    if image_data:
        print("Image downloaded successfully!")
    
    # 여러 이미지 동시 다운로드
    image_urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg"
    ]
    images = await download_multiple_images(image_urls)
    print(f"Downloaded {len([img for img in images if img is not None])} images successfully")

if __name__ == "__main__":
    asyncio.run(main())
