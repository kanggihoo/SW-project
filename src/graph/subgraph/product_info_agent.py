from langgraph.prebuilt import create_react_agent

from graph.constants import NodeName
from llm import get_llm_model

llm = get_llm_model('google/gemini-2.5-flash-lite')

product_info_agent = create_react_agent(
    model=llm,
    tools=[],
    prompt='You are a product info agent. You are given a product name and you need to fetch the product information.',
    name=NodeName.PRODUCT_INFO_AGENT,
)
