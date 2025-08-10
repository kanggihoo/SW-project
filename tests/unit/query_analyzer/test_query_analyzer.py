"""
Query Analyzer 사용 예시
"""
import json
from query_analyzer.single_step_analyzer import SingleStepAnalyzer
from query_analyzer.multi_step_analyzer import MultiStepAnalyzer
import pytest

@pytest.fixture(scope="session")
def single_step_analyzer():
    analyzer = SingleStepAnalyzer("openrouter" , "google/gemini-flash-1.5")
    return analyzer

@pytest.fixture(scope="session")
def multi_step_analyzer():
    analyzer = MultiStepAnalyzer("openrouter", "google/gemini-flash-1.5" , "openrouter" , "google/gemini-flash-1.5")
    return analyzer

@pytest.mark.asyncio
async def test_single_step(single_step_analyzer :SingleStepAnalyzer):
    """단일 단계 분석기 테스트"""
    print("=== 단일 단계 분석기 테스트 ===")
    
    # 테스트 쿼리
    query = """블루 베이직 버튼다운 반팔 셔츠랑 베이지 와이드 슬랙스가 잘 어울려. 
깔끔하면서도 시원한 느낌이 나서 소개팅하기 딱이야. 
베이지 로퍼를 매치하면 정장 느낌은 나지만 여름 분위기도 살릴 수 있어."""
    
    try:
        # 분석 실행
        result = await single_step_analyzer.analyze_and_format(query)
        print("분석 결과:")
        print(result , type(result))
    except Exception as e:
        print(f"분석 중 오류 발생: {e}")

@pytest.mark.asyncio
async def test_multi_step(multi_step_analyzer:MultiStepAnalyzer):
    """다중 단계 분석기 테스트"""
    print("\n=== 다중 단계 분석기 테스트 ===")    
    # 테스트 쿼리
    query = "출근룩으로 입을 화이트 셔츠와 네이비 슬랙스를 찾고 있어"
    
    try:
        # 분석 실행
        result = await multi_step_analyzer.analyze_and_format(query)
        print("분석 결과:")
        print(result , type(result))
    except Exception as e:
        print(f"분석 중 오류 발생: {e}")


