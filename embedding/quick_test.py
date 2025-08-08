import asyncio
import time
import aiohttp
import os
from dotenv import load_dotenv

# Import Jina embedding
from embedding.embedding import JinaEmbedding

load_dotenv()

async def quick_jina_test(dimensions:int=1024):
    """Jina Embedding 빠른 성능 테스트"""
    print("🚀 Quick Jina Embedding Performance Test")
    print("=" * 50)
    
    # 테스트 텍스트들
    test_texts = [
        "Hello, world!",
        "This is a test sentence.",
        "The quick brown fox jumps over the lazy dog.",
        "Artificial intelligence and machine learning.",
        "Natural language processing is amazing."
    ]
    
    jina_embedding = JinaEmbedding(dimensions=dimensions)
    total_time = 0
    successful_requests = 0
    
    print(f"Testing {len(test_texts)} texts...")
    
    async with aiohttp.ClientSession() as session:
        for i, text in enumerate(test_texts):
            try:
                start_time = time.time()
                
                # 임베딩 요청
                result = await jina_embedding.get_embedding([text], session)
                
                request_time = time.time() - start_time
                total_time += request_time
                successful_requests += 1
                
                # 결과 출력
                print(f"  ✓ Text {i+1}: {request_time:.3f}s")
                print(f"    Text: '{text[:30]}{'...' if len(text) > 30 else ''}'")
                print(f"    Embedding dimensions: {len(result['embeddings'][0])}")
                
            except Exception as e:
                print(f"  ✗ Text {i+1}: Failed - {str(e)}")
    
    # 최종 결과 출력
    print("\n📊 Final Results:")
    print("=" * 30)
    print(f"Successful requests: {successful_requests}/{len(test_texts)}")
    print(f"Total time: {total_time:.3f} seconds")
    
    if successful_requests > 0:
        avg_time = total_time / successful_requests
        requests_per_sec = successful_requests / total_time
        print(f"Average time per request: {avg_time:.3f} seconds")
        print(f"Requests per second: {requests_per_sec:.2f}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(quick_jina_test(dimensions=1024)) 