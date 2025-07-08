from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ImageManager:
    folder_path: str
    type: str
    s3_key:str = field(default="")
    s3_url: str|None = None
    
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