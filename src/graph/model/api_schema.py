from typing import Annotated, Any, Literal, NotRequired, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field, SerializeAsAny

from llm.llm_models import AllModelEnum, OpenAIModelName, OpenRouterModelName


class AgentInfo(BaseModel):
    """Info about an available agent."""

    key: str = Field(
        description='Agent key.',
        examples=['research-assistant'],
    )
    description: str = Field(
        description='Description of the agent.',
        examples=['A research assistant for generating research papers.'],
    )


class UserInput(BaseModel):
    """agent에게 전달될 input
    message : 사용자 입력 메세지
    model : 사용할 모델
    thread_id : 대화 스레드 ID(고유한 유저에 대한 채팅방 식별 ID)
    user_id : 사용자 ID(동일한 사용자의 여러 채팅방에서 대화를 유지하기 위한 식별 ID)
    agent_config : 에이전트 설정
    is_predefined_template : 미리 정의된 템플릿 클릭 여부 (Perplexity처럼)
    """

    message: str = Field(
        description='사용자 입력 메세지',
        examples=['오늘 날씨 어때?'],
    )
    model: SerializeAsAny[AllModelEnum] | None = Field(
        title='Model',
        description='agent에 사용할 모델 이름',
        default=OpenRouterModelName.OPENROUTER_GEMINI_20_FLASH_LITE,
        examples=[OpenRouterModelName.OPENROUTER_GEMINI_20_FLASH_LITE, OpenAIModelName.GPT_4O_MINI],
    )
    thread_id: str | None = Field(
        description='Thread ID to persist and continue a multi-turn conversation.',
        default=None,
        examples=['847c6285-8fc9-4560-a83f-4e6285809254'],
    )
    user_id: str | None = Field(
        description='User ID to persist and continue a conversation across multiple threads.',
        default=None,
        examples=['847c6285-8fc9-4560-a83f-4e6285809254'],
    )
    agent_config: dict[str, Any] = Field(
        description='Additional configuration to pass through to the agent',
        default_factory=dict,
        examples=[{'spicy_level': 0.8}],
    )
    is_predefined_template: bool = Field(
        description='미리 정의된 템플릿(버튼) 클릭 여부. True: 템플릿 클릭, False: 직접 입력',
        default=False,
        examples=[False, True],
    )
    product_id: str | None = Field(
        description='채팅 UI에서 클릭한 제품 ID. None: 제품 클릭 안 함, str: 제품 ID',
        default=None,
        examples=[None, '4255016_블루'],
    )


class StreamInput(UserInput):
    """agent의 응답을 스트리밍할 때 API 입력 요청 형식, 기존의 UserInput 모델을 상속받아 스트리밍에 대한 응답을 원하는지 담고 있음"""

    stream_tokens: bool = Field(
        description='Whether to stream LLM tokens to the client.',
        default=True,
    )

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'message': '데이트',
                    'model': OpenRouterModelName.OPENROUTER_GEMINI_25_FLASH_LITE,
                    'thread_id': '847c6285-8fc9-4560-a83f-4e6285809254',
                    'user_id': '847c6285-8fc9-4560-a83f-4e6285809254',
                    'agent_config': {'spicy_level': 0.8},
                    'stream_tokens': True,
                    'product_id': '4255016_블루',
                }
            ]
        }
    }


class ToolCall(TypedDict):
    """Represents a request to call a tool."""

    name: str
    """The name of the tool to be called."""
    args: dict[str, Any]
    """The arguments to the tool call."""
    id: str | None
    """An identifier associated with the tool call."""
    type: NotRequired[Literal['tool_call']]


# TODO : 여기서 content 필드를 호환성을 위해 str이 아닌 List형태로 정의하는게 좋아보이는데
class ChatMessage(BaseModel):
    """Langchain의 BaseMessage를 pydantic 모델로 정의한 ChatMessage 으로 변환 후 API 요청에 대한 응답 데이터 타입"""

    type: Literal['human', 'ai', 'tool', 'custom'] = Field(
        description='Role of the message.',
        examples=['human', 'ai', 'tool', 'custom'],
    )
    content: str = Field(
        description='Content of the message.',
        examples=['Hello, world!'],
    )
    tool_calls: list[ToolCall] = Field(
        description='Tool calls in the message.',
        default_factory=list,
    )
    tool_call_id: str | None = Field(
        description='type = tool 혹은 ai이면서 tool_calls 필드가 있는 경우 메세지의 tool_call_id 전달',
        default=None,
        examples=['call_Jja7J89XsjrOLA5r!MEOW!SL'],
    )
    # run_id: str | None = Field(
    #     description="Run ID of the message.",
    #     default=None,
    #     examples=["847c6285-8fc9-4560-a83f-4e6285809254"],
    # )
    # response_metadata: dict[str, Any] = Field(
    #     description="type = ai 인경우 ai 메세지의 response_metadata 필드 전달 For example: response headers, logprobs, token counts.",
    #     default_factory=dict,
    # )
    additional_kwargs: dict[str, Any] = Field(
        description='additional_kwargs 필드 전달',
        default_factory=dict,
    )
    # custom_data: dict[str, Any] = Field(
    #     description="type = custom 인 경우 content 필드 대신 해당 필드에 데이터 전달",
    #     default_factory=dict,
    # )

    def pretty_repr(self) -> str:
        """Get a pretty representation of the message."""
        base_title = self.type.title() + ' Message'
        padded = ' ' + base_title + ' '
        sep_len = (80 - len(padded)) // 2
        sep = '=' * sep_len
        second_sep = sep + '=' if len(padded) % 2 else sep
        title = f'{sep}{padded}{second_sep}'
        return f'{title}\n\n{self.content}'

    def pretty_print(self):
        print(self.pretty_repr())


class ChatHistoryInput(BaseModel):
    """사용자가 원하는 thread_id에 대한 채팅 내역을 보고 싶은 경우 API 입력 요청 형식"""

    thread_id: str = Field(
        description='Thread ID to persist and continue a multi-turn conversation.',
        examples=['847c6285-8fc9-4560-a83f-4e6285809254'],
    )


# TODO : 마찬가지로 cursor 기반 pagenation을 위해 응답으로 최근 메세지의 ts를 client에게 다시 전달하는 구조로
class ChatHistory(BaseModel):
    """사용자가 원하는 thread_id에 대한 채팅 내역을 보고 싶은 경우 API 응답 데이터 타입"""

    messages: list[ChatMessage]


class ServiceMetadata(BaseModel):
    """사용자가 요청할 수 있는 agents 및 models 및 추가 메타정보를 담는 객체
    Args:
        agents : 사용 가능한 agents 목록
        models : 사용 가능한 models 목록
        default_agent : 기본 agent
        default_model : 기본 model
    """

    agents: list[str] = Field(
        description='List of available agents.',
        examples=['chatbot', 'product', 'search', 'external_llm', 'llm_search'],
    )
    models: list[AllModelEnum] = Field(
        description='List of available LLMs.',
    )
    default_agent: str = Field(
        description='Default agent used when none is specified.',
        examples=['research-assistant'],
    )
    default_model: AllModelEnum = Field(
        description='Default model used when none is specified.',
    )


class StatusUpdate(BaseModel):
    """특정 작업의 진행 상태를 클라이언트에 전달하기 위한 모델
    task_id : 작업의 고유 ID. 동일한 작업의 시작과 종료를 매칭하는 데 사용됩니다.
    state : 작업의 현재 상태 (시작, 종료, 진행중, 에러)
    content : 사용자에게 보여줄 메시지 (예: '벡터 DB 검색 중...')
    error_details : 에러 발생 시 추가적인 에러 정보를 담을 수 있는 필드
    """

    task_id: Annotated[
        str, Field(default_factory=lambda: str(uuid4()), description='작업의 고유 ID. 동일한 작업의 시작과 종료를 매칭하는 데 사용됩니다.')
    ]

    state: Literal['start', 'end', 'progress', 'error'] = Field(
        description='작업의 현재 상태 (시작, 종료, 진행중, 에러)',
        examples=['start', 'end', 'progress', 'error'],
    )

    content: str = Field(
        description="사용자에게 보여줄 메시지 (예: '벡터 DB 검색 중...')",
        examples=['벡터 DB 검색 중...'],
    )

    # 에러 발생 시 추가적인 에러 정보를 담을 수 있는 필드
    error_details: str | None = None


class DeleteHistoryResponse(BaseModel):
    """사용자 채팅 내역 삭제 응답 모델"""

    success: Annotated[bool, '삭제 결과 성공 여부']
    message: Annotated[str, '삭제 결과 메시지']
    data: Annotated[dict[str, Any], Field(default_factory=dict, description='삭제 결과 데이터')]

    model_config = {
        'json_schema_extra': {
            'examples': [{'success': True, 'message': '사용자 채팅 내역 삭제 완료', 'data': {'thread_id': '847c6285-8fc9-4560-a83f-4e6285809254'}}]
        }
    }


class ErrorResponse(BaseModel):
    """API 오류 응답 모델"""

    detail: Annotated[str, Field(description='오류 상세 메시지')]

    model_config = {'json_schema_extra': {'examples': [{'detail': 'Unexpected error'}]}}


if __name__ == '__main__':
    message = ChatMessage(type='human', content='Hello, world!')
    message.pretty_print()
