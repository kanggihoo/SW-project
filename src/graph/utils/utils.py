# ruff: noqa: E501
import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from loguru import logger

from graph.constants import COLOR_EXPERT, FITTING_COORDINATOR, SHOW_CACHED, SKIP_STREAM, STYLE_ANALYST, GraphName, NodeName, SSETypes, StateName
from graph.model.api_schema import ChatMessage, StreamInput, UserInput
from graph.model.graph_schemas import ClothSearch

from .messages import convert_message_content_to_string, create_ai_message, create_message, langchain_to_chat_message, remove_tool_calls


def _get_search_subgraph_initial_state(user_input: UserInput, current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    search_subgraph 테스트를 위한 다양한 시나리오별 초기 state 생성

    시나리오 키워드:
    - "최초검색" or 기본: 새로운 벡터 검색 시작
    - "캐시순환" or "다른거": 캐시된 결과에서 다음 코디 가져오기
    - "캐시소진": 캐시는 있지만 모두 소진된 상태
    - "색상변경": 색상 조건만 변경 (color_expert만 재실행)
    - "스타일변경": 스타일 조건만 변경 (style_analyst만 재실행)

    Args:
        user_input: 사용자 입력
        current_state: 현재 그래프의 state (있으면 기존 상태 유지/병합, 없으면 새로 생성)
    """
    message = user_input.message.lower()

    # 기존 state가 있는지 확인
    has_existing_state = current_state is not None and bool(current_state)

    # 시나리오 1: 캐시 순환 (데이터 충분)
    if '캐시순환' in message or '다른거' in message:
        # 기존 state가 있으면 기존 데이터 유지하고 필요한 필드만 업데이트
        if has_existing_state:
            logger.info('기존 state 유지 - 캐시 순환 모드')
            return {
                StateName.USER_MESSAGE: user_input.message,
                StateName.LAST_UPDATED_FIELDS: [SHOW_CACHED],  # 캐시 순환 플래그
            }

        # 기존 state가 없으면 테스트용 mock state 생성
        logger.info('테스트용 mock state 생성 - 캐시 순환')
        return {
            StateName.USER_MESSAGE: user_input.message,
            StateName.LAST_UPDATED_FIELDS: [SHOW_CACHED],  # 캐시 순환 플래그
            StateName.MESSAGES: [],
            StateName.EXPERT_OPINIONS: {
                COLOR_EXPERT: '블루 셔츠에 네이비 베스트와 그레이 와이드 슬랙스는톤온톤 원리로 세련된 색상 조화를 이루고 있어. 차가운 계열의 블루와 네이비의 레이어드는 명도 대비를 통해 깊이감을 만들어내. 화이트 셔츠의 포인트와 블랙 로퍼의 마무리로 전체적인 색상밸런스가 안정적으로 구성되어 있어.',
                STYLE_ANALYST: '화이트 버튼다운 반팔 셔츠에 블랙 핀스트라이프 슬랙스가 잘 어울려. 셔츠 앞부분만 살짝 넣어서 캐주얼하면서도 세련된 데이트룩을 완성할 수 있어. 브라운 옥스포드 슈즈로 포멀한 느낌을 더하고 실버 가죽 시계로 포인트를 줘.셔츠 버튼 1-2개 풀어서 답답해보이지 않게 연출하면 돼.',
                FITTING_COORDINATOR: '베이지 오버핏 반팔 셔츠에 블랙 와이드슬랙스가잘 어울려. 면소재의 여유로운 셔츠 실루엣에깔끔한블랙 슬랙스로세련된 데이트룩이완성될거야. 셔츠 앞부분만살짝 넣어서자연스러운 느낌을 주고, 위쪽 버튼 1-2개 정도는풀어두는게좋아.블랙 옥스포드 슈즈로포멀함을 더하고브라운 가죽 서류가방으로 포인트를 더하고줘서세련된 분위기를 연출할수 있어. 여유로운 실루엣이지만 전체적으로 균형 잡힌 비율이라데이트 장소 어디든잘 어울릴 거야.',
            },
            StateName.EXPERT_SEARCH_CACHE: {
                COLOR_EXPERT: {
                    'TOP': ['4255016_블루', '3271408_블루', '4045204_블루', '3858441_블루', '3290710_블루'],
                    'BOTTOM': ['5081343_그레이', '2711142_그레이', '3201942_그레이', '4897566_그레이', '4750059_그레이'],
                },
                STYLE_ANALYST: {
                    'TOP': ['3847744_화이트', '4989731_화이트', '4898914_화이트', '4989730_화이트', '2171532_화이트'],
                    'BOTTOM': ['2503135_블랙', '3201942_블랙', '4149670_블랙', '4750059_블랙', '3187939_블랙'],
                },
                FITTING_COORDINATOR: {
                    'TOP': ['4227290_베이지', '4045199_베이지', '4917809_베이지', '3847744_베이지', '4045204_베이지'],
                    'BOTTOM': ['2711142_블랙', '3201942_블랙', '3139448_블랙', '4149670_블랙', '3187939_블랙'],
                },
            },
            StateName.EXPERT_OFFSETS: {
                COLOR_EXPERT: 1,  # 이미 첫 번째 코디 표시함
                STYLE_ANALYST: 1,
                FITTING_COORDINATOR: 1,
            },
            StateName.SHOWN_IN_PRODUCT_IDS: {'4255016_블루', '5081343_그레이', '3847744_화이트', '2503135_블랙', '4227290_베이지', '2711142_블랙'},
        }

    # 시나리오 2: 캐시 소진
    elif '캐시소진' in message:
        # 기존 state가 있으면 기존 데이터 유지하고 필요한 필드만 업데이트
        if has_existing_state:
            logger.info('기존 state 유지 - 캐시 소진 테스트')
            return {
                StateName.USER_MESSAGE: user_input.message,
                StateName.LAST_UPDATED_FIELDS: [SHOW_CACHED],
            }

        # 기존 state가 없으면 테스트용 mock state 생성
        logger.info('테스트용 mock state 생성 - 캐시 소진')
        return {
            StateName.USER_MESSAGE: user_input.message,
            StateName.LAST_UPDATED_FIELDS: [SHOW_CACHED],
            StateName.MESSAGES: [],
            StateName.EXPERT_OPINIONS: {
                COLOR_EXPERT: '블루 셔츠에 네이비 베스트와 그레이 와이드 슬랙스는톤온톤 원리로 세련된 색상 조화를 이루고 있어. 차가운 계열의 블루와 네이비의 레이어드는 명도 대비를 통해 깊이감을 만들어내. 화이트 셔츠의 포인트와 블랙 로퍼의 마무리로 전체적인 색상밸런스가 안정적으로 구성되어 있어.',
                STYLE_ANALYST: '화이트 버튼다운 반팔 셔츠에 블랙 핀스트라이프 슬랙스가 잘 어울려. 셔츠 앞부분만 살짝 넣어서 캐주얼하면서도 세련된 데이트룩을 완성할 수 있어. 브라운 옥스포드 슈즈로 포멀한 느낌을 더하고 실버 가죽 시계로 포인트를 줘.셔츠 버튼 1-2개 풀어서 답답해보이지 않게 연출하면 돼.',
                FITTING_COORDINATOR: '베이지 오버핏 반팔 셔츠에 블랙 와이드슬랙스가잘 어울려. 면소재의 여유로운 셔츠 실루엣에깔끔한블랙 슬랙스로세련된 데이트룩이완성될거야. 셔츠 앞부분만살짝 넣어서자연스러운 느낌을 주고, 위쪽 버튼 1-2개 정도는풀어두는게좋아.블랙 옥스포드 슈즈로포멀함을 더하고브라운 가죽 서류가방으로 포인트를 더하고줘서세련된 분위기를 연출할수 있어. 여유로운 실루엣이지만 전체적으로 균형 잡힌 비율이라데이트 장소 어디든잘 어울릴 거야.',
            },
            StateName.EXPERT_SEARCH_CACHE: {
                COLOR_EXPERT: {
                    'TOP': ['4255016_블루', '3271408_블루', '4045204_블루'],
                    'BOTTOM': ['5081343_그레이', '2711142_그레이', '3201942_그레이'],
                },
                STYLE_ANALYST: {
                    'TOP': ['3847744_화이트', '4989731_화이트'],
                    'BOTTOM': ['2503135_블랙', '3201942_블랙'],
                },
                FITTING_COORDINATOR: {
                    'TOP': ['4227290_베이지', '4045199_베이지', '4917809_베이지'],
                    'BOTTOM': ['2711142_블랙', '3201942_블랙', '3139448_블랙'],
                },
            },
            StateName.EXPERT_OFFSETS: {
                COLOR_EXPERT: 3,  # 모든 캐시 소진
                STYLE_ANALYST: 2,  # 모든 캐시 소진
                FITTING_COORDINATOR: 3,  # 모든 캐시 소진
            },
            StateName.SHOWN_IN_PRODUCT_IDS: {
                '4255016_블루',
                '5081343_그레이',
                '3271408_블루',
                '2711142_그레이',
                '4045204_블루',
                '3201942_그레이',
                '3847744_화이트',
                '2503135_블랙',
                '4989731_화이트',
                '3201942_블랙',
                '4227290_베이지',
                '2711142_블랙',
                '4045199_베이지',
                '4917809_베이지',
                '3139448_블랙',
            },
        }

    # 시나리오 3: 색상 조건만 변경
    elif '색상변경' in message or '색상' in message:
        # 기존 state가 있으면 기존 의견 유지하고 캐시/offset 초기화
        if has_existing_state:
            logger.info('기존 state 유지 - 색상 조건 변경, 캐시 초기화')
            return {
                StateName.USER_MESSAGE: user_input.message,
                StateName.LAST_UPDATED_FIELDS: ['color'],  # 색상만 변경
                StateName.EXPERT_SEARCH_CACHE: {},  # 조건 변경 시 캐시 초기화
                StateName.EXPERT_OFFSETS: {
                    COLOR_EXPERT: 0,
                    STYLE_ANALYST: 0,
                    FITTING_COORDINATOR: 0,
                },
                StateName.SHOWN_IN_PRODUCT_IDS: set(),
            }

        # 기존 state가 없으면 테스트용 mock state 생성
        logger.info('테스트용 mock state 생성 - 색상 조건 변경')
        return {
            StateName.USER_MESSAGE: user_input.message,
            StateName.LAST_UPDATED_FIELDS: ['color'],  # 색상만 변경
            StateName.MESSAGES: [],
            StateName.EXPERT_OPINIONS: {
                STYLE_ANALYST: '화이트 버튼다운 반팔 셔츠에 블랙 핀스트라이프 슬랙스가 잘 어울려. 셔츠 앞부분만 살짝 넣어서 캐주얼하면서도 세련된 데이트룩을 완성할 수 있어. 브라운 옥스포드 슈즈로 포멀한 느낌을 더하고 실버 가죽 시계로 포인트를 줘.셔츠 버튼 1-2개 풀어서 답답해보이지 않게 연출하면 돼.',
                FITTING_COORDINATOR: '베이지 오버핏 반팔 셔츠에 블랙 와이드슬랙스가잘 어울려. 면소재의 여유로운 셔츠 실루엣에깔끔한블랙 슬랙스로세련된 데이트룩이완성될거야. 셔츠 앞부분만살짝 넣어서자연스러운 느낌을 주고, 위쪽 버튼 1-2개 정도는풀어두는게좋아.블랙 옥스포드 슈즈로포멀함을 더하고브라운 가죽 서류가방으로 포인트를 더하고줘서세련된 분위기를 연출할수 있어. 여유로운 실루엣이지만 전체적으로 균형 잡힌 비율이라데이트 장소 어디든잘 어울릴 거야.',
            },
            StateName.EXPERT_SEARCH_CACHE: {},  # 조건 변경 시 캐시 초기화됨
            StateName.EXPERT_OFFSETS: {
                COLOR_EXPERT: 0,
                STYLE_ANALYST: 0,
                FITTING_COORDINATOR: 0,
            },
            StateName.SHOWN_IN_PRODUCT_IDS: set(),
        }

    # 시나리오 4: 스타일 조건만 변경
    elif '스타일변경' in message or '스타일' in message:
        # 기존 state가 있으면 기존 의견 유지하고 캐시/offset 초기화
        if has_existing_state:
            logger.info('기존 state 유지 - 스타일 조건 변경, 캐시 초기화')
            return {
                StateName.USER_MESSAGE: user_input.message,
                StateName.LAST_UPDATED_FIELDS: ['style'],  # 스타일만 변경
                StateName.EXPERT_SEARCH_CACHE: {},  # 조건 변경 시 캐시 초기화
                StateName.EXPERT_OFFSETS: {
                    COLOR_EXPERT: 0,
                    STYLE_ANALYST: 0,
                    FITTING_COORDINATOR: 0,
                },
                StateName.SHOWN_IN_PRODUCT_IDS: set(),
            }

        # 기존 state가 없으면 테스트용 mock state 생성
        logger.info('테스트용 mock state 생성 - 스타일 조건 변경')
        return {
            StateName.USER_MESSAGE: user_input.message,
            StateName.LAST_UPDATED_FIELDS: ['style'],  # 스타일만 변경
            StateName.MESSAGES: [],
            StateName.EXPERT_OPINIONS: {
                COLOR_EXPERT: '블루 셔츠에 네이비 베스트와 그레이 와이드 슬랙스는톤온톤 원리로 세련된 색상 조화를 이루고 있어. 차가운 계열의 블루와 네이비의 레이어드는 명도 대비를 통해 깊이감을 만들어내. 화이트 셔츠의 포인트와 블랙 로퍼의 마무리로 전체적인 색상밸런스가 안정적으로 구성되어 있어.',
                FITTING_COORDINATOR: '베이지 오버핏 반팔 셔츠에 블랙 와이드슬랙스가잘 어울려. 면소재의 여유로운 셔츠 실루엣에깔끔한블랙 슬랙스로세련된 데이트룩이완성될거야. 셔츠 앞부분만살짝 넣어서자연스러운 느낌을 주고, 위쪽 버튼 1-2개 정도는풀어두는게좋아.블랙 옥스포드 슈즈로포멀함을 더하고브라운 가죽 서류가방으로 포인트를 더하고줘서세련된 분위기를 연출할수 있어. 여유로운 실루엣이지만 전체적으로 균형 잡힌 비율이라데이트 장소 어디든잘 어울릴 거야.',
            },
            StateName.EXPERT_SEARCH_CACHE: {},  # 조건 변경 시 캐시 초기화됨
            StateName.EXPERT_OFFSETS: {
                COLOR_EXPERT: 0,
                STYLE_ANALYST: 0,
                FITTING_COORDINATOR: 0,
            },
            StateName.SHOWN_IN_PRODUCT_IDS: set(),
        }

    # 시나리오 0: 최초 검색 (기본값)
    else:
        logger.info('최초 검색 - 새로운 state 생성')
        return {
            StateName.USER_MESSAGE: user_input.message,
            StateName.LAST_UPDATED_FIELDS: [],  # 빈 리스트 = 최초 검색
        }


def get_initial_state(agent: CompiledStateGraph, user_input: UserInput, current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    그래프 초기 state 생성

    Args:
        agent: 실행할 그래프
        user_input: 사용자 입력
        current_state: 현재 그래프의 state (있으면 병합, 없으면 새로 생성)
    """
    if (product_id := user_input.product_id) and len(product_id.split('_')) >= 2:
        user_input.product_id = product_id.split('_')[0]
    if agent.name == GraphName.SEARCH_SUBGRAPH:
        return _get_search_subgraph_initial_state(user_input, current_state)
    elif agent.name == GraphName.BEFORE_SEARCH or agent.name == GraphName.FASHION_SEARCH:
        return {
            StateName.MESSAGES: create_message(message_type='human', content=user_input.message),
            StateName.USER_MESSAGE: user_input.message,
            # StateName.USER_NAME: 'kkh',
            StateName.IS_PREDEFINED_TEMPLATE: user_input.is_predefined_template,
            StateName.PRODUCT_ID: user_input.product_id,
            StateName.CLOTH_SEARCH: current_state.get(StateName.CLOTH_SEARCH, ClothSearch()),
        }
    else:
        return {
            StateName.MESSAGES: create_message(message_type='human', content=user_input.message),
            StateName.USER_MESSAGE: user_input.message,
            StateName.EXPERTS_TO_RUN: [COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATOR],
            StateName.CURRENT_EXPERT: COLOR_EXPERT,
            # StateName.USER_NAME: 'kkh',
            StateName.IS_PREDEFINED_TEMPLATE: user_input.is_predefined_template,
            StateName.PRODUCT_ID: user_input.product_id,
            StateName.SHOWN_IN_PRODUCT_IDS: set(),
        }
    # elif agent.name == GraphName.SEARCH_SUBGRAPH:
    #     return _get_search_subgraph_initial_state(user_input, current_state)
    # elif agent.name == GraphName.BEFORE_SEARCH:
    #     return {

    #     }
    # else:
    #     return {
    #         StateName.MESSAGES: create_message(message_type='human', content=user_input.message),
    #         StateName.USER_MESSAGE: user_input.message,
    #         StateName.EXPERTS_TO_RUN: [COLOR_EXPERT, STYLE_ANALYST, FITTING_COORDINATER],
    #         StateName.CURRENT_EXPERT: COLOR_EXPERT,
    #         StateName.USER_NAME: 'kkh',
    #         StateName.IS_PREDEFINED_TEMPLATE: user_input.is_predefined_template,
    #         StateName.PRODUCT_ID: user_input.product_id,
    #     }


async def handle_user_input(user_input: UserInput, agent: CompiledStateGraph, **kwargs) -> tuple[dict[str, Any], UUID]:
    """
    user_input을 parsing 하고 , 현재 graph 상태가 interrupt 상태인지 확인 후 재개가 필요한 경우 Command 객체를 생성하여 "input" 키에 사용자가 입력한 메세지를 전달
    그렇지 않다면 "input" 키에 HumanMessage 객체에 사용자가 입력한 메세지 전달(문자열)
    Return kwargs for agent invocation and the run_id
    Args:
        user_input (UserInput): user input
        agent (CompiledStateGraph): agent

    Returns:
        tuple[dict[str, Any], str]: kwargs and run_id

    Raises:
        HTTPException: 입력 검증 실패 시
        ValueError: 필수 파라미터 누락 시
        Exception: 기타 예상치 못한 오류 시
    """  # noqa: E501
    try:
        run_id = uuid4()
        thread_id = user_input.thread_id
        user_id = user_input.user_id

        if not thread_id:
            logger.error('thread_id is required')
            raise ValueError('thread_id is required')

        if not user_id:
            logger.error('user_id is required')
            raise ValueError('user_id is required')

        configurable = {'thread_id': thread_id, 'user_id': user_id, 'model': user_input.model, **kwargs}
        callbacks = []

        # Initialize Langfuse CallbackHandler for Langchain (tracing)
        # if settings.MONITORING_TYPE == MonitoringType.LANGFUSE and settings.LANGFUSE_TRACING:
        #     langfuse_handler = CallbackHandler()
        #     callbacks.append(langfuse_handler)
        #     # langfuse_user_id , langfuse_session_id , langfuse_tags ,
        #     configurable.update({'metadata': {'langfuse_user_id': 'test'}})
        # elif settings.MONITORING_TYPE == MonitoringType.LANGSMITH and settings.LANGSMITH_TRACING:
        #     # Initialize Langsmith CallbackHandler for Langchain (tracing)
        #     langsmith_handler = LangsmithCallbackHandler()
        #     callbacks.append(langsmith_handler)

        if user_input.agent_config:
            if overlap := user_input.agent_config.keys() & configurable.keys():
                raise HTTPException(status_code=400, detail=f'Overlapping keys in agent_config: {overlap}')
            configurable.update(user_input.agent_config)

        config = RunnableConfig(configurable=configurable, callbacks=callbacks, run_id=run_id)
        # 현재 agent(CompiledStateGraph) 의 상태를 가져와서 interrupt 상태인지 확인
        try:
            state = await agent.aget_state(config)
        except Exception as e:
            logger.error(f'Failed to get agent state: {e}')
            raise ValueError(f'Failed to get agent state: {e}') from e

        interrupted_task = [task for task in state.tasks if hasattr(task, 'interrupt') and task.interrupts]

        input: Command | dict[str, Any]

        if interrupted_task:
            input = Command(resume=user_input.message)

        # TODO : 그래프의 이름에 따라서 초기 state 지정하기
        else:
            # 현재 state를 전달하여 기존 state 유지 여부 결정
            input = get_initial_state(agent, user_input, state.values if state else None)
            kwargs = {
                'input': input,
                'config': config,
            }
        return kwargs, run_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Unexpected error in handle_user_input: {e}')
        raise


# TODO : SSE 응답 결과도 서버에서 확인을 해야 해서 logging 추가
async def message_generator(user_input: StreamInput, agent: CompiledStateGraph, **kwargs) -> AsyncGenerator[str, None]:
    """Generate a stream of messages from the agent
    스트리밍 모드로 요청을 받았을 때, graph의 동작과정을 SSE 방식으로 전송하기 위한 비동기 제너레이터

    Args:
        user_input (StreamInput): user input
        agent (CompiledStateGraph): agent / agent_name에 맞는 CompiledStateGraph 객체
    """
    try:
        kwargs, run_id = await handle_user_input(user_input, agent, **kwargs)

    except Exception as e:
        logger.exception(f'Failed to handle user input: {e}')
        yield f'data: {json.dumps({"type": SSETypes.ERROR, "content": f"Failed to process user input: {str(e)}"})}\n\n'
        return

    try:
        async for stream_event in agent.astream(**kwargs, stream_mode=['updates', 'custom', 'messages'], subgraphs=True):
            if not isinstance(stream_event, tuple):
                continue

            # subgraphs = True 인 경우
            if len(stream_event) == 3:
                name_space, stream_mode_type, data = stream_event

            else:
                stream_mode_type, data = stream_event

            filtered_messages = []  # "updates" 모드에서 특정 노드의 결과를 포함할 메세지 리스트

            if stream_mode_type == 'updates':
                node_name = next(iter(data.keys()))
                if node_name in (NodeName.PRODUCT_INFO_AGENT, NodeName.CUSTOM_PRE_MODEL_NODE, NodeName.SEARCH_NODE):
                    logger.info(f'{node_name} 노드 메세지 skip')
                    continue
                # ===============================================================================================================
                # stream_mode == "updates" 인 경우 , data에는 특정 노드에서 업데이트 된 모든 정보를 dict로 담고 있음
                # => 여기서는 해당 dict로 부터 "messages" 키에 있는 메세지 리스트 만을 추출해서 처리
                # ===============================================================================================================
                # logger.info('stream_mode_type이 updates 인 경우 처리')

                if not isinstance(data, dict):
                    logger.warning(f'Expected dict for updates data, got {type(data)}')
                    continue

                for node_name, updates in data.items():
                    logger.info(f'state updated!\n node_name: {node_name}, updates: {updates}')
                    # subgraph의 prodcut_info_agent 노드 , custom_pre_model_node 노드애서의 업데이트 결과는 제외
                    # 특정 노드에서 업데이트 된 딕셔너리로 부터 messages 키에 있는 메세지 리스트 추출
                    if not isinstance(updates, dict):
                        logger.warning(f'Expected dict for node updates, got {type(updates)} for node {node_name}')
                        continue

                    updated_messages = updates.get('messages', [])

                    # node_name 이름에 따라 처리 (supervisor 노드의 도구 호출 결과가 필요한 경우만 처리, 나머지 중간노드 결과는 pass)
                    # if node_name == 'supervisor':
                    #     updated_messages = (
                    #         [updated_messages[-1]] if updated_messages and isinstance(updated_messages[-1], ToolMessage) else []
                    #     )  # tool 메세지만 필요

                    # updated_messages = []

                    filtered_messages.extend(updated_messages)

            # updates 모드에서 사용자에게 결과 보여줄 메세지 추가 가공 (튜플 형식으로 제공되는 메세지인 경우(ChatMessage)는 분리 후 AIMessage 객체로 변환??)
            processed_messages: list[AIMessage | BaseMessage] = []
            current_message: dict[str, Any] = {}
            for message in filtered_messages:
                try:
                    if isinstance(message, tuple):
                        key, value = message
                        # Store parts in temporary dict
                        current_message[key] = value
                    else:
                        # Add complete message if we have one in progress
                        if current_message:
                            try:
                                processed_messages.append(create_ai_message(current_message))
                            except Exception as e:
                                logger.exception(f'Error creating AI message from parts: {e}, parts: {current_message}')
                            current_message = {}
                        processed_messages.append(message)
                except Exception as e:
                    logger.exception(f'Error processing message: {e}, message: {message}')
                    continue

                # Add any remaining message parts
                if current_message:
                    try:
                        processed_messages.append(create_ai_message(current_message))
                    except Exception as e:
                        logger.exception(f'Error creating final AI message from parts: {e}, parts: {current_message}')

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "updates" 인 경우) => {"type": "message", "content": ChatMessage}
            # 1. langgraph에서 반환된 BaseMessage 객체를 ChatMessage 객체로 변환 (langchain_to_chat_message 함수 참고)
            # 2. ChatMessage 객체를 SSE 응답 형식으로 변환
            # 사용자가 입력한 메세지는 다시 전송하지 않음.
            # ===============================================================================================================
            for message in processed_messages:
                try:
                    if isinstance(message, BaseMessage):
                        chat_message = langchain_to_chat_message(message)
                        # chat_message.run_id = str(run_id)
                    else:
                        d = {
                            'type': 'ai',
                            'content': message,
                        }
                        chat_message = ChatMessage.model_validate(d)
                except Exception as e:
                    logger.exception(f'Error parsing message: {e}, message: {message}')
                    yield f'data: {json.dumps({"type": SSETypes.ERROR, "content": f"Error parsing message: {str(e)}"})}\n\n'
                    continue

                # 사용자가 입력한 메세지를 다시 전송하는 것을 방지
                if chat_message.type == 'human' and chat_message.content == user_input.message:
                    continue
                content = chat_message.model_dump()
                logger.info(f'SSE response => type : {SSETypes.MESSAGE}, content : {content}')
                yield f'data: {json.dumps({"type": SSETypes.MESSAGE, "content": content})}\n\n'

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "messages" 인 경우) => {"type": "token", "content": ChatMessage}
            # ===============================================================================================================
            if stream_mode_type == 'messages':
                try:
                    if not user_input.stream_tokens:
                        continue
                    msg, metadata = data
                    if SKIP_STREAM in metadata.get('tags', []):
                        continue

                    # ===============================================================================================================
                    # 특정 노드에서 BaseMessage 형태로 반환하는 경우 "updates" 모드와 "messages" 모드에서 모두 반환.
                    # 따라서 messages 모드에서는 AIMessageChunk 형태가 아닌 경우는 Drop 처리.
                    # ===============================================================================================================
                    if not isinstance(msg, AIMessageChunk):
                        continue
                    content = remove_tool_calls(msg.content)
                    if content:
                        # Empty content in the context of OpenAI usually means
                        # that the model is asking for a tool to be invoked.
                        # So we only print non-empty content.
                        content = convert_message_content_to_string(content)
                        logger.info(f'SSE response => type : {SSETypes.TOKEN}, content : {content}')
                        yield f'data: {json.dumps({"type": SSETypes.TOKEN, "content": content})}\n\n'
                except Exception as e:
                    logger.exception(f'Error processing messages stream: {e}')
                    yield f'data: {json.dumps({"type": SSETypes.ERROR, "content": f"Error processing messages: {str(e)}"})}\n\n'

            # ===============================================================================================================
            # stream_mode_type == "custom" 인 경우 처리 (외부 LLM 스트리밍 결과 처리 및 writer를 이용해서 출력을 내보내는 경우 처리)
            # 실제 데이터는 python dict 형식으로 {"type": "token" | "status" , "content": "데이터"} 형식으로 전달됨
            # 이때 content 데이터는 StatusUpdate 모델 형식으로 전달됨
            # ===============================================================================================================
            if stream_mode_type == 'custom':
                try:
                    if not isinstance(data, dict) or 'type' not in data or 'content' not in data:
                        logger.warning(f'Invalid custom data format: {data}')
                        continue

                    event_type, content = data['type'], data['content']
                    match event_type:
                        case SSETypes.TOKEN:
                            logger.info(f'SSE response => type : {SSETypes.TOKEN} , content : {content}')
                            yield f'data: {json.dumps({"type": SSETypes.TOKEN, "content": content})}\n\n'
                        case SSETypes.STATUS:
                            logger.info(f'SSE response => type : {SSETypes.STATUS} , content : {content}')
                            yield f'data: {json.dumps({"type": SSETypes.STATUS, "content": content})}\n\n'
                        case _:
                            logger.warning(f'Unknown custom type: {event_type}')
                except Exception as e:
                    logger.exception(f'Error processing custom stream: {e}')
                    yield f'data: {json.dumps({"type": SSETypes.ERROR, "content": f"Error processing custom stream: {str(e)}"})}\n\n'
    except asyncio.CancelledError:
        logger.info('Message generation cancelled by client')
        raise
    except Exception as e:
        logger.exception(f'Critical error in message generator: {e}')
        yield f'data: {json.dumps({"type": SSETypes.ERROR, "content": f"Critical error: {str(e)}"})}\n\n'
    finally:
        logger.info('Message generation completed')
        yield f'data: {json.dumps({"type": SSETypes.END, "content": ""})}\n\n'


async def show_graph_stream(
    graph: CompiledStateGraph, input: dict, config: RunnableConfig, user_input: UserInput, return_result: bool = False
) -> None | ChatMessage:
    try:
        async for stream_event in graph.astream(input=input, config=config, stream_mode=['updates', 'custom', 'messages'], subgraphs=True):
            if not isinstance(stream_event, tuple):
                continue

            # subgraphs = True 인 경우
            if len(stream_event) == 3:
                name_space, stream_mode_type, data = stream_event

            else:
                stream_mode_type, data = stream_event

            filtered_messages = []  # "updates" 모드에서 특정 노드의 결과를 포함할 메세지 리스트

            if stream_mode_type == 'updates':
                # ===============================================================================================================
                # stream_mode == "updates" 인 경우 , data에는 특정 노드에서 업데이트 된 모든 정보를 dict로 담고 있음
                # => 여기서는 해당 dict로 부터 "messages" 키에 있는 메세지 리스트 만을 추출해서 처리
                # ===============================================================================================================
                if not isinstance(data, dict):
                    logger.warning(f'Expected dict for updates data, got {type(data)}')
                    continue

                for node_name, updates in data.items():
                    # 특정 노드에서 업데이트 된 딕셔너리로 부터 messages 키에 있는 메세지 리스트 추출
                    if not isinstance(updates, dict):
                        logger.warning(f'Expected dict for node updates, got {type(updates)} for node {node_name}')
                        continue

                    if return_result and node_name == 'run_expert_evaluation':
                        current_expert = input.get('current_expert', '')
                        return updates.get('expert_opinions', '').get(current_expert, '')

                    updated_messages = updates.get('messages', [])
                    filtered_messages.extend(updated_messages)

                # updates 모드에서 사용자에게 결과 보여줄 메세지 추가 가공 (튜플 형식으로 제공되는 메세지인 경우(ChatMessage)는 분리 후 AIMessage 객체로 변환??)
            processed_messages: list[AIMessage | BaseMessage] = []
            current_message: dict[str, Any] = {}
            for message in filtered_messages:
                try:
                    if isinstance(message, tuple):
                        key, value = message
                        # Store parts in temporary dict
                        current_message[key] = value
                    else:
                        # Add complete message if we have one in progress
                        if current_message:
                            try:
                                processed_messages.append(create_ai_message(current_message))
                            except Exception as e:
                                logger.exception(f'Error creating AI message from parts: {e}, parts: {current_message}')
                            current_message = {}
                        processed_messages.append(message)
                except Exception as e:
                    logger.exception(f'Error processing message: {e}, message: {message}')
                    continue

                # Add any remaining message parts
                if current_message:
                    try:
                        processed_messages.append(create_ai_message(current_message))
                    except Exception as e:
                        logger.exception(f'Error creating final AI message from parts: {e}, parts: {current_message}')

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "updates" 인 경우) => {"type": "message", "content": ChatMessage}
            # 1. langgraph에서 반환된 BaseMessage 객체를 ChatMessage 객체로 변환 (langchain_to_chat_message 함수 참고)
            # 2. ChatMessage 객체를 SSE 응답 형식으로 변환
            # 사용자가 입력한 메세지는 다시 전송하지 않음.
            # ===============================================================================================================
            for message in processed_messages:
                try:
                    if isinstance(message, BaseMessage):
                        chat_message = langchain_to_chat_message(message)
                        # chat_message.run_id = str(run_id)
                    else:
                        data = {
                            'type': 'ai',
                            'content': message,
                        }
                        chat_message = ChatMessage.model_validate(data)
                except Exception as e:
                    logger.error(f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error parsing message: {str(e)}"})}\n\n')
                    continue

                # 사용자가 입력한 메세지를 다시 전송하는 것을 방지
                print()
                if chat_message.type == 'human' and chat_message.content == user_input.message:
                    continue
                logger.info(f'data: {json.dumps({"type": SSETypes.MESSAGE.value, "content": chat_message.model_dump()})}\n\n')

                if return_result and chat_message and isinstance(chat_message, ChatMessage):
                    return chat_message

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "messages" 인 경우) => {"type": "token", "content": ChatMessage}
            # ===============================================================================================================
            if stream_mode_type == 'messages':
                try:
                    msg, metadata = data
                    if 'skip_stream' in metadata.get('tags', []):
                        continue

                    # ===============================================================================================================
                    # 특정 노드에서 BaseMessage 형태로 반환하는 경우 "updates" 모드와 "messages" 모드에서 모두 반환.
                    # 따라서 messages 모드에서는 AIMessageChunk 형태가 아닌 경우는 Drop 처리.
                    # ===============================================================================================================
                    if not isinstance(msg, AIMessageChunk):
                        continue
                    content = remove_tool_calls(msg.content)
                    if content:
                        # Empty content in the context of OpenAI usually means
                        # that the model is asking for a tool to be invoked.
                        # So we only print non-empty content.
                        logger.info(
                            f'SSE response => data : {json.dumps({"type": SSETypes.TOKEN.value, "content": convert_message_content_to_string(content)})}\n\n'
                        )
                except Exception as e:
                    logger.error(
                        f'SSE response => data : {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing messages: {str(e)}"})}\n\n'
                    )

            # ===============================================================================================================
            # stream_mode_type == "custom" 인 경우 처리 (외부 LLM 스트리밍 결과 처리 및 writer를 이용해서 출력을 내보내는 경우 처리)
            # 실제 데이터는 python dict 형식으로 {"type": "token" | "status" , "content": "데이터"} 형식으로 전달됨
            # 이때 content 데이터는 StatusUpdate 모델 형식으로 전달됨
            # ===============================================================================================================
            if stream_mode_type == 'custom':
                try:
                    if not isinstance(data, dict) or 'type' not in data or 'content' not in data:
                        logger.warning(f'Invalid custom data format: {data}')
                        continue

                    event_type, content = data['type'], data['content']
                    logger.debug(f'stream_mode_type: custom인 경우 : {event_type} , {content}')
                    match event_type:
                        case SSETypes.TOKEN.value:
                            logger.info(f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": content})}\n\n')
                        case SSETypes.STATUS.value:
                            logger.info(f'data: {json.dumps({"type": SSETypes.STATUS.value, "content": content})}\n\n')
                        case _:
                            logger.warning(f'Unknown custom type: {event_type}')
                except Exception as e:
                    logger.error(f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing custom stream: {str(e)}"})}\n\n')

    except Exception as e:
        logger.error(f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Critical error: {str(e)}"})}\n\n')

    finally:
        logger.info(f'data: {json.dumps({"type": SSETypes.END.value, "content": ""})}\n\n')


async def test_message_generator(agent: CompiledStateGraph, input: dict, config: RunnableConfig, user_input: UserInput) -> AsyncGenerator[str, None]:
    """Generate a stream of messages from the agent
    스트리밍 모드로 요청을 받았을 때, graph의 동작과정을 SSE 방식으로 전송하기 위한 비동기 제너레이터

    Args:
        user_input (StreamInput): user input
        agent (CompiledStateGraph): agent / agent_name에 맞는 CompiledStateGraph 객체
    """
    try:
        async for stream_event in agent.astream(input=input, config=config, stream_mode=['updates', 'custom', 'messages'], subgraphs=True):
            if not isinstance(stream_event, tuple):
                continue

            # subgraphs = True 인 경우
            if len(stream_event) == 3:
                name_space, stream_mode_type, data = stream_event

            else:
                stream_mode_type, data = stream_event

            filtered_messages = []  # "updates" 모드에서 특정 노드의 결과를 포함할 메세지 리스트

            if stream_mode_type == 'updates':
                # ===============================================================================================================
                # stream_mode == "updates" 인 경우 , data에는 특정 노드에서 업데이트 된 모든 정보를 dict로 담고 있음
                # => 여기서는 해당 dict로 부터 "messages" 키에 있는 메세지 리스트 만을 추출해서 처리
                # ===============================================================================================================
                if not isinstance(data, dict):
                    logger.warning(f'Expected dict for updates data, got {type(data)}')
                    continue

                for node_name, updates in data.items():
                    # 특정 노드에서 업데이트 된 딕셔너리로 부터 messages 키에 있는 메세지 리스트 추출
                    if not isinstance(updates, dict):
                        logger.warning(f'Expected dict for node updates, got {type(updates)} for node {node_name}')
                        continue

                    updated_messages = updates.get('messages', [])

                    # node_name 이름에 따라 처리 (supervisor 노드의 도구 호출 결과가 필요한 경우만 처리, 나머지 중간노드 결과는 pass)
                    # if node_name == 'supervisor':
                    #     if isinstance(updated_messages[-1], ToolMessage):  # tool 메세지만 필요
                    #         updated_messages = [updated_messages[-1]]
                    #     else:
                    #         # 중간 노드 메세지 제거
                    #         updated_messages = []

                    # if node_name in ('research_expert', 'math_expert'):
                    #     # 중간 노드 메세지 제거
                    #     updated_messages = []

                    filtered_messages.extend(updated_messages)

            # updates 모드에서 사용자에게 결과 보여줄 메세지 추가 가공 (튜플 형식으로 제공되는 메세지인 경우(ChatMessage)는 분리 후 AIMessage 객체로 변환??)
            processed_messages: list[AIMessage | BaseMessage] = []
            current_message: dict[str, Any] = {}
            for message in filtered_messages:
                try:
                    if isinstance(message, tuple):
                        key, value = message
                        # Store parts in temporary dict
                        current_message[key] = value
                    else:
                        # Add complete message if we have one in progress
                        if current_message:
                            try:
                                processed_messages.append(create_ai_message(current_message))
                            except Exception as e:
                                logger.error(f'Error creating AI message from parts: {e}, parts: {current_message}', exc_info=True)
                            current_message = {}
                        processed_messages.append(message)
                except Exception as e:
                    logger.error(f'Error processing message: {e}, message: {message}', exc_info=True)
                    continue

                # Add any remaining message parts
                if current_message:
                    try:
                        processed_messages.append(create_ai_message(current_message))
                    except Exception as e:
                        logger.error(f'Error creating final AI message from parts: {e}, parts: {current_message}', exc_info=True)

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "updates" 인 경우) => {"type": "message", "content": ChatMessage}
            # 1. langgraph에서 반환된 BaseMessage 객체를 ChatMessage 객체로 변환 (langchain_to_chat_message 함수 참고)
            # 2. ChatMessage 객체를 SSE 응답 형식으로 변환
            # 사용자가 입력한 메세지는 다시 전송하지 않음.
            # ===============================================================================================================
            for message in processed_messages:
                try:
                    if isinstance(message, BaseMessage):
                        chat_message = langchain_to_chat_message(message)
                        # chat_message.run_id = str(run_id)
                    else:
                        data = {
                            'type': 'ai',
                            'content': message,
                        }
                        chat_message = ChatMessage.model_validate(data)
                except Exception as e:
                    logger.exception(f'Error parsing message: {e}, message: {message}')
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error parsing message: {str(e)}"})}\n\n'
                    continue

                # 사용자가 입력한 메세지를 다시 전송하는 것을 방지
                if chat_message.type == 'human' and chat_message.content == user_input.message:
                    continue
                data = chat_message.model_dump()
                logger.info(f'type: {SSETypes.MESSAGE} , content: {data}')
                yield f'data: {json.dumps({"type": SSETypes.MESSAGE, "content": data})}\n\n'

            # ===============================================================================================================
            # SSE 응답에 대한 처리 (stream_mode_type == "messages" 인 경우) => {"type": "token", "content": ChatMessage}
            # ===============================================================================================================
            if stream_mode_type == 'messages':
                msg = None
                try:
                    msg, metadata = data
                    if 'skip_stream' in metadata.get('tags', []):
                        continue

                    # ===============================================================================================================
                    # 특정 노드에서 BaseMessage 형태로 반환하는 경우 "updates" 모드와 "messages" 모드에서 모두 반환.
                    # 따라서 messages 모드에서는 AIMessageChunk 형태가 아닌 경우는 Drop 처리.
                    # ===============================================================================================================
                    if not isinstance(msg, AIMessageChunk):
                        continue
                    content = remove_tool_calls(msg.content)
                    if content:
                        # Empty content in the context of OpenAI usually means
                        # that the model is asking for a tool to be invoked.
                        # So we only print non-empty content.
                        data = convert_message_content_to_string(content)
                        logger.info(f'type: {SSETypes.TOKEN} , content: {data}')
                        yield f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": data})}\n\n'
                except Exception as e:
                    logger.exception(f'Error processing messages stream | content : {msg} ,  error: {e}')
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing messages: {str(e)}"})}\n\n'

            # ===============================================================================================================
            # stream_mode_type == "custom" 인 경우 처리 (외부 LLM 스트리밍 결과 처리 및 writer를 이용해서 출력을 내보내는 경우 처리)
            # 실제 데이터는 python dict 형식으로 {"type": "token" | "status" , "content": "데이터"} 형식으로 전달됨
            # 이때 content 데이터는 StatusUpdate 모델 형식으로 전달됨
            # ===============================================================================================================
            if stream_mode_type == 'custom':
                event_type, content = None, None
                try:
                    if not isinstance(data, dict) or 'type' not in data or 'content' not in data:
                        logger.warning(f'Invalid custom data format: {data}')
                        continue

                    event_type, content = data['type'], data['content']
                    match event_type:
                        case SSETypes.TOKEN.value:
                            logger.info(f'type: {SSETypes.TOKEN} , content: {content}')
                            yield f'data: {json.dumps({"type": SSETypes.TOKEN.value, "content": content})}\n\n'
                        case SSETypes.STATUS.value:
                            logger.info(f'type: {SSETypes.STATUS} , content: {content}')
                            yield f'data: {json.dumps({"type": SSETypes.STATUS.value, "content": content})}\n\n'
                        case _:
                            logger.warning(f'Unknown custom type: {type} , content: {content}')
                except Exception as e:
                    logger.exception(f'Error processing custom stream | content : {content} , error: {e}')
                    yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Error processing custom stream: {str(e)}"})}\n\n'

    except Exception as e:
        logger.exception(f'Critical error in message generator: {e}')
        yield f'data: {json.dumps({"type": SSETypes.ERROR.value, "content": f"Critical error: {str(e)}"})}\n\n'
    finally:
        logger.info('Message generation completed')
        yield f'data: {json.dumps({"type": SSETypes.END.value, "content": ""})}\n\n'
