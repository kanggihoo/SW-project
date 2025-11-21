from __future__ import annotations

from langchain_tavily import TavilySearch
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from graph.constants import NodeName
from graph.settings import settings
from llm import get_llm_model

SYSTEM_PROMPT = """
**Your Role:** You are an expert AI assistant specialized in answering user questions using real-time search results.

**Your Goal:** To provide accurate, relevant, and concise answers based *only* on the information retrieved from your search tools. You must respond in Korean.

**Core Instructions:**
1.  **Analyze the Input:** First, carefully understand what the user is asking.
2.  **Use Your Tools:** Use the search tool to find the information for the given question.
3.  **Synthesize and Respond:** Combine the information you've gathered from the tools into a clear and easy-to-understand answer for the user.
4.  **Handle Missing Information:** If you use your tools and cannot find the information needed to answer the question, you MUST inform the user politely that you were unable to find the specific information.

**Crucial Rules:**
-   **Tool-Use is Mandatory:** ALWAYS use your tools to get information. Do not rely on pre-existing knowledge.
-   **Language:** All your final responses to the user must be in polite, natural Korean.
"""


def build_info_qa_agent_subgraph() -> CompiledStateGraph:
    # Using the same model as the product info agent example
    llm = get_llm_model('google/gemini-2.5-flash')

    # Connect LangChain's Tavily search tool
    # This tool requires TAVILY_API_KEY to be set in the environment variables
    tool = TavilySearch(
        tavily_api_key=settings.TAVILY_API_KEY.get_secret_value() if settings.TAVILY_API_KEY else None,
        max_results=5,
    )

    info_qa_agent = create_react_agent(
        model=llm,
        tools=[tool],
        prompt=SYSTEM_PROMPT,
        name=NodeName.INFO_QA,
    )
    return info_qa_agent


info_qa_agent_subgraph = build_info_qa_agent_subgraph()
