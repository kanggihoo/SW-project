# src/graph/summarizer/review_summarizer.py

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.constants import SKIP_STREAM
from llm import ModelT, get_llm_model

# --- 1. 리뷰 요약에 사용할 프롬프트를 정의합니다. ---
# (프롬프트 내용은 아래 2번 항목에서 자세히 설명)
SUMMARY_PROMPT_TEMPLATE = """
당신은 쇼핑몰 상품의 리뷰 요약 전문가입니다.
아래에 제공되는 리뷰 목록을 분석하여, 다른 구매자들이 궁금해할 만한 핵심적인 내용들을 간결하게 요약해주세요.

**요약 규칙:**
1.  **긍정적인 피드백**과 **부정적인 피드백**을 명확히 구분하여 각각 한두 문장으로 요약합니다.
2.  사이즈, 핏, 색상, 소재, 품질 등 구체적인 항목에 대한 언급을 최대한 포함해주세요.
3.  객관적인 사실 위주로 작성하고, 당신의 주관적인 의견은 절대 추가하지 마세요.
4.  최종 결과는 "전반적으로... 하지만..." 과 같은 자연스러운 문장 형태로 완성해주세요.

**리뷰 목록:**
---
{review_texts}
---

**요약 결과:**
"""


class ReviewSummarizer:
    """리뷰 목록을 받아 LLM을 통해 요약문을 생성하는 클래스"""

    def __init__(self, model_str: ModelT = None):
        # 요약에 특화된, 빠르고 저렴한 모델을 사용하는 것이 좋습니다.
        if model_str is None:
            model_str = 'google/gemini-2.5-flash'
        try:
            self.llm = get_llm_model(model_str)
        except ValueError as e:
            raise ValueError(f'Invalid model name: {model_str}') from e

        self.chain = (ChatPromptTemplate.from_template(SUMMARY_PROMPT_TEMPLATE) | self.llm | StrOutputParser()).with_config(tags=[SKIP_STREAM])

    async def summarize(self, reviews: list[dict]) -> str:
        """리뷰 목록을 받아 요약문을 비동기적으로 생성합니다."""
        if not reviews:
            return '요약할 리뷰가 없습니다.'

        # LLM에 전달할 리뷰 텍스트를 하나의 문자열로 합칩니다.
        # 각 리뷰는 작성자 정보, 평점, 내용 등을 포함하여 컨텍스트를 풍부하게 합니다.
        review_texts_for_prompt = []
        for review in reviews:
            # 예시: "평점: 5/5, 작성자: 175cm/70kg - 내용: 핏이 아주 좋습니다. 추천합니다."
            author_spec = review.get('author', '정보 없음')
            rating = review.get('rating', '평점 없음')
            content = review.get('content', '')
            review_texts_for_prompt.append(f'평점: {rating}/5, 작성자: {author_spec} - 내용: {content}')

        # 프롬프트에 삽입할 최종 텍스트
        formatted_review_texts = '\\n'.join(review_texts_for_prompt)

        # 구성된 체인을 실행하여 요약 결과를 얻습니다.
        summary = await self.chain.ainvoke({'review_texts': formatted_review_texts})

        return summary.strip()
