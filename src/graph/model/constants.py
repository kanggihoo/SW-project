from enum import StrEnum 

class SSETypes(StrEnum):
    """SSE 타입"""
    STATUS = "status"
    MESSAGE = "message"
    TOKEN = "token"
    ERROR = "error"
    END = "[DONE]"

class MessageTypes(StrEnum):
    """Message type"""
    AI = "ai"
    HUMAN = "human"
    TOOL = "tool"
    CUSTOM = "custom"

class ExternalLLMNames(StrEnum):
    """Agent name"""
    COLOR_ANALYST = "color_analyst"
    STYLE_ANALYST = "style_analyst"
    FASHION_ANALYST = "fashion_analyst"