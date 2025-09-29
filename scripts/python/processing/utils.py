import base64
import io
from typing import List, Union
from PIL import Image, ImageOps


from PIL import Image, ImageDraw, ImageOps, ImageFont
from typing import List


def preprocess_and_concat_images(
    pil_images: List[Image.Image],
    target_size: int = 224,
    type: str = 'image',
    border_width: int = 5,
    border_color: str = 'lightgray',
    add_index: bool = True,
    font_size: int = 28,
    font_color: str = 'yellow',
) -> Image.Image:
    """
    여러 이미지를 전처리하고 이어붙이는 함수.
    type="image"이고 add_index=True일 때만 테두리와 인덱스를 추가합니다.
    """
    if type not in ['image', 'text']:
        raise ValueError("type은 'image' 또는 'text'여야 합니다.")

    processed_images = []

    # 폰트는 type="image"이고 add_index=True일 때만 필요하므로 이때 로드합니다.
    font = None
    if type == 'image' and add_index:
        # 사용하시는 폰트 경로를 그대로 사용합니다.
        font_path = '/Users/kkh/Library/Fonts/MesloLGS NF Regular.ttf'
        font = ImageFont.truetype(font_path, font_size)

    for i, pil_image in enumerate(pil_images):
        try:
            image = pil_image.convert('RGB') if pil_image.mode != 'RGB' else pil_image

            if type == 'image':
                # 1. 이미지를 정사각형으로 패딩합니다.
                processed = ImageOps.pad(image, (target_size, target_size), color=(0, 0, 0))

                # 2. add_index가 True일 때만 테두리와 인덱스를 추가합니다.
                if add_index:
                    # 테두리 추가
                    processed = ImageOps.expand(processed, border=border_width, fill=border_color)

                    # 인덱스 텍스트 추가
                    draw = ImageDraw.Draw(processed)
                    index_text = str(i + 1)
                    text_position = (border_width + 5, border_width + 5)
                    draw.text(text_position, index_text, font=font, fill=font_color)

            else:  # type == "text"
                # 테두리나 인덱스 없이, 너비에 맞춰 리사이즈만 수행합니다.
                width, height = image.size
                aspect_ratio = height / width
                new_height = int(target_size * aspect_ratio)
                processed = image.resize((target_size, new_height), Image.Resampling.LANCZOS)

            processed_images.append(processed)
        except Exception as e:
            raise Exception(f'이미지 전처리 중 오류 발생: {e}')

    if not processed_images:
        return None

    # --- 이미지 이어붙이기 ---
    if type == 'image':
        # 첫 번째 이미지의 크기를 기준으로 전체 캔버스 크기를 계산합니다.
        # 이렇게 하면 add_index 여부에 따라 크기가 달라져도 코드가 올바르게 동작합니다.
        img_width, img_height = processed_images[0].size
        total_width = img_width * len(processed_images)
        combined = Image.new('RGB', (total_width, img_height))

        for i, img in enumerate(processed_images):
            combined.paste(img, (i * img_width, 0))
    else:  # type == "text"
        # 텍스트 타입은 너비는 고정, 높이는 가변적입니다.
        img_width = target_size
        total_height = sum(img.size[1] for img in processed_images)
        combined = Image.new('RGB', (img_width, total_height))

        current_height = 0
        for img in processed_images:
            combined.paste(img, (0, current_height))
            current_height += img.size[1]

    return combined


def resize_with_padding_single(image_path: str, target_size: int = 224) -> Image.Image:
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
        color=(0, 0, 0),  # 검정색 패딩
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


def save_preprocessed_image(image_paths: List[str], output_path: str, target_size: int = 224, concat_direction: str = 'horizontal') -> None:
    """
    전처리된 이미지를 파일로 저장하는 함수

    Args:
        image_paths: 이미지 파일 경로 리스트
        output_path: 저장할 파일 경로
        target_size: 각 이미지의 목표 크기
        concat_direction: 'horizontal' 또는 'vertical'
    """
    combined_image = preprocess_and_concat_images(image_paths, target_size, concat_direction)
    combined_image.save(output_path, 'JPEG', quality=95)
    print(f'전처리된 이미지가 저장되었습니다: {output_path}')


def images_to_base64(pil_images: List[Image.Image], target_size: int = 224, type: str = 'image') -> str:
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
    combined_image = preprocess_and_concat_images(pil_images, target_size, type)

    # PIL 이미지를 base64로 변환
    base64_string = pil_to_base64(combined_image)

    return base64_string
