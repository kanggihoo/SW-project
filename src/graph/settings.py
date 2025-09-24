from pydantic_settings import BaseSettings , SettingsConfigDict
from pydantic import (
    Field ,
    SecretStr,
    computed_field
)
from typing import Annotated , Any
from enum import StrEnum

from graph.model.llm_models import (
    AllModelEnum , 
    GoogleModelName , 
    OpenAIModelName , 
    OpenRouterModelName,
    LLMProvider
)


class DatabaseType(StrEnum):
    """Database type"""
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MONGO = "mongo"

class EnvType(StrEnum):
    """Environment type"""
    LOCAL = "local"
    CLOUD = "cloud"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        )

    # HOST : Annotated[str, "Fastapi Server host"] = Field(default="0.0.0.0")
    # PORT : Annotated[int, "Fastapi Server port"] = Field(default=8000)
    # AGENT_ENDPOINT : Annotated[str, "Fastapi Server agent endpoint"] = Field(default="/langgraph")

    # LLM API keys 
    GOOGLE_API_KEY : SecretStr | None = None
    OPENAI_API_KEY : SecretStr | None = None
    OPENROUTER_API_KEY : SecretStr | None = None
    
    #기본적으로 사용할 LLM 모델 및 사용 가능한 LLM 모델 집합
    # DEFAULT_LLM_MODEL : AllModelEnum  = OpenRouterModelName.GEMINI_20_FLASH_LITE    
    DEFAULT_LLM_MODEL : AllModelEnum  = OpenRouterModelName.OPENROUTER_GEMINI_20_FLASH_LITE   
    AVAILABLE_LLM_MODELS : Annotated[set[AllModelEnum], "사용 가능한 모든 LLM 모델 집합"] = Field(default_factory=set)

    # Langsmith 
    LANGSMITH_TRACING : Annotated[str, "Langsmith tracing"] = Field(default="False")
    LANGSMITH_PROJECT : Annotated[str, "Langsmith project"] = Field(default="langgraph-agent-test")
    LANGSMITH_ENDPOINT : str | None = None
    LANGSMITH_API_KEY : SecretStr | None = None


    #===============================================================================================================
    # 데이터베이스 설정(Connection String 정보 및 Connection Pool 설정)
    #===============================================================================================================
    DATABASE_TYPE: DatabaseType = DatabaseType.POSTGRES

    DB_ENV : Annotated[EnvType, "Environment type"] = EnvType.LOCAL

    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: SecretStr | None = None
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int | None = None
    POSTGRES_DB: str | None = None

    LOCAL_POSTGRES_USER: str | None = None
    LOCAL_POSTGRES_PASSWORD: SecretStr | None = None
    LOCAL_POSTGRES_HOST: str | None = None
    LOCAL_POSTGRES_PORT: int | None = None
    LOCAL_POSTGRES_DB: str | None = None

    POSTGRES_APPLICATION_NAME: str = "langgraph-agent-test"
    POSTGRES_MIN_CONNECTIONS_PER_POOL: int = 1
    POSTGRES_MAX_CONNECTIONS_PER_POOL: int = 10

    # Pydantic 모델이 초기화된 후 실행되는 메서드입니다.
    def model_post_init(self, __context: Any) -> None:
       api_keys = {
           LLMProvider.GOOGLE : self.GOOGLE_API_KEY,
           LLMProvider.OPENAI : self.OPENAI_API_KEY,
           LLMProvider.OPENROUTER : self.OPENROUTER_API_KEY,
       }
       
       active_api_keys = [k for k , v in api_keys.items() if v]
       if not active_api_keys:
           raise ValueError("No active API keys found")
       
       for provider in active_api_keys:
           match provider:
               case LLMProvider.OPENAI:
                #    self.DEFAULT_LLM_MODEL = OpenAIModelName.GPT_4O_MINI
                   self.AVAILABLE_LLM_MODELS.update(set(OpenAIModelName))
               case LLMProvider.OPENROUTER:
                #    self.DEFAULT_LLM_MODEL = OpenRouterModelName.GPT_4O_MINI
                   self.AVAILABLE_LLM_MODELS.update(set(OpenRouterModelName))
               case LLMProvider.GOOGLE:
                #    self.DEFAULT_LLM_MODEL = GoogleModelName.GEMINI_20_FLASH_LITE
                   self.AVAILABLE_LLM_MODELS.update(set(GoogleModelName))
               case _:
                   raise ValueError(f"Invalid LLM provider: {provider}")
               

    def is_local(self) -> bool:
        """Check if the server is in local environment"""
        return self.DB_ENV == EnvType.LOCAL
    
    

    

settings = Settings()
    



