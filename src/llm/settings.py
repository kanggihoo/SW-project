from typing import Annotated, Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .llm_models import AllModelEnum, GoogleModelName, LLMProvider, OpenAIModelName, OpenRouterModelName


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_ignore_empty=True,
        extra='ignore',
    )

    # LLM API keys
    GOOGLE_API_KEY: SecretStr | None = None
    OPENAI_API_KEY: SecretStr | None = None
    OPENROUTER_API_KEY: SecretStr | None = None

    # 기본적으로 사용할 LLM 모델 및 사용 가능한 LLM 모델 집합
    # DEFAULT_LLM_MODEL : AllModelEnum  = OpenRouterModelName.GEMINI_20_FLASH_LITE
    DEFAULT_LLM_MODEL: AllModelEnum = OpenRouterModelName.OPENROUTER_GEMINI_20_FLASH_LITE
    AVAILABLE_LLM_MODELS: Annotated[set[AllModelEnum], '사용 가능한 모든 LLM 모델 집합'] = Field(default_factory=set)

    # Langsmith
    LANGSMITH_TRACING: Annotated[str, 'Langsmith tracing'] = Field(default='true')
    LANGSMITH_PROJECT: Annotated[str, 'Langsmith project'] = Field(default='langgraph-agent-test')
    LANGSMITH_ENDPOINT: str | None = None
    LANGSMITH_API_KEY: SecretStr | None = None

    # ===============================================================================================================
    # 데이터베이스 설정(Connection String 정보 및 Connection Pool 설정)
    # ===============================================================================================================

    # Pydantic 모델이 초기화된 후 실행되는 메서드입니다.
    def model_post_init(self, __context: Any) -> None:
        api_keys = {
            LLMProvider.GOOGLE: self.GOOGLE_API_KEY,
            LLMProvider.OPENAI: self.OPENAI_API_KEY,
            LLMProvider.OPENROUTER: self.OPENROUTER_API_KEY,
        }

        active_api_keys = [k for k, v in api_keys.items() if v]
        if not active_api_keys:
            raise ValueError('No active API keys found')

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
                    raise ValueError(f'Invalid LLM provider: {provider}')


settings = Settings()
