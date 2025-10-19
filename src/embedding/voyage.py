import asyncio
import time

import httpx
import voyageai

api_key = 'pa-9IGLFFer3tVs5AXhBtBMibuEjOkpOGfMINGK6RIr_NM'
vo = voyageai.AsyncClient(api_key=api_key)
httpx_client = httpx.AsyncClient()

test_input = ['hello world123', 'hello world 2123']


async def get_embedding():
    start_time = time.perf_counter()
    url = 'https://api.voyageai.com/v1/embeddings'
    payload = {
        'model': 'voyage-3.5-lite',
        'input': test_input,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    try:
        async with httpx_client as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
            print(
                {
                    'object': result.get('object'),
                    'data': [len(data.get('embedding')) for data in result.get('data')],
                    'usage': result.get('usage'),
                }
            )
            end_time = time.perf_counter()
            print(f'Time taken: {end_time - start_time} seconds')
    except httpx.HTTPStatusError as e:
        print(f'Error: {e}')
        return None


async def get_embedding_with_voyage():
    start_time = time.perf_counter()
    result = await vo.embed(test_input, model='voyage-3.5-lite')
    print(result)
    end_time = time.perf_counter()
    print(f'Time taken: {end_time - start_time} seconds')


async def main():
    await get_embedding()
    await get_embedding_with_voyage()


async def rerank():
    start_time = time.perf_counter()
    query = '최신 AI 모델인 Gemini의 주요 특징은 무엇인가요?'

    documents = [
        # 긍정 문서 (Positive Document) 예시 - 관련성 높음
        'Gemini는 Google DeepMind가 개발한 최신 대규모 멀티모달 AI 모델입니다. 텍스트, 이미지, 오디오, 비디오 등 다양한 형태의 정보를 이해하고 결합하여 처리할 수 있습니다.',
        # 부정 문서 (Negative Document) 예시 1 - 관련성 낮음 (일반적인 AI 개념)
        '인공지능(AI)은 컴퓨터 시스템이 인간의 지능을 모방하여 학습, 문제 해결, 의사 결정을 수행할 수 있도록 하는 기술입니다. 머신러닝, 딥러닝 등의 하위 분야가 있습니다.',
        # 부정 문서 (Negative Document) 예시 2 - 관련성 낮음 (다른 AI 모델 언급)
        'GPT-4는 OpenAI에서 개발한 강력한 언어 모델로, 대규모 데이터를 학습하여 높은 수준의 자연어 이해 및 생성 능력을 보여줍니다.',
        # 긍정 문서 (Positive Document) 예시 - 관련성 높음
        'Gemini는 Ultra, Pro, Nano 세 가지 버전으로 출시되었으며, 특히 Ultra는 복잡한 추론과 태스크 처리에 최적화되어 있습니다.',
        # 부정 문서 (Negative Document) 예시 3 - 관련성 낮음 (무관한 주제)
        '파이썬은 웹 개발, 데이터 분석 등 다양한 분야에 사용되는 인기 있는 프로그래밍 언어입니다. 간결한 문법이 특징입니다.',
    ]

    reranking = await vo.rerank(query, documents, model='rerank-2.5', top_k=3)
    for r in reranking.results:
        print(f'Document: {r.document}')
        print(f'Relevance Score: {r.relevance_score}')
        print()
    end_time = time.perf_counter()
    print(f'Time taken: {end_time - start_time} seconds')


if __name__ == '__main__':
    asyncio.run(main())
