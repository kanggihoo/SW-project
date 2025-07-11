import base64
import io
from typing import List, Union
from PIL import Image, ImageOps


def preprocess_and_concat_images(
    pil_images: List[Image.Image], 
    target_size: int = 224,
    type: str = "image"
) -> Image.Image:
    """
    여러 이미지를 전처리하고 하나로 이어붙이는 함수
    
    Args:
        pil_images: PIL Image 객체 리스트
        target_size: 각 이미지의 목표 크기 (정사각형) - image type의 경우
                    또는 목표 width 크기 - text type의 경우
        type: 이미지 처리 방식 ("image" 또는 "text")
                - "image": 비율 유지 + 패딩으로 정사각형 만든 후 가로로 합치기
                - "text": width를 target_size에 맞추고 height는 비율 유지, 세로로 합치기
    
    Returns:
        합쳐진 PIL Image 객체
    
    Raises:
        FileNotFoundError: 이미지 파일을 찾을 수 없는 경우
        ValueError: 잘못된 type 값인 경우
    """
    if type not in ['image', 'text']:
        raise ValueError("type은 'image' 또는 'text'여야 합니다.")
    
    processed_images = []
    
    # 각 이미지 전처리
    for pil_image in pil_images:
        try:
            if pil_image.mode != 'RGB':
                image = pil_image.convert('RGB')
            else:
                image = pil_image
            
            if type == "image":
                # 기존 방식: aspect ratio 유지하면서 목표 크기에 맞춰 패딩 추가
                processed = ImageOps.pad(
                    image, 
                    (target_size, target_size), 
                    color=(0, 0, 0)  # 검정색 패딩
                )
            else:  # type == "text"
                # width를 target_size로 고정하고 height는 비율 유지
                width, height = image.size
                aspect_ratio = height / width
                new_height = int(target_size * aspect_ratio)
                processed = image.resize((target_size, new_height), Image.Resampling.LANCZOS)
                
            processed_images.append(processed)
        except Exception as e:
            raise Exception(f"이미지 전처리 중 오류 발생: {e}")
    
    # 이미지 이어붙이기
    if type == "image":
        # 가로로 이어붙이기
        total_width = target_size * len(processed_images)
        combined = Image.new('RGB', (total_width, target_size))
        
        for i, img in enumerate(processed_images):
            combined.paste(img, (i * target_size, 0))
    else:  # type == "text"
        # 세로로 이어붙이기
        total_height = sum(img.size[1] for img in processed_images)
        combined = Image.new('RGB', (target_size, total_height))
        
        current_height = 0
        for img in processed_images:
            combined.paste(img, (0, current_height))
            current_height += img.size[1]
    
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
    pil_images: List[Image.Image],
    target_size: int = 224,
    type: str = "image"
) -> str:
    """
    여러 이미지를 전처리하고 합친 후 base64로 인코딩하는 함수
    
    Args:
        pil_images: PIL Image 객체 리스트
        target_size: 각 이미지의 목표 크기 (정사각형)
        type: 'image' 또는 'text'
    
    Returns:
        base64로 인코딩된 문자열
        
    Raises:
        FileNotFoundError: 이미지 파일을 찾을 수 없는 경우
        ValueError: 잘못된 type 값인 경우
    """
    # 기존 함수를 이용해 이미지들을 전처리하고 합치기
    combined_image = preprocess_and_concat_images(
        pil_images, target_size, type
    )
    
    # PIL 이미지를 base64로 변환
    base64_string = pil_to_base64(combined_image)
    
    return base64_string


