# ruff: noqa: E501
from __future__ import annotations

from langchain.tools import StructuredTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

# from app.services.musinsa import MusinsaAPIWrapper
from graph.constants import NodeName
from graph.tools.definition import PRODUCT_TOOL_DEFINITION
from graph.tools.handlers.product_handlers import ProductToolHandlers
from llm import get_llm_model

SYSTEM_PROMPT = """
**Your Role:** You are a specialized AI agent, an expert at retrieving product information. Your sole purpose is to answer user questions about a specific product using a set of tools you have access to.

**Your Goal:** To provide accurate, relevant, and concise answers based *only* on the information retrieved from your tools. You must respond in Korean.

**Core Instructions:**
1.  **Analyze the Input:** You will receive a `product_id` and a user's question. First, carefully understand what the user is asking 
2.  **Use Your Tools:** Based on your analysis, select and use the most appropriate tool(s) to find the information for the given `product_id`. You may need to use multiple tools to fully answer a question. The tool descriptions will guide you on what each tool does.
3.  **Synthesize and Respond:** Combine the information you've gathered from the tools into a clear and easy-to-understand answer for the user.
4.  **Handle Missing Information:** If you use your tools and cannot find the information needed to answer the question, you MUST inform the user politely that you were unable to find the specific information. Do not make up answers or use any knowledge outside of the tool outputs.

**--- 중요: 도구 호출 형식 규칙 (Tool Calling Format Rule) ---**
-   **여러 도구를 호출해야 할 경우, 각 도구 호출을 `tool_calls` 리스트 안에 별개의 객체로 만들어야 합니다.**
-   **절대로 여러 함수의 이름이나 인자를 하나의 객체 안에 합치지 마세요.**

-   **올바른 예시 (Correct Example for 2 tool calls):**
    ```json
    "tool_calls": [
      {
        "name": "get_product_like_count",
        "arguments": { "product_id": 12345 },
        "id": "call_abc"
      },
      {
        "name": "get_brand_and_price",
        "arguments": { "product_id": 12345 },
        "id": "call_def"
      }
    ]
    ```

-   **잘못된 예시 (Incorrect Example - DO NOT DO THIS):**
    ```json
    "tool_calls": [
      {
        "name": "get_product_like_countget_brand_and_price",
        "arguments": "{\\"product_id\\": 12345}{\\"product_id\\": 12345}"
      }
    ]
    ```

**Crucial Rules:**
-   **Tool-Use is Mandatory:** ALWAYS use your tools to get information. Do not rely on pre-existing knowledge.
-   **Language:** All your final responses to the user must be in polite, natural Korean.
"""


def build_product_info_agent_subgraph(musinsa_api_wrapper, cache_client, task_queue_client, db_repository) -> CompiledStateGraph:
    # llm = get_llm_model('google/gemini-2.5-flash-lite')
    llm = get_llm_model('google/gemini-2.5-flash')

    # Bind tools from handler based on TOOL_DEFINITION
    # service = 'MusinsaAPIWrapper'(client)
    handlers = ProductToolHandlers(musinsa_api_wrapper, cache_client, task_queue_client, db_repository)

    bound_tools: list[StructuredTool] = []
    for spec in PRODUCT_TOOL_DEFINITION:
        name = spec['name']
        args_schema = spec['args_schema']
        handler_func = getattr(handlers, f'handle_{name}')
        tool = StructuredTool.from_function(
            func=None,
            name=name,
            description=(handler_func.__doc__ or name),
            args_schema=args_schema,
            coroutine=handler_func,
        )
        bound_tools.append(tool)

    product_info_agent = create_react_agent(
        model=llm,
        tools=bound_tools,
        prompt=SYSTEM_PROMPT,
        name=NodeName.PRODUCT_INFO_AGENT,
    )
    return product_info_agent
