from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image
from pydantic import BaseModel , Field
from typing import Annotated

@dataclass
class ImageManager:
    folder_path: str
    type: str
    s3_key:str = field(default="")
    s3_url: str|None = None
    pil_image: Image.Image|None = None
    
    
@dataclass
class ProductManager:
    main_category: str
    product_id: str
    sub_category: int
    images: list[ImageManager] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        self.product_dir = Path(self.main_category) / str(self.sub_category) / self.product_id
        for image in self.images:
            image.s3_key = (self.product_dir / image.folder_path).as_posix()

class Base64DataForLLM(BaseModel):
    """
    LLM 입력에 맞는 데이터 모델
    
    Args:
        deep_caption (str): 딥캡션 이미지
        color_images (str): 색상 이미지
        text_images (str): 텍스트 이미지
        success (bool): 이미지 변환 성공 여부
        fail (int): pil image를 base64로 변환할때 실패한 이미지 개수
        color_count (int): 해당 제품의 색상 이미지 개수
    """
    deep_caption: str
    color_images: str
    text_images: Annotated[str, Field(default="")]
    success: Annotated[bool, Field(default=False , description="이미지 변환 성공 여부")]
    fail: Annotated[int, Field(default=0 , description="pil image를 base64로 변환할때 실패한 이미지 개수")]
    color_count: Annotated[int, Field(default=0 , description="해당 제품의 색상 이미지 개수")]