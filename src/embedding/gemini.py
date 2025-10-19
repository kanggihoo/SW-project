import os

from google import genai
from google.genai import types
from loguru import logger


class GeminiEmbedding:
    def __init__(self, model_name: str = 'gemini-embedding-001'):
        self.model_name = model_name
        self.client = self.set_gemini_client()

    def set_gemini_client(self):
        if 'GOOGLE_API_KEY' not in os.environ:
            from dotenv import load_dotenv

            load_dotenv()
            logger.warning('GOOGLE_API_KEY loaded from .env')
        return genai.Client(api_key=os.environ['GOOGLE_API_KEY'])

    async def get_embedding(
        self,
        texts: str | list[str],
        output_dimension: int = 3072,
        task_type: str = 'RETRIEVAL_DOCUMENT',
    ) -> list[float]:
        """Gemini Embedding 모델을 사용하여 텍스트를 임베딩하는 함수

        Args:
            texts (str | list[str]): 임베딩 할 텍스트 리스트 또는 문자열
            output_dimension (int, optional): 임베딩 차원. Defaults to 3072. (3072 , 1536 , 768)
            task_type (str, optional): 임베딩 작업 유형. Defaults to "RETRIEVAL_DOCUMENT". ,
        Returns:
            list[float]: _description_
        """

        result = await self.client.aio.models.embed_content(
            model=self.model_name,
            contents=texts,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=output_dimension),
        )
        return [emb.values for emb in result.embeddings]


gemini_embedding = GeminiEmbedding()


# API 키 설정 (환경 변수에 설정하는 것을 권장)
# genai.configure(api_key="YOUR_API_KEY")


# async def main():
#     # embedding = await gemini_embedding.get_embedding(texts=['Hello, world!'], output_dimension=768)
#     # # normalized_embedding = normalize_vector(embedding[0])
#     # # print(norm(normalized_embedding))
#     # # print(norm(embedding[0]))
#     # print(len(embedding[0]), len(embedding))


# # 비동기 함수 실행
# if __name__ == '__main__':
#     asyncio.run(main())
