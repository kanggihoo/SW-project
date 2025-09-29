from functools import cache

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .llm_models import GoogleModelName, OpenAIModelName, OpenRouterModelName
from .settings import settings

type ModelT = GoogleModelName | OpenAIModelName | OpenRouterModelName

# 딕셔너리 병합 연산자 | (Python 3.9 이상)
_MODEL_TABLE = {m: m.value for m in GoogleModelName} | {m: m.value for m in OpenAIModelName} | {m: m.value for m in OpenRouterModelName}


@cache
def get_llm_model(model_name: ModelT, max_tokens: int | None = None) -> BaseChatModel:
    model_name_str = _MODEL_TABLE[model_name]
    if not model_name_str:
        raise ValueError(f'Invalid model name: {model_name}')
    kwargs = {
        'temperature': 0.0,
        'streaming': True,
        'max_tokens': max_tokens,
        'model': model_name_str,
    }
    if max_tokens:
        kwargs['max_tokens'] = max_tokens
    if model_name in OpenRouterModelName:
        kwargs['api_key'] = settings.OPENROUTER_API_KEY.get_secret_value()
        kwargs['base_url'] = 'https://openrouter.ai/api/v1/'

    if model_name_str in GoogleModelName:
        return ChatGoogleGenerativeAI(**kwargs)
    elif model_name_str in OpenAIModelName or model_name_str in OpenRouterModelName:
        return ChatOpenAI(**kwargs)

    raise ValueError(f'Invalid model name: {model_name}')
