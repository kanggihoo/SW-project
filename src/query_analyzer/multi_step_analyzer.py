# ruff: noqa: E501
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel

from llm import ModelT, get_llm_model

from .models import BottomFilter, InitialAnalysis, MainCategory, TopFilter
from .prompt import SYSTEMPROMPT1, SYSTEMPROMPT2


class MultiStepAnalyzer:
    """Analyzes a fashion query in two steps: identification and then detailed analysis."""

    def __init__(self, model_name1: ModelT, model_name2: ModelT, max_tokens: int = 2000):
        # Can use different models for different steps if needed

        self.llm1 = get_llm_model(model_name1, max_tokens)
        self.llm2 = get_llm_model(model_name2, max_tokens)

    def _get_first_chain(self):
        """Step 1: Identify items and common context from the query."""
        system_prompt = SYSTEMPROMPT1
        prompt = ChatPromptTemplate.from_messages([SystemMessage(content=system_prompt), ('human', '쿼리: {query}')])
        return prompt | self.llm1.with_structured_output(InitialAnalysis)

    def _get_second_chain(self, item_type: MainCategory):
        """Step 2: Analyze a single identified item."""
        output_pydantic_model = TopFilter if item_type == MainCategory.TOP else BottomFilter

        system_prompt_template = SYSTEMPROMPT2.format(item_type=item_type.value)
        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=system_prompt_template), ('human', '공통 문맥: {common_context}\n분석할 쿼리: {raw_query}')]
        )
        return (prompt | self.llm2.with_structured_output(output_pydantic_model)).with_config({'tags': ['skip_stream']})

    def _create_full_chain(self):
        first_chain = self._get_first_chain()
        top_analyzer = self._get_second_chain(MainCategory.TOP)
        bottom_analyzer = self._get_second_chain(MainCategory.BOTTOM)

        def dynamic_router(initial_data: InitialAnalysis):
            branches = {}
            for idx, item in enumerate(initial_data.items):
                analyzer = top_analyzer if item.item_type == MainCategory.TOP else bottom_analyzer

                selector = RunnableLambda(
                    lambda data, current_item=item: {'common_context': data.common_context, 'raw_query': current_item.raw_query},
                    name=f'SelectItem_{idx}',
                )
                key = f'{item.item_type.value}_{idx}'
                branches[key] = selector | analyzer

            if not branches:
                return RunnableLambda(lambda x: {{}})

            return RunnableParallel(**branches)

        main_chain = first_chain | RunnableLambda(dynamic_router, name='DynamicRouter')
        return main_chain

    async def analyze(self, query: str) -> dict:
        """
        Analyzes the user query asynchronously and returns a dictionary of structured results,
        with each key corresponding to an identified item.
        """
        chain = self._create_full_chain()
        return await chain.ainvoke({'query': query})

    async def analyze_and_format(self, query: str) -> list[dict]:
        """
        Analyzes the user query asynchronously and formats the result to return a list of dictionaries.

        Args:
            query (str): The user query string.

        Returns:
            A list of dictionaries with the analysis results.
        example:
        ```
        [
            {
                'main_category': '상의',
                'sub_category': '셔츠',
                'color': '블랙',
                'style_tags': '베이직',
                'tpo_tags': '데일리',
                'fit': '슬림 핏',
                'pattern_type': '무지/솔리드',
                'rewritten_query': '블랙 베이직 셔츠 구매',
            },
            ...,
        ]
        ```
        """
        analysis_result = await self.analyze(query)

        formatted_result = []
        for key, value in analysis_result.items():
            if not value:
                continue
            item_type = key.split('_')[0]
            analysis_result = value.model_dump(mode='json') if hasattr(value, 'model_dump') else value

            formatted_item = {'main_category': item_type, **analysis_result}
            formatted_result.append(formatted_item)

        return formatted_result
