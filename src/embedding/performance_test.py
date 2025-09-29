import asyncio
import time
import statistics
import aiohttp
from typing import List, Dict, Any
import json
from dataclasses import dataclass
from datetime import datetime
import os
from dotenv import load_dotenv

# Import embedding functions
from embedding.embedding import JinaEmbedding
from embedding.other_api import get_embedding_with_openai, get_embedding_with_gemini

load_dotenv()


@dataclass
class PerformanceMetrics:
    """성능 측정 결과를 저장하는 데이터 클래스"""

    api_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    total_tokens: int
    avg_tokens_per_request: float
    errors: List[str]
    timestamp: str


class EmbeddingPerformanceTester:
    """임베딩 API 성능 테스트 클래스"""

    def __init__(self):
        self.test_texts = [
            'Hello, world!',
            'This is a test sentence for embedding performance measurement.',
            'The quick brown fox jumps over the lazy dog.',
            'Artificial intelligence and machine learning are transforming the world.',
            'Natural language processing enables computers to understand human language.',
            'Vector embeddings represent text as numerical vectors in high-dimensional space.',
            'Semantic similarity can be measured using cosine similarity between embeddings.',
            'Deep learning models have revolutionized the field of natural language processing.',
            'Transformer architecture has become the foundation for modern NLP models.',
            'Attention mechanisms allow models to focus on relevant parts of input sequences.',
        ]

        # 다양한 길이의 텍스트로 테스트
        self.long_texts = [
            'This is a much longer text that contains more words and should take longer to process. ' * 10,
            'Another long text with different content and structure. ' * 15,
            'A comprehensive text about machine learning and artificial intelligence. ' * 20,
        ]

        self.results: List[PerformanceMetrics] = []

    async def test_jina_embedding(self, session: aiohttp.ClientSession, texts: List[str], test_name: str = 'Jina Embedding') -> PerformanceMetrics:
        """Jina Embedding API 성능 테스트"""
        print(f'\n🧪 Testing {test_name}...')

        jina_embedding = JinaEmbedding()
        response_times = []
        errors = []
        successful_requests = 0
        total_tokens = 0

        start_time = time.time()

        for i, text in enumerate(texts):
            try:
                request_start = time.time()

                # 단일 텍스트를 리스트로 변환하여 전달
                result = await jina_embedding.get_embedding([text], session)

                request_time = time.time() - request_start
                response_times.append(request_time)
                successful_requests += 1

                # 토큰 수 계산 (대략적인 추정)
                total_tokens += len(text.split())

                print(f'  ✓ Request {i + 1}/{len(texts)}: {request_time:.3f}s')

            except Exception as e:
                errors.append(f'Request {i + 1}: {str(e)}')
                print(f'  ✗ Request {i + 1}/{len(texts)}: Failed - {str(e)}')

        total_time = time.time() - start_time

        return self._calculate_metrics(test_name, len(texts), successful_requests, len(errors), total_time, response_times, total_tokens, errors)

    def test_openai_embedding(self, texts: List[str], test_name: str = 'OpenAI Embedding') -> PerformanceMetrics:
        """OpenAI Embedding API 성능 테스트"""
        print(f'\n🧪 Testing {test_name}...')

        response_times = []
        errors = []
        successful_requests = 0
        total_tokens = 0

        start_time = time.time()

        for i, text in enumerate(texts):
            try:
                request_start = time.time()

                result = get_embedding_with_openai([text])

                request_time = time.time() - request_start
                response_times.append(request_time)
                successful_requests += 1

                # 토큰 수 계산 (대략적인 추정)
                total_tokens += len(text.split())

                print(f'  ✓ Request {i + 1}/{len(texts)}: {request_time:.3f}s')

            except Exception as e:
                errors.append(f'Request {i + 1}: {str(e)}')
                print(f'  ✗ Request {i + 1}/{len(texts)}: Failed - {str(e)}')

        total_time = time.time() - start_time

        return self._calculate_metrics(test_name, len(texts), successful_requests, len(errors), total_time, response_times, total_tokens, errors)

    def test_gemini_embedding(self, texts: List[str], test_name: str = 'Gemini Embedding') -> PerformanceMetrics:
        """Gemini Embedding API 성능 테스트"""
        print(f'\n🧪 Testing {test_name}...')

        response_times = []
        errors = []
        successful_requests = 0
        total_tokens = 0

        start_time = time.time()

        for i, text in enumerate(texts):
            try:
                request_start = time.time()

                result = get_embedding_with_gemini([text])

                request_time = time.time() - request_start
                response_times.append(request_time)
                successful_requests += 1

                # 토큰 수 계산 (대략적인 추정)
                total_tokens += len(text.split())

                print(f'  ✓ Request {i + 1}/{len(texts)}: {request_time:.3f}s')

            except Exception as e:
                errors.append(f'Request {i + 1}: {str(e)}')
                print(f'  ✗ Request {i + 1}/{len(texts)}: Failed - {str(e)}')

        total_time = time.time() - start_time

        return self._calculate_metrics(test_name, len(texts), successful_requests, len(errors), total_time, response_times, total_tokens, errors)

    def _calculate_metrics(
        self,
        api_name: str,
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
        total_time: float,
        response_times: List[float],
        total_tokens: int,
        errors: List[str],
    ) -> PerformanceMetrics:
        """성능 메트릭 계산"""
        if not response_times:
            return PerformanceMetrics(
                api_name=api_name,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                total_time=total_time,
                avg_response_time=0,
                min_response_time=0,
                max_response_time=0,
                median_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                requests_per_second=0,
                total_tokens=total_tokens,
                avg_tokens_per_request=total_tokens / total_requests if total_requests > 0 else 0,
                errors=errors,
                timestamp=datetime.now().isoformat(),
            )

        sorted_times = sorted(response_times)
        n = len(sorted_times)

        return PerformanceMetrics(
            api_name=api_name,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_time=total_time,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            median_response_time=statistics.median(response_times),
            p95_response_time=sorted_times[int(0.95 * n)] if n > 0 else 0,
            p99_response_time=sorted_times[int(0.99 * n)] if n > 0 else 0,
            requests_per_second=successful_requests / total_time if total_time > 0 else 0,
            total_tokens=total_tokens,
            avg_tokens_per_request=total_tokens / successful_requests if successful_requests > 0 else 0,
            errors=errors,
            timestamp=datetime.now().isoformat(),
        )

    def print_metrics(self, metrics: PerformanceMetrics):
        """성능 메트릭 출력"""
        print(f'\n📊 {metrics.api_name} Performance Results:')
        print('=' * 60)
        print(f'📈 Requests: {metrics.successful_requests}/{metrics.total_requests} successful')
        print(f'⏱️  Total Time: {metrics.total_time:.3f}s')
        print(f'🚀 Requests/sec: {metrics.requests_per_second:.2f}')
        print(f'📊 Response Times:')
        print(f'   • Average: {metrics.avg_response_time:.3f}s')
        print(f'   • Median: {metrics.median_response_time:.3f}s')
        print(f'   • Min: {metrics.min_response_time:.3f}s')
        print(f'   • Max: {metrics.max_response_time:.3f}s')
        print(f'   • 95th percentile: {metrics.p95_response_time:.3f}s')
        print(f'   • 99th percentile: {metrics.p99_response_time:.3f}s')
        print(f'📝 Tokens: {metrics.total_tokens} total, {metrics.avg_tokens_per_request:.1f} avg/request')

        if metrics.errors:
            print(f'❌ Errors ({len(metrics.errors)}):')
            for error in metrics.errors[:3]:  # 최대 3개 에러만 표시
                print(f'   • {error}')
            if len(metrics.errors) > 3:
                print(f'   • ... and {len(metrics.errors) - 3} more errors')

    def save_results(self, filename: str = None):
        """결과를 JSON 파일로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'embedding_performance_results_{timestamp}.json'

        results_dict = []
        for metrics in self.results:
            results_dict.append(
                {
                    'api_name': metrics.api_name,
                    'total_requests': metrics.total_requests,
                    'successful_requests': metrics.successful_requests,
                    'failed_requests': metrics.failed_requests,
                    'total_time': metrics.total_time,
                    'avg_response_time': metrics.avg_response_time,
                    'min_response_time': metrics.min_response_time,
                    'max_response_time': metrics.max_response_time,
                    'median_response_time': metrics.median_response_time,
                    'p95_response_time': metrics.p95_response_time,
                    'p99_response_time': metrics.p99_response_time,
                    'requests_per_second': metrics.requests_per_second,
                    'total_tokens': metrics.total_tokens,
                    'avg_tokens_per_request': metrics.avg_tokens_per_request,
                    'errors': metrics.errors,
                    'timestamp': metrics.timestamp,
                }
            )

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)

        print(f'\n💾 Results saved to: {filename}')

    async def run_comprehensive_test(self):
        """종합 성능 테스트 실행"""
        print('🚀 Starting Comprehensive Embedding Performance Test')
        print('=' * 60)

        # 1. 기본 텍스트 테스트
        print('\n📝 Phase 1: Basic Text Test')
        print('-' * 40)

        async with aiohttp.ClientSession() as session:
            # Jina Embedding 테스트
            jina_metrics = await self.test_jina_embedding(session, self.test_texts)
            self.results.append(jina_metrics)
            self.print_metrics(jina_metrics)

        # OpenAI Embedding 테스트
        try:
            openai_metrics = self.test_openai_embedding(self.test_texts)
            self.results.append(openai_metrics)
            self.print_metrics(openai_metrics)
        except Exception as e:
            print(f'❌ OpenAI test failed: {e}')

        # Gemini Embedding 테스트
        try:
            gemini_metrics = self.test_gemini_embedding(self.test_texts)
            self.results.append(gemini_metrics)
            self.print_metrics(gemini_metrics)
        except Exception as e:
            print(f'❌ Gemini test failed: {e}')

        # 2. 긴 텍스트 테스트
        print('\n📝 Phase 2: Long Text Test')
        print('-' * 40)

        async with aiohttp.ClientSession() as session:
            jina_long_metrics = await self.test_jina_embedding(session, self.long_texts, 'Jina Embedding (Long Text)')
            self.results.append(jina_long_metrics)
            self.print_metrics(jina_long_metrics)

        # 3. 결과 저장
        self.save_results()

        # 4. 요약 출력
        self.print_summary()

    def print_summary(self):
        """테스트 결과 요약 출력"""
        print('\n🎯 Performance Test Summary')
        print('=' * 60)

        # 성공률 기준으로 정렬
        sorted_results = sorted(self.results, key=lambda x: x.requests_per_second, reverse=True)

        print(f'{"API":<25} {"RPS":<10} {"Avg Time":<12} {"Success Rate":<15}')
        print('-' * 60)

        for metrics in sorted_results:
            success_rate = (metrics.successful_requests / metrics.total_requests) * 100
            print(f'{metrics.api_name:<25} {metrics.requests_per_second:<10.2f} {metrics.avg_response_time:<12.3f} {success_rate:<15.1f}%')


async def main():
    """메인 실행 함수"""
    tester = EmbeddingPerformanceTester()
    await tester.run_comprehensive_test()


if __name__ == '__main__':
    asyncio.run(main())
