# ruff: noqa: E501
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from llm import ModelT, get_llm_model

from .models import BottomFilter, SingleCallAnalysisResult, TopFilter
from .prompt import SYSTEMPROMPT


class SingleStepAnalyzer:
    """Analyzes a fashion query in a single LLM call."""

    def __init__(self, model_name: ModelT, max_tokens: int = 2000):
        self.llm = get_llm_model(model_name, max_tokens)
        self.chain = self._create_chain()

    def _create_chain(self):
        system_prompt = SYSTEMPROMPT
        prompt = ChatPromptTemplate.from_messages([SystemMessage(content=system_prompt), ('human', '분석할 사용자 쿼리: {query}')])

        return (prompt | self.llm.with_structured_output(SingleCallAnalysisResult)).with_config({'tags': ['skip_stream']})

    async def analyze(self, query: str) -> SingleCallAnalysisResult:
        """Analyzes the user query asynchronously and returns the structured result."""
        return await self.chain.ainvoke({'query': query})

    async def analyze_and_format(self, query: str) -> list[dict]:
        """
        Analyzes the user query asynchronously and formats the result to return a list of dictionaries,
        each containing the item_type and the analysis details.
        example:
        ```
        [
            {
                "main_category": "상의",
                "sub_category": "셔츠",
                "color": "블랙",
                "style_tags": ["베이직"],
                "tpo_tags": ["데일리"],
                "fit": "슬림 핏",
                "pattern_type": "무지/솔리드",
                "rewritten_query": "블랙 베이직 셔츠 구매"
            },
            ...
        """
        analysis_result = await self.analyze(query)

        if not analysis_result or not analysis_result.analyzed_items:
            return []

        formatted_result = []
        for item in analysis_result.analyzed_items:
            item_type = None
            # isinstance() is a reliable way to check the type of the Pydantic model instance
            if isinstance(item, TopFilter):
                item_type = '상의'
            elif isinstance(item, BottomFilter):
                item_type = '하의'

            analysis_data = item.model_dump(mode='json')

            formatted_result.append({'main_category': item_type, **analysis_data})

        return formatted_result
