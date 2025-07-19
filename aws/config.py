from pathlib import Path
from typing import Dict, Any
def get_default_pagenator_config() -> dict:
    return {"MaxItems": 100, "PageSize": 4}

class Config():
    def __init__(self):
        self._config = self._load_config()

    def _load_config(self):
        DEFAULT_CACHE_DIR = Path.home() / ".cache" /  "ai_dataset_curation" / "product_images"
        REGION_NAME = "ap-northeast-2"
        return {
            "aws": {
                "region_name": REGION_NAME
            },
            "s3": {
                "region_name": REGION_NAME,
                "bucket_name": "sw-fashion-image-data"
            },
            "dynamodb": {
                "region_name": REGION_NAME,
                "table_name": "ProductAssets",
                "DEFAULT_PROJECTION_FIELDS": ("sub_category", "product_id", "main_category", "representative_assets" , "text"),
                "DEFAULT_PAGINATOR_CONFIG": get_default_pagenator_config(),
                "DEFAULT_CACHE_DIR":DEFAULT_CACHE_DIR.as_posix()
            },
            "cache": {
                "DEFAULT_CACHE_DIR":DEFAULT_CACHE_DIR.as_posix()
            }
        }

    def get_aws_config(self) -> Dict[str, Any]:
        return self._config["aws"]
    
    def get_s3_config(self) -> Dict[str, Any]:
        return self._config["s3"]
    
    def get_dynamodb_config(self) -> Dict[str, Any]:
        return self._config["dynamodb"]
    
    def get_cache_config(self) -> Dict[str, Any]:
        return self._config["cache"]





