from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from .models import SingleCallAnalysisResult, TopFilter, BottomFilter
from .llm_manager import LLMManager

class SingleStepAnalyzer:
    """Analyzes a fashion query in a single LLM call."""

    def __init__(self, model_provider: str, model_name: str, max_tokens: int = 2000):
        llm_manager = LLMManager()
        self.llm = llm_manager.load_llm(model_provider, model_name, max_tokens)
        self.chain = self._create_chain()

    def _create_chain(self):
        system_prompt = """
        당신은 패션 쿼리 분석 전문가입니다. 사용자 쿼리에서 언급된 모든 의류 아이템을 식별하고 JSON 형태로 구조화하여 반환합니다.

        ## 작업 방법
        1. 쿼리에서 모든 의류 아이템(상의/하의)을 찾습니다
        2. 각 아이템을 TopFilter 또는 BottomFilter 스키마에 맞춰 분석합니다
        3. 쿼리에 명시된 정보만 추출하고, 없으면 None/[]로 설정합니다
        4. 각 아이템에 대해 간단한 rewritten_query를 생성합니다

       ## 작업 지침
        0. **중요: 사용자가 추천하지 않거나, 거절하거나, 적절하지 않다고 언급하는 아이템은 분석 대상에서 완전히 제외하세요.**
        1. **전체 쿼리 분석**: 사용자 쿼리 전체를 읽고, 언급된 모든 개별 의류 아이템(예: 셔츠, 자켓, 슬랙스)을 찾아 목록을 만듭니다.
        2. **개별 아이템 분석 (반복)**: 목록의 각 아이템에 대해 다음을 수행합니다.
            a.  **타입 결정**: 아이템이 '상의'인지 '하의'인지 결정하고, 그에 맞는 `TopFilter` 또는 `BottomFilter` 스키마를 선택합니다.
            b.  **정보 추출 및 엄격한 태그 매칭**: 아이템의 모든 속성(하위 카테고리, 색상, 스타일, TPO, 핏, 패턴, 기장)을 추출합니다. 추출한 속성을 스키마의 각 필드 `description`에 명시된 **가능한 값(`Enum`) 중에서만** 매칭합니다.
            c.  **규칙 준수**:
                - 쿼리에 **명시적으로 언급된 정보만 추출**하고, 절대 유추하거나 가정하지 마세요.
                - 해당하는 정보가 없으면 **반드시 `None` 또는 빈 리스트(`[]`)로 설정**해야 합니다.
            d.  **쿼리 재작성**: 분석된 태그 정보와 사용자의 원래 의도를 종합하여, 해당 아이템만을 위한 자연스러운 검색용 문장(`rewritten_query`)을 생성합니다.
        3. **최종 종합**: 분석이 완료된 모든 아이템 객체들을 `analyzed_items` 리스트에 순서대로 추가하여 최종 결과를 완성합니다.

        ## 중요 예시
        - **사용자 쿼리**: "출근룩으로 입을 건데, 스트라이프 셔츠랑 그 위에 걸칠 검정색 자켓, 그리고 베이지색 슬랙스 찾아줘"
        - **완벽한 출력 (이러한 형식으로 출력해야 함)**:
        ```json
        {
          "analyzed_items": [
            {
              "sub_category": "셔츠-블라우스",
              "color": null,
              "style_tags": ["포멀"],
              "tpo_tags": ["오피스"],
              "fit": null,
              "pattern_type": "스트라이프",
              "length": null,
              "rewritten_query": "출근용 스트라이프 셔츠"
            },
            {
              "sub_category": null,
              "color": "블랙",
              "style_tags": ["포멀"],
              "tpo_tags": ["오피스"],
              "fit": null,
              "pattern_type": null,
              "length": null,
              "rewritten_query": "검정색 출근용 자켓"
            },
            {
              "sub_category": "슈트팬츠-슬랙스",
              "color": "베이지",
              "style_tags": ["포멀"],
              "tpo_tags": ["오피스"],
              "fit": null,
              "pattern_type": "무지",
              "length": null,
              "rewritten_query": "베이지색 출근용 슬랙스"
            }
          ]
        }
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            ("human", "분석할 사용자 쿼리: {query}")
        ])

        return (prompt | self.llm.with_structured_output(SingleCallAnalysisResult)).with_config({"tags": ["skip_stream"]})

    async def analyze(self, query: str) -> SingleCallAnalysisResult:
        """Analyzes the user query asynchronously and returns the structured result."""
        return await self.chain.ainvoke({"query": query})

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
                item_type = "상의"
            elif isinstance(item, BottomFilter):
                item_type = "하의"
            
            analysis_data = item.model_dump(mode='json')
            
            formatted_result.append({
                "main_category": item_type,
                **analysis_data
            })
            
        return formatted_result