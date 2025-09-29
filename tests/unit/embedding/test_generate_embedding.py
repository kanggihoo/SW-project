import pytest
import time
import numpy as np
import httpx
import asyncio
from embedding.embedding import JinaEmbedding
from embedding.other_api import GeminiEmbedding
from dotenv import load_dotenv
from embedding.utils import normalize_vector
from numpy.linalg import norm

load_dotenv()

# 테스트에 사용할 텍스트 데이터
TEXT_DATA = ['Hello, world!', 'This is a test.', 'Pytest is awesome.']
ITERATIONS = 5  # 반복 횟수


@pytest.mark.asyncio
async def test_jina_embedding_performance():
    """JinaEmbedding 클래스의 임베딩 생성 시간 측정"""
    times = []
    async with httpx.AsyncClient() as session:
        jina_embedding = JinaEmbedding(session=session)
        # 초기화를 위한 첫 호출 (실제 측정에서 제외)
        await jina_embedding.get_embedding(TEXT_DATA[0])

        for _ in range(ITERATIONS):
            start_time = time.time()
            await jina_embedding.get_embedding(TEXT_DATA)
            end_time = time.time()
            times.append(end_time - start_time)
            await asyncio.sleep(0.1)  # API rate limit 방지를 위한 짧은 대기

    min_time = np.min(times)
    max_time = np.max(times)
    avg_time = np.mean(times)

    print('\n--- Jina Embedding Performance ---')
    print(f'Iterations: {ITERATIONS}')
    print(f'Min time: {min_time:.4f} seconds')
    print(f'Max time: {max_time:.4f} seconds')
    print(f'Avg time: {avg_time:.4f} seconds')
    print('------------------------------------')

    assert avg_time > 0


@pytest.mark.asyncio
async def test_gemini_embedding_performance():
    """GeminiEmbedding 클래스의 임베딩 생성 시간 측정"""
    times = []
    gemini_embedding = GeminiEmbedding()
    # 초기화를 위한 첫 호출 (실제 측정에서 제외)
    await gemini_embedding.get_embedding(TEXT_DATA[0])
    output_dimension = 768

    for _ in range(ITERATIONS):
        start_time = time.time()
        await gemini_embedding.get_embedding(TEXT_DATA, output_dimension=768)
        end_time = time.time()
        times.append(end_time - start_time)
        await asyncio.sleep(0.1)  # API rate limit 방지를 위한 짧은 대기

    min_time = np.min(times)
    max_time = np.max(times)
    avg_time = np.mean(times)

    print('\n--- Gemini Embedding Performance ---')
    print(f'Iterations: {ITERATIONS}')
    print(f'Min time: {min_time:.4f} seconds')
    print(f'Max time: {max_time:.4f} seconds')
    print(f'Avg time: {avg_time:.4f} seconds')
    print('--------------------------------------')

    assert avg_time > 0


@pytest.mark.asyncio
async def test_gemini_embedding():
    """GeminiEmbedding 클래스의 임베딩 생성 테스트"""
    gemini_embedding = GeminiEmbedding()
    embedding = await gemini_embedding.get_embedding(TEXT_DATA[0], output_dimension=768)
    normalized_embedding = normalize_vector(embedding)
    print(len(normalized_embedding), normalized_embedding.shape)
    for emb in normalized_embedding:
        print(norm(emb))
