from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableLambda, RunnableParallel
from .models import (
    InitialAnalysis, TopFilter, BottomFilter, MainCategory
)
from .llm_manager import LLMManager
import json

class MultiStepAnalyzer:
    """Analyzes a fashion query in two steps: identification and then detailed analysis."""

    def __init__(self, model_provider1: str, model_name1: str, model_provider2: str, model_name2: str):
        # Can use different models for different steps if needed
        llm_manager = LLMManager()
        self.llm1 = llm_manager.load_llm(model_provider1, model_name1)
        self.llm2 = llm_manager.load_llm(model_provider2, model_name2)

    def _get_first_chain(self):
        """Step 1: Identify items and common context from the query."""
        system_prompt = """
        당신은 사용자의 패션 쿼리를 분석하고 상의와 하의에 대한 정보를 명확히 분리하는 AI 어시스턴트입니다.
        ## 작업 지침
        1. **아이템 식별**: 사용자 쿼리에서 '상의' 또는 '하의'와 관련된 모든 내용을 찾아 식별합니다.
        2. **정보 추출**: 각 아이템에 대해 사용자가 언급한 모든 관련 정보(색상, 스타일, 핏, 패턴, 기장, TPO 등)를 추출하여 `raw_query` 필드에 저장합니다.
        3. **공통 정보 처리**: 사용자 쿼리에서 여러 아이템에 공통으로 적용되는 정보(예: 특정 상황, TPO)가 있다면, 해당 정보를 분리된 모든 아이템의 `raw_query`에 반드시 포함시켜야 합니다.
        4. **분리 및 구성**:
            - 쿼리에 상의와 하의 정보가 모두 포함되어 있다면, 각각을 별도의 `IdentifiedItem`으로 분리하여 리스트에 추가합니다.
            - **중요**: 상의와 하의 정보가 명확히 분리되지 않거나, 둘 중 어느 쪽인지 판단하기 모호한 경우, 가장 가능성이 높은 쪽으로 판단하되 `raw_query`에는 판단의 근거가 된 모든 정보를 포함해야 합니다.
        5. **공통 문맥 추출**: 여러 아이템에 공통으로 적용되는 정보(예: '주말 데이트', '여행가서 입을')가 있다면, 이를 `common_context` 필드에 별도로 추출하여 저장합니다.
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            ("human", "쿼리: {query}")
        ])
        return prompt | self.llm1.with_structured_output(InitialAnalysis)

    def _get_second_chain(self, item_type: MainCategory):
        """Step 2: Analyze a single identified item."""
        output_pydantic_model = TopFilter if item_type == MainCategory.TOP else BottomFilter
        
        system_prompt_template = f"""
        당신은 {item_type.value}에 대한 쿼리를 분석하여 지정된 Pydantic 모델에 맞춰 필터 정보를 추출하고, 검색에 최적화된 쿼리를 재작성하는 전문 AI 어시스턴트입니다.
        ## 작업 지침
        1. **입력 분석**: 사용자의 `{item_type.value}`에 대한 쿼리를 철저히 분석합니다.
        2. **필터 매칭**: 쿼리내에 {item_type.value} 에 대해 언급된 속성(예: 하위 카테고리, 색상, 스타일, 핏, 패턴, 기장, 어느상황에서 입고 싶은지 등)을 식별하고, 각 속성별로 미리 정의된 Pydantic 모델의 필드 값들 중 **가장 의미적으로 유사한** 값을 찾아 매칭시킵니다.
        3. **엄격한 규칙 적용**:
            - **쿼리에 없는 정보는 절대 유추하지 마세요.** 쿼리에 해당 속성에 대한 내용이 없는 경우, 반드시 None 혹은 빈 리스트로 [] 처리해야 합니다.
            - 특히, **'스타일' 및 'TPO' 태그는 사용자가 명시적으로 언급한 경우에만 매칭하세요.** '편한', '멋진'과 같이 모호한 표현을 기반으로 태그를 유추하지 않습니다.
            - **가장 유사한 값만 매칭**: 쿼리의 내용과 Pydantic 모델의 값이 **매우 유사할 때만** 매칭하고, 모호하거나 관련 없는 내용은 `None`으로 처리합니다.
        4. **쿼리 재작성**:
            - 추출된 각 필터 값을 이용하여 **자연스러운 문장 형태**의 독립적인 쿼리를 `rewritten_query` 필드에 작성합니다. 이때, **사용자의 원래 의도를 유지**하되, 검색에 적합한 형태로 만드세요.
        # 중요
        위의 작업지침을 단계적으로 처리해주세요.
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_template),
            ("human", "공통 문맥: {common_context}\n분석할 쿼리: {raw_query}")
        ])
        return prompt | self.llm2.with_structured_output(output_pydantic_model)

    def _create_full_chain(self):
        first_chain = self._get_first_chain()
        top_analyzer = self._get_second_chain(MainCategory.TOP)
        bottom_analyzer = self._get_second_chain(MainCategory.BOTTOM)

        def dynamic_router(initial_data: InitialAnalysis):
            branches = {}
            for idx, item in enumerate(initial_data.items):
                analyzer = top_analyzer if item.item_type == MainCategory.TOP else bottom_analyzer
                
                selector = RunnableLambda(
                    lambda data, current_item=item: {
                        "common_context": data.common_context,
                        "raw_query": current_item.raw_query
                    },
                    name=f"SelectItem_{idx}"
                )
                key = f"{item.item_type.value}_{idx}"
                branches[key] = selector | analyzer
            
            if not branches:
                return RunnableLambda(lambda x: {{}})
                
            return RunnableParallel(**branches)

        main_chain = first_chain | RunnableLambda(dynamic_router, name="DynamicRouter")
        return main_chain

    async def analyze(self, query: str) -> dict:
        """
        Analyzes the user query asynchronously and returns a dictionary of structured results,
        with each key corresponding to an identified item.
        """
        chain = self._create_full_chain()
        return await chain.ainvoke({"query": query})

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
                "main_category": "상의",
                "sub_category": "셔츠",
                "color": "블랙",
                "style_tags": "베이직",
                "tpo_tags": "데일리",
                "fit": "슬림 핏",
                "pattern_type": "무지/솔리드",
                "rewritten_query": "블랙 베이직 셔츠 구매"
                
            },
            ...
        ]
        ```
        """
        analysis_result = await self.analyze(query)
        
        formatted_result = []
        for key, value in analysis_result.items():
            if not value:
                continue
            item_type = key.split('_')[0]
            analysis_result = value.model_dump(mode="json") if hasattr(value, 'model_dump') else value
            
            formatted_item = {
                "main_category": item_type,
                **analysis_result
            }
            formatted_result.append(formatted_item)
        
        return formatted_result