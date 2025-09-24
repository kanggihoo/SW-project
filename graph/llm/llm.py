from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypeAlias

from graph.settings import settings
from graph.model.llm_models import (
    AllModelEnum,
    GoogleModelName,
    OpenAIModelName,
    OpenRouterModelName
)
from functools import cache 

ModelT : TypeAlias = (
    GoogleModelName
    | OpenAIModelName
    | OpenRouterModelName
)

# 딕셔너리 병합 연산자 | (Python 3.9 이상)
_MODEL_TABLE = (
    {m:m.value for m in GoogleModelName}
    | {m:m.value for m in OpenAIModelName}
    | {m:m.value for m in OpenRouterModelName}
)


@cache
def get_llm_model(model_name : AllModelEnum) -> ModelT:
    model_name_str = _MODEL_TABLE[model_name]
    if not model_name_str :
        raise ValueError(f"Invalid model name: {model_name}")
    
    if model_name_str in GoogleModelName:
        return ChatGoogleGenerativeAI(
            model=model_name_str,
            temperature=0.0,
        
        )
    elif model_name_str in OpenAIModelName:
        return ChatOpenAI(
            model=model_name_str,
            temperature=0.0,
            streaming=True,
        )
    elif model_name_str in OpenRouterModelName:
        print("model_name_str: " , model_name_str)
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY.get_secret_value(),
            model=model_name_str,
            base_url="https://openrouter.ai/api/v1/",
            temperature=0.0,
            streaming=True,
        )
    
    raise ValueError(f"Invalid model name: {model_name}")

