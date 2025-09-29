from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, ChatMessage as LangchainChatMessage
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
    if content is None:
        logger.warning('Content is None, returning empty string')
        return ''

    if isinstance(content, str):
        return content
    text: list[str] = []
    for content_item in content:
        if isinstance(content_item, str):
            text.append(content_item)
            continue
        if isinstance(content_item, dict) and content_item.get('type', '') == 'text':
            text.append(content_item['text'])
    return ''.join(text)


def create_message(
    message_type: Literal['ai', 'human', 'tool', 'custom'],
    content: str,
    metadata: dict | None = None,
) -> BaseMessage:
    """Langchain의 BaseMessage 객체를 생성하기 위해 필요한 content 리스트 형태로 변환

    Args:
        message_type (Literal["ai" , "human" , "tool" , "custom"]): 메세지 타입
        content (str): 메세지 내용
        metadata (dict | None): 메타데이터

    Returns:
        BaseMessage: BaseMessage 객체

    Raises:
        ValueError: 잘못된 메시지 타입이나 내용인 경우
        TypeError: 잘못된 타입의 파라미터인 경우

    Example:
        AIMessage(
            content="요청하신 '강아지' 이미지입니다.",
            additional_kwargs={
                "type": "refer",
                "expert_type": "color_expert",
                "product_ids": ["3858441_블루", "4109513_화이트"]
            }
        )
        AIMessage(
            content="요청하신 '강아지' 이미지입니다.",
            additional_kwargs={}
        )

    """
    try:
        # 입력 검증
        if not message_type:
            logger.error('message_type is required')
            raise ValueError('message_type is required')

        if message_type not in ['ai', 'human', 'tool', 'custom']:
            logger.error(f'Invalid message type: {message_type}')
            raise ValueError(f'Invalid message type: {message_type}')

        if content is None:
            logger.warning('content is None, using empty string')
            content = ''

        if not isinstance(content, str):
            logger.error(f'content must be string, got {type(content)}')
            raise TypeError(f'content must be string, got {type(content)}')

        if metadata is not None and not isinstance(metadata, dict):
            logger.error(f'metadata must be dict or None, got {type(metadata)}')
            raise TypeError(f'metadata must be dict or None, got {type(metadata)}')

        # additional_kwargs 구성
        additional_kwargs = {}

        additional_kwargs['created_at'] = get_current_utc_timestamp().isoformat()

        if metadata:
            for key, value in metadata.items():
                additional_kwargs[key] = value

        # 메시지 타입에 따른 객체 생성
        try:
            match message_type:
                case 'ai':
                    message = AIMessage(content=content, additional_kwargs=additional_kwargs)
                case 'human':
                    message = HumanMessage(content=content, additional_kwargs=additional_kwargs)
                case 'tool':
                    # ToolMessage는 tool_call_id가 필요할 수 있음
                    message = ToolMessage(content=content, additional_kwargs=additional_kwargs)
                case 'custom':
                    # Custom 메시지는 별도 처리 필요
                    logger.warning('Custom message type not fully implemented')
                    message = AIMessage(content=content, additional_kwargs=additional_kwargs)

            return message

        except Exception as e:
            logger.error(f'Failed to create {message_type} message: {e}')
            raise ValueError(f'Failed to create {message_type} message: {e}')

    except Exception as e:
        if isinstance(e, (ValueError, TypeError)):
            raise
        logger.error(f'Unexpected error creating message: {e}')
        raise ValueError(f'Unexpected error creating message: {e}')


def create_ai_message(parts: dict) -> AIMessage:
    """Langchain의 AIMessage를 생성하기 위해 필요한 인자만 필터링 해서 안전하게 dict로 부터 AIMessage 객체 생성

    Args:
        parts (dict): AIMessage 생성에 필요한 파라미터들이 담긴 딕셔너리

    Returns:
        AIMessage: 생성된 AIMessage 객체

    Raises:
        ValueError: parts가 dict가 아니거나 필수 파라미터가 없는 경우
        TypeError: AIMessage 생성 시 타입 오류가 발생한 경우
    """
    sig = inspect.signature(AIMessage)
    valid_keys = set(sig.parameters)
    filtered = {k: v for k, v in parts.items() if k in valid_keys}
    return AIMessage(**filtered)


def langchain_to_chat_message(message: BaseMessage) -> ChatMessage:
    """langchain의 BaseMessage를 pydantic 모델로 정의한 ChatMessage 으로 변환

    Args:
        message (BaseMessage): 변환할 langchain BaseMessage 객체

    Returns:
        ChatMessage: 변환된 ChatMessage 객체

    Raises:
        ValueError: 지원하지 않는 메시지 타입이거나 변환 실패 시
        TypeError: 메시지 객체가 올바르지 않은 타입인 경우
    """
    if not isinstance(message, BaseMessage):
        logger.error(f'Expected BaseMessage, got {type(message)}: {message}')
        raise TypeError(f'Expected BaseMessage, got {type(message)}')

    try:
        match message:
            case HumanMessage():
                try:
                    content = convert_message_content_to_string(message.content)
                    human_message = ChatMessage(
                        type='human',
                        content=content,
                        additional_kwargs=message.additional_kwargs or {},
                    )
                    logger.debug(f'Converted HumanMessage to ChatMessage: {content[:100]}...')
                    return human_message
                except Exception as e:
                    logger.error(f'Error converting HumanMessage: {e}, content: {message.content}')
                    raise ValueError(f'Failed to convert HumanMessage: {e}')

            case AIMessage():
                try:
                    content = convert_message_content_to_string(message.content)
                    ai_message = ChatMessage(
                        type='ai',
                        content=content,
                        additional_kwargs=message.additional_kwargs or {},
                    )
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        ai_message.tool_calls = message.tool_calls
                    if hasattr(message, 'response_metadata') and message.response_metadata:
                        ai_message.response_metadata = message.response_metadata
                    logger.debug(f'Converted AIMessage to ChatMessage: {content[:100]}...')
                    return ai_message
                except Exception as e:
                    logger.error(f'Error converting AIMessage: {e}, content: {message.content}')
                    raise ValueError(f'Failed to convert AIMessage: {e}')

            case ToolMessage():
                try:
                    content = convert_message_content_to_string(message.content)
                    tool_message = ChatMessage(
                        type='tool',
                        content=content,
                        tool_call_id=getattr(message, 'tool_call_id', None),
                        additional_kwargs=message.additional_kwargs or {},
                    )
                    logger.debug(f'Converted ToolMessage to ChatMessage: {content[:100]}...')
                    return tool_message
                except Exception as e:
                    logger.error(f'Error converting ToolMessage: {e}, content: {message.content}')
                    raise ValueError(f'Failed to convert ToolMessage: {e}')

            # case LangchainChatMessage():
            #     try:
            #         if message.role == "custom":
            #             if not hasattr(message, 'content') or not message.content:
            #                 logger.error(f"Custom message has no content: {message}")
            #                 raise ValueError("Custom message must have content")

            #             custom_data = message.content[0] if isinstance(message.content, list) and message.content else message.content
            #             custom_message = ChatMessage(
            #                 type="custom",
            #                 content="",
            #                 custom_data=custom_data,
            #                 additional_kwargs=message.additional_kwargs or {},
            #             )
            #             logger.debug(f"Converted custom LangchainChatMessage to ChatMessage")
            #             return custom_message
            #         else:
            #             logger.error(f"Unsupported chat message role: {message.role}")
            #             raise ValueError(f"Unsupported chat message role: {message.role}")
            #     except Exception as e:
            #         logger.error(f"Error converting LangchainChatMessage: {e}, role: {getattr(message, 'role', 'unknown')}")
            #         raise ValueError(f"Failed to convert LangchainChatMessage: {e}")

            case _:
                logger.error(f'Unsupported message type: {message.__class__.__name__}')
                raise ValueError(f'Unsupported message type: {message.__class__.__name__}')

    except Exception as e:
        if isinstance(e, (ValueError, TypeError)):
            raise
        logger.error(f'Unexpected error converting message {message.__class__.__name__}: {e}')
        raise ValueError(f'Unexpected error converting message: {e}')


def remove_tool_calls(content: str | list[str | dict]) -> str | list[str | dict]:
    """주어진 content 내에서 tool calls 정보 삭제

    Args:
        content (str | list[str | dict]): 처리할 content

    Returns:
        str | list[str | dict]: tool calls가 제거된 content

    Raises:
        TypeError: content가 예상하지 못한 타입인 경우
    """

    if isinstance(content, str):
        return content
    return [content_item for content_item in content if isinstance(content_item, str) or content_item.get('type') != 'tool_use']
