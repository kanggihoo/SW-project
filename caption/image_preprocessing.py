import base64
import io
from typing import List, Union
from PIL import Image, ImageOps


def preprocess_and_concat_images(
    image_paths: List[str], 
    target_size: int = 224, 
    concat_direction: str = 'horizontal'
) -> Image.Image:
    """
    여러 이미지를 전처리하고 하나로 이어붙이는 함수
    
    Args:
        image_paths: 이미지 파일 경로 리스트
        target_size: 각 이미지의 목표 크기 (정사각형)
        concat_direction: 'horizontal' 또는 'vertical'
    
    Returns:
        합쳐진 PIL Image 객체
    
    Raises:
        FileNotFoundError: 이미지 파일을 찾을 수 없는 경우
        ValueError: 잘못된 concat_direction 값인 경우
    """
    if concat_direction not in ['horizontal', 'vertical']:
        raise ValueError("concat_direction은 'horizontal' 또는 'vertical'이어야 합니다.")
    
    processed_images = []
    
    # 각 이미지 전처리 (aspect ratio 유지 + 패딩)
    for path in image_paths:
        try:
            image = Image.open(path).convert('RGB')
            # ImageOps.pad: aspect ratio 유지하면서 목표 크기에 맞춰 패딩 추가
            processed = ImageOps.pad(
                image, 
                (target_size, target_size), 
                color=(0, 0, 0)  # 검정색 패딩
            )
            processed_images.append(processed)
        except FileNotFoundError:
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {path}")
    
    # 이미지 이어붙이기
    if concat_direction == 'horizontal':
        # 가로로 이어붙이기
        total_width = target_size * len(processed_images)
        combined = Image.new('RGB', (total_width, target_size))
        
        for i, img in enumerate(processed_images):
            combined.paste(img, (i * target_size, 0))
            
    else:  # vertical
        # 세로로 이어붙이기
        total_height = target_size * len(processed_images)
        combined = Image.new('RGB', (target_size, total_height))
        
        for i, img in enumerate(processed_images):
            combined.paste(img, (0, i * target_size))
    
    return combined


def resize_with_padding_single(
    image_path: str, 
    target_size: int = 224
) -> Image.Image:
    """
    단일 이미지를 aspect ratio 유지하면서 리사이징하고 패딩을 추가하는 함수
    
    Args:
        image_path: 이미지 파일 경로
        target_size: 목표 크기 (정사각형)
    
    Returns:
        전처리된 PIL Image 객체
    """
    image = Image.open(image_path).convert('RGB')
    processed = ImageOps.pad(
        image, 
        (target_size, target_size), 
        color=(0, 0, 0)  # 검정색 패딩
    )
    return processed


def pil_to_base64(image: Image.Image, format: str = 'JPEG', quality: int = 95) -> str:
    """
    PIL Image를 base64 문자열로 변환하는 함수
    
    Args:
        image: PIL Image 객체
        format: 이미지 포맷 ('JPEG', 'PNG' 등)
        quality: JPEG 품질 (1-100)
    
    Returns:
        base64로 인코딩된 문자열
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format, quality=quality)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def save_preprocessed_image(
    image_paths: List[str], 
    output_path: str,
    target_size: int = 224, 
    concat_direction: str = 'horizontal'
) -> None:
    """
    전처리된 이미지를 파일로 저장하는 함수
    
    Args:
        image_paths: 이미지 파일 경로 리스트
        output_path: 저장할 파일 경로
        target_size: 각 이미지의 목표 크기
        concat_direction: 'horizontal' 또는 'vertical'
    """
    combined_image = preprocess_and_concat_images(
        image_paths, target_size, concat_direction
    )
    combined_image.save(output_path, 'JPEG', quality=95)
    print(f"전처리된 이미지가 저장되었습니다: {output_path}")


def images_to_base64(
    image_paths: List[str],
    target_size: int = 224,
    concat_direction: str = 'horizontal'
) -> str:
    """
    여러 이미지를 전처리하고 합친 후 base64로 인코딩하는 함수
    
    Args:
        image_paths: 이미지 파일 경로 리스트
        target_size: 각 이미지의 목표 크기 (정사각형)
        concat_direction: 'horizontal' 또는 'vertical'
    
    Returns:
        base64로 인코딩된 문자열
        
    Raises:
        FileNotFoundError: 이미지 파일을 찾을 수 없는 경우
        ValueError: 잘못된 concat_direction 값인 경우
    """
    # 기존 함수를 이용해 이미지들을 전처리하고 합치기
    combined_image = preprocess_and_concat_images(
        image_paths, target_size, concat_direction
    )
    
    # PIL 이미지를 base64로 변환
    base64_string = pil_to_base64(combined_image)
    
    return base64_string


# --- 사용 예시 및 테스트 코드 ---
if __name__ == "__main__":
    # 예시 이미지 경로들
    from pathlib import Path
    DATA_DIR = Path("/Users/kkh/Desktop/1005")
    PRODUCT_ID = "674732"
    IMAGE_PATH = DATA_DIR / PRODUCT_ID / "segment"
    
    sample_images = [
        IMAGE_PATH / "0_1.jpg",
        IMAGE_PATH / "0_2.jpg", 
        IMAGE_PATH / "1_4.jpg"
    ]
    
    try:
        # 1. 이미지 전처리 및 합치기dma
        combined = preprocess_and_concat_images(
            sample_images, 
            target_size=384, # (224,224) , (384,384) , (512,512) 
            concat_direction='vertical'
        )
        print(f"합쳐진 이미지 크기: {combined.size}")
        
        # 2. Base64 변환
        base64_string = pil_to_base64(combined)
        print(f"Base64 길이: {len(base64_string)}")
        
        # 3. 파일로 저장
        save_preprocessed_image(
            sample_images,
            "combined_output.jpg",
            target_size=224,
            concat_direction='horizontal'
        )
        
    except FileNotFoundError as e:
        print(f"파일 오류: {e}")
    except Exception as e:
        print(f"처리 중 오류 발생: {e}") 