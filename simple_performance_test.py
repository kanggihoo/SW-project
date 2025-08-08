import asyncio
import time
import aiohttp
from typing import List
import os
from dotenv import load_dotenv

# Import embedding functions
from embedding.embedding import JinaEmbedding
from embedding.other_api import get_embedding_with_openai, get_embedding_with_gemini

load_dotenv()

class SimpleEmbeddingTester:
    """간단한 임베딩 성능 테스트 클래스"""
    
    def __init__(self):
        self.test_texts = [
            "Hello, world!",
            "This is a test sentence for embedding performance measurement.",
            "The quick brown fox jumps over the lazy dog.",
            "Artificial intelligence and machine learning are transforming the world.",
            "Natural language processing enables computers to understand human language."
        ]
    
    async def test_jina_speed(self):
        """Jina Embedding 속도 테스트"""
        print("🧪 Testing Jina Embedding Speed...")
        
        jina_embedding = JinaEmbedding()
        total_time = 0
        successful_requests = 0
        
        async with aiohttp.ClientSession() as session:
            for i, text in enumerate(self.test_texts):
                try:
                    start_time = time.time()
                    
                    result = await jina_embedding.get_embedding([text], session)
                    
                    request_time = time.time() - start_time
                    total_time += request_time
                    successful_requests += 1
                    
                    print(f"  ✓ Request {i+1}: {request_time:.3f}s")
                    
                except Exception as e:
                    print(f"  ✗ Request {i+1}: Failed - {str(e)}")
        
        if successful_requests > 0:
            avg_time = total_time / successful_requests
            print(f"📊 Jina Results: {successful_requests}/{len(self.test_texts)} successful")
            print(f"   • Total time: {total_time:.3f}s")
            print(f"   • Average time: {avg_time:.3f}s")
            print(f"   • Requests/sec: {successful_requests/total_time:.2f}")
        else:
            print("❌ All Jina requests failed")
    
    def test_openai_speed(self):
        """OpenAI Embedding 속도 테스트"""
        print("\n🧪 Testing OpenAI Embedding Speed...")
        
        total_time = 0
        successful_requests = 0
        
        for i, text in enumerate(self.test_texts):
            try:
                start_time = time.time()
                
                result = get_embedding_with_openai([text])
                
                request_time = time.time() - start_time
                total_time += request_time
                successful_requests += 1
                
                print(f"  ✓ Request {i+1}: {request_time:.3f}s")
                
            except Exception as e:
                print(f"  ✗ Request {i+1}: Failed - {str(e)}")
        
        if successful_requests > 0:
            avg_time = total_time / successful_requests
            print(f"📊 OpenAI Results: {successful_requests}/{len(self.test_texts)} successful")
            print(f"   • Total time: {total_time:.3f}s")
            print(f"   • Average time: {avg_time:.3f}s")
            print(f"   • Requests/sec: {successful_requests/total_time:.2f}")
        else:
            print("❌ All OpenAI requests failed")
    
    def test_gemini_speed(self):
        """Gemini Embedding 속도 테스트"""
        print("\n🧪 Testing Gemini Embedding Speed...")
        
        total_time = 0
        successful_requests = 0
        
        for i, text in enumerate(self.test_texts):
            try:
                start_time = time.time()
                
                result = get_embedding_with_gemini([text])
                
                request_time = time.time() - start_time
                total_time += request_time
                successful_requests += 1
                
                print(f"  ✓ Request {i+1}: {request_time:.3f}s")
                
            except Exception as e:
                print(f"  ✗ Request {i+1}: Failed - {str(e)}")
        
        if successful_requests > 0:
            avg_time = total_time / successful_requests
            print(f"📊 Gemini Results: {successful_requests}/{len(self.test_texts)} successful")
            print(f"   • Total time: {total_time:.3f}s")
            print(f"   • Average time: {avg_time:.3f}s")
            print(f"   • Requests/sec: {successful_requests/total_time:.2f}")
        else:
            print("❌ All Gemini requests failed")
    
    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 Starting Simple Embedding Speed Test")
        print("=" * 50)
        
        # Jina 테스트
        # await self.test_jina_speed()
        
        # OpenAI 테스트
        try:
            self.test_openai_speed()
        except Exception as e:
            print(f"❌ OpenAI test failed: {e}")
        
        # Gemini 테스트
        try:
            self.test_gemini_speed()
        except Exception as e:
            print(f"❌ Gemini test failed: {e}")
        
        print("\n✅ All tests completed!")

async def main():
    """메인 실행 함수"""
    tester = SimpleEmbeddingTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 