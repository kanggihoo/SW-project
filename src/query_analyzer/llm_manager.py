import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

class LLMManager:
    def __init__(self):
        self._load_env()

    def load_llm(self, model_provider: str, model_name: str, max_tokens: int = 2000):
        provider = model_provider.lower()
        if provider == "gemini":
            return ChatGoogleGenerativeAI(model=model_name, temperature=0, max_output_tokens=max_tokens)
        elif provider == "openai":
            return ChatOpenAI(model=model_name, temperature=0, max_tokens=max_tokens)
        elif provider == "friendli":
            # Friendli uses a specific model name, so we might ignore self.model_name
            model_name = "LGAI-EXAONE/EXAONE-4.0.1-32B"
            return ChatOpenAI(
                api_key=os.getenv("FRIENDLI_TOKEN"),
                base_url="https://api.friendli.ai/serverless/v1",
                model=model_name,
                temperature=0,
                max_tokens=max_tokens
            )
        elif provider == "openrouter":
            return ChatOpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url=os.getenv("OPENROUTER_BASE_URL"),
                model=model_name,
                temperature=0,
                max_tokens=max_tokens
            )
        else:
            raise ValueError(f"Invalid model provider: {model_provider}")
    
    def _load_env(self):
        import os
        if not os.getenv("GOOGLE_API_KEY") and not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
            load_dotenv()
    

