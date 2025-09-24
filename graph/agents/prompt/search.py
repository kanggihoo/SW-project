from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder
from langchain_core.messages import SystemMessage

SYSTEM_MESSAGE = "사용자 질문에 대해서 적합한 상항에 대한 옷에 대해서 응답을 해주세요. 이때 반드시 상의와 하의 하나의 조합만 응답해주세요 \
    예시 응답 : 상의 : 티셔츠 , 하의 : 청바지 \
        "


search_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_MESSAGE),
        MessagesPlaceholder(variable_name="messages"),
    ])

