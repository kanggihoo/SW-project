from langchain_core.messages import BaseMessage , HumanMessage , AIMessage , ToolMessage , ChatMessage as LangchainChatMessage
import logging
import inspect 
from typing import Literal

from graph.model.api_schema import ChatMessage
from .time import get_current_utc_timestamp

logger = logging.getLogger(__name__)


def convert_message_content_to_string(content: str | list[str | dict]) -> str:
    """langchain의 BaseMessage 객체의 .content가 입력으로 전달 받으면 ChatMessage 객체의 content에 담을 문자열 파싱 
    단순 문자열인 경우 그대로 반환 , 

    Args:
        content (str | list[str  |  dict]): langchain의 BaseMessage 객체의 .content

    Returns:
        str: ChatMessage 객체의 content에 담을 문자열
    """
    if isinstance(content, str):
        return content
    text: list[str] = []
    for content_item in content:
        if isinstance(content_item, str):
            text.append(content_item)
            continue
        if isinstance(content_item, dict) and content_item.get("type","") == "text":
            text.append(content_item["text"])
    return "".join(text)

def create_message(
    message_type:Literal["ai" , "human" , "tool" , "custom"] , 
    content: str , 
    metadata_type:Literal["text" , "image"] = "text" , 
    image_urls: list[str] | None = None,
    metadata:dict | None = None,
    ) -> BaseMessage:
    """Langchain의 AIMessage 객체를 생성하기 위해 필요한 content 리스트 형태로 변환

    Args:
        message_type (Literal["ai" , "human" , "tool" , "custom"]): 메세지 타입
        content (str): 메세지 내용
        metadata_type (Literal["text" , "image"]): 메타데이터 타입
        image_urls (list[str] | None): 이미지 URL 리스트
        metadata (dict | None): 메타데이터

    Returns:
        BaseMessage: BaseMessage 객체
    Example: 
        AIMessage(
            content="요청하신 '강아지' 이미지입니다.",
            additional_kwargs={
                "type": "image",
                "image_urls": ["s3://.../puppy-1.png"],
                "metadata": {
                    "role_id": "ai2",
                    "display_name": "이미지 검색 AI",
                }
            }
        )
    
    """
    #message 타입 확인
    if message_type not in ["ai" , "human" , "tool" , "custom"]:
        raise ValueError(f"Invalid message type: {message_type}")
    if metadata_type not in ["text" , "image"]:
        raise ValueError(f"Invalid metadata type: {metadata_type}")
    additional_kwargs = {}
    additional_kwargs["type"] = metadata_type
    additional_kwargs["created_at"] = get_current_utc_timestamp().isoformat()
    if image_urls and metadata_type == "image":
        additional_kwargs["image_urls"] = image_urls if isinstance(image_urls, list) else [image_urls]
    if metadata:
        additional_kwargs["metadata"] = metadata
    match message_type:
        case "ai":
            return AIMessage(content=content , additional_kwargs=additional_kwargs)
        case "human":
            return HumanMessage(content=content , additional_kwargs=additional_kwargs)

        


def create_ai_message(parts: dict) -> AIMessage:
    """Langchain의 AIMessage를 생성하기 위해 필요한 인자만 필터링 해서 안전하세 dict로 부터 AIMessage 객체 생성

    Args:
        parts (dict): _description_

    Returns:
        AIMessage: _description_
    """
    sig = inspect.signature(AIMessage)
    valid_keys = set(sig.parameters)
    filtered = {k: v for k, v in parts.items() if k in valid_keys}
    return AIMessage(**filtered)


def langchain_to_chat_message(message: BaseMessage) -> ChatMessage:
    """langchain의 BaseMessage를 pydantic 모델로 정의한 ChatMessage 으로 변환"""
    match message:
        case HumanMessage():
            human_message = ChatMessage(
                type="human",
                content=convert_message_content_to_string(message.content),
                additional_kwargs=message.additional_kwargs,
            )
            return human_message
        case AIMessage():
            ai_message = ChatMessage(
                type="ai",
                content=convert_message_content_to_string(message.content),
                additional_kwargs=message.additional_kwargs,
            )
            if message.tool_calls:
                ai_message.tool_calls = message.tool_calls
            if message.response_metadata:
                ai_message.response_metadata = message.response_metadata
            return ai_message
        case ToolMessage():
            tool_message = ChatMessage(
                type="tool",
                content=convert_message_content_to_string(message.content),
                tool_call_id=message.tool_call_id,
                additional_kwargs=message.additional_kwargs,
            )
            return tool_message
        case LangchainChatMessage():
            if message.role == "custom":
                custom_message = ChatMessage(
                    type="custom",
                    content="",
                    custom_data=message.content[0],
                    additional_kwargs=message.additional_kwargs,
                )
                return custom_message
            else:
                raise ValueError(f"Unsupported chat message role: {message.role}")
        case _:
            raise ValueError(f"Unsupported message type: {message.__class__.__name__}")
        

def remove_tool_calls(content:str | list[str | dict])-> str | list[str | dict]:
    "주어진 content 내에서 tool calls 정보 삭제"
    if isinstance(content , str):
        return content
    
    return [
        content_item
        for content_item in content
        if isinstance(content_item , str) or content_item.get("type") != "tool_use"
    ]

