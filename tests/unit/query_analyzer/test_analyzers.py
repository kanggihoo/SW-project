import pytest
from unittest.mock import MagicMock, patch

from query_analyzer.single_step_analyzer import SingleStepAnalyzer
from query_analyzer.multi_step_analyzer import MultiStepAnalyzer
from query_analyzer.models import (
    SingleCallAnalysisResult,
    InitialAnalysis,
    IdentifiedItem,
    TopFilter,
    BottomFilter,
    ItemType,
    Color,
    StyleTag,
    TPOTag,
    TopSubCategory,
    BottomSubCategory
)

# Sample query for testing
SAMPLE_QUERY = "출근룩으로 입을 건데, 스트라이프 셔츠랑 베이지색 슬랙스 찾아줘"

# --- SingleStepAnalyzer Tests ---

@patch('query_analyzer.single_step_analyzer.LLMManager')
def test_single_step_analyzer(MockLLMManager):
    """Tests if the SingleStepAnalyzer correctly processes a query."""
    # Arrange
    mock_llm_instance = MockLLMManager.return_value.get_llm.return_value
    
    mock_result = SingleCallAnalysisResult(
        analyzed_items=[
            TopFilter(
                item_type=ItemType.TOP,
                item_name="스트라이프 셔츠",
                sub_category=TopSubCategory.SHIRT_BLOUSE,
                color=Color.STRIPE,
                style_tags=[StyleTag.FORMAL, StyleTag.BASIC],
                tpo_tags=[TPOTag.OFFICE],
                rewritten_query="출근룩으로 입기 좋은 스트라이프 셔츠"
            ),
            BottomFilter(
                item_type=ItemType.BOTTOM,
                item_name="베이지색 슬랙스",
                sub_category=BottomSubCategory.SUIT_SLACKS,
                color=Color.BEIGE,
                style_tags=[StyleTag.FORMAL, StyleTag.BASIC],
                tpo_tags=[TPOTag.OFFICE],
                rewritten_query="출근룩에 어울리는 베이지색 슬랙스"
            )
        ]
    )
    mock_llm_instance.with_structured_output.return_value.invoke.return_value = mock_result

    analyzer = SingleStepAnalyzer(model_provider="mock", model_name="mock")

    # Act
    result = analyzer.analyze(SAMPLE_QUERY)

    # Assert
    assert isinstance(result, SingleCallAnalysisResult)
    assert len(result.analyzed_items) == 2
    assert result.analyzed_items[0].item_name == "스트라이프 셔츠"
    assert result.analyzed_items[1].color == Color.BEIGE
    mock_llm_instance.with_structured_output.return_value.invoke.assert_called_once_with({"query": SAMPLE_QUERY})


# --- MultiStepAnalyzer Tests ---

@patch('query_analyzer.multi_step_analyzer.LLMManager')
def test_multi_step_analyzer(MockLLMManager):
    """Tests if the MultiStepAnalyzer correctly processes a query through its two steps."""
    # Arrange
    mock_llm_instance = MockLLMManager.return_value.get_llm.return_value

    mock_initial_analysis = InitialAnalysis(
        items=[
            IdentifiedItem(item_type=ItemType.TOP, raw_query="스트라이프 셔츠, 출근룩"),
            IdentifiedItem(item_type=ItemType.BOTTOM, raw_query="베이지색 슬랙스, 출근룩")
        ],
        common_context="출근룩"
    )
    mock_top_result = TopFilter(
        item_type=ItemType.TOP, item_name="스트라이프 셔츠", sub_category=TopSubCategory.SHIRT_BLOUSE,
        color=Color.STRIPE, style_tags=[StyleTag.FORMAL], tpo_tags=[TPOTag.OFFICE],
        rewritten_query="출근룩 스트라이프 셔츠"
    )
    mock_bottom_result = BottomFilter(
        item_type=ItemType.BOTTOM, item_name="베이지색 슬랙스", sub_category=BottomSubCategory.SUIT_SLACKS,
        color=Color.BEIGE, style_tags=[StyleTag.FORMAL], tpo_tags=[TPOTag.OFFICE],
        rewritten_query="출근룩 베이지색 슬랙스"
    )

    def structured_output_side_effect(pydantic_model):
        chain_mock = MagicMock()
        if pydantic_model == InitialAnalysis:
            chain_mock.invoke.return_value = mock_initial_analysis
        elif pydantic_model == TopFilter:
            chain_mock.invoke.return_value = mock_top_result
        elif pydantic_model == BottomFilter:
            chain_mock.invoke.return_value = mock_bottom_result
        return chain_mock

    mock_llm_instance.with_structured_output.side_effect = structured_output_side_effect
    
    analyzer = MultiStepAnalyzer(model_provider="mock", model_name="mock")

    # Act
    result = analyzer.analyze(SAMPLE_QUERY)

    # Assert
    assert isinstance(result, dict)
    assert "item_0" in result
    assert "item_1" in result
    assert isinstance(result["item_0"], TopFilter)
    assert isinstance(result["item_1"], BottomFilter)
    assert result["item_0"].item_name == "스트라이프 셔츠"
    assert result["item_1"].color == Color.BEIGE
