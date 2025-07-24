# 설정관리 
from functools import lru_cache
from pydantic_settings import BaseSettings , SettingsConfigDict
from pydantic import Field
from typing import Annotated

class Settings(BaseSettings):
    USE_ATLAS : Annotated[bool , Field(default=True)]
    MONGODB_ATLAS_URI: Annotated[str , Field(... , json_schema_extra={"env": "MONGODB_ATLAS_URI"})]
    MONGODB_ATLAS_DATABASE: Annotated[str , Field(default="fashion_db")]
    MONGODB_ATLAS_COLLECTION: Annotated[str , Field(default="products")]


    

    model_config = SettingsConfigDict(_env_file=".env")


@lru_cache
def get_settings():
    return Settings()