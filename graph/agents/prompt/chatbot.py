from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder
from langchain_core.messages import SystemMessage

SYSTEM_MESSAGE = "You are a helpful assistant. and answer in Korean."


chatbot_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_MESSAGE),
        MessagesPlaceholder(variable_name="messages"),
    ])

