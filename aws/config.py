from pathlib import Path

DEFAULT_CACHE_DIR = Path.home() / ".cache" /  "ai_dataset_curation" / "product_images"




def get_default_pagenator_config() -> dict:
    return {"MaxItems": 100, "PageSize": 4}

class Config(dict):
    def __init__(self):
        _dynamodb_dict = {
            "DEFAULT_PROJECTION_FIELDS": ("sub_category", "product_id", "main_category", "representative_assets" , "text"),
            "DEFAULT_PAGINATOR_CONFIG": get_default_pagenator_config(),
        }
        
        _common_dict = {
            "DEFAULT_CACHE_DIR":DEFAULT_CACHE_DIR.as_posix()
        }
        
        super().__init__()
        self.update(_dynamodb_dict)
        self.update(_common_dict)

        

