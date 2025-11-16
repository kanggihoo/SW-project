from enum import StrEnum

CONFIG = 'configurable'
HTTP_SESSION = 'http_session'
SEARCH_SERVICE = 'search_service'
COLOR_EXPERT = 'color_expert'
STYLE_ANALYST = 'style_analyst'
FITTING_COORDINATOR = 'fitting_coordinator'
SHOW_CACHED = '__SHOW_CACHED__'
SKIP_STREAM = 'skip_stream'

HISTORY_WINDOW_SMALL = 3  # 짧은 컨텍스트
HISTORY_WINDOW_MEDIUM = 5  # 중간 컨텍스트
HISTORY_WINDOW_LARGE = 7  # 긴 컨텍스트


class GraphName(StrEnum):
    """Graph name"""

    LLM_SEARCH = 'llm_search'
    LLM_SEARCH_ONCE = 'llm_search_once'
    FASHION_SEARCH = 'fashion_search'
    SEARCH_SUBGRAPH = 'search_subgraph'
    CHATBOT = 'chatbot'
    BEFORE_SEARCH = 'before_search'


class SSETypes(StrEnum):
    """SSE 타입"""

    STATUS = 'status'
    MESSAGE = 'message'
    TOKEN = 'token'
    ERROR = 'error'
    END = '[DONE]'


class MessageTypes(StrEnum):
    """Message type"""

    AI = 'ai'
    HUMAN = 'human'
    TOOL = 'tool'
    CUSTOM = 'custom'


class ExternalLLMNames(StrEnum):
    """Agent name"""

    COLOR_ANALYST = 'color_analyst'
    STYLE_ANALYST = 'style_analyst'
    FASHION_ANALYST = 'fashion_analyst'


class StatusUpdateTypes(StrEnum):
    """Status update type"""

    START = 'start'
    END = 'end'
    ERROR = 'error'


class IntentTypes(StrEnum):
    """Intent type"""

    DIRECT_SEARCH = 'direct_search'
    INFO_QA = 'info_qa'
    SEARCH_REFINEMENT = 'search_refinement'
    CHATBOT = 'chatbot'
    INAPPROPRIATE_QUERY = 'inappropriate_query'
    UNCLEAR = 'unclear'


class NodeName(StrEnum):
    # 의도 분류 관련 노드
    CLASSIFY_INTENT = 'classify_intent'
    RECLASSIFY_INTENT = 'reclassify_intent'
    HANDLE_INAPPROPRIATE = 'handle_inappropriate'
    CHATBOT = 'chatbot'
    INFO_QA = 'info_qa'

    # 정보 수집 및 업데이트 관련
    INFORMATION_GATHERING = 'information_gathering'
    INFORMATION_UPDATE = 'information_update'

    # 검색 메시지 준비 관련 노드
    PREPARE_SEARCH_MESSAGE = 'prepare_search_message'
    # search_subgraph 관련 노드
    SEARCH_NODE = 'search_node'

    PREPARE_TEMPLATE_SEARCH = 'prepare_template_search'  # ??
    POP_NEXT_EXPERT = 'pop_next_expert'
    RUN_EXPERT_EVALUATION = 'run_expert_evaluation'
    VECTOR_SEARCH = 'vector_search'
    GET_CACHED_ITEM = 'get_cached_item'
    SEND_REFINEMENT_PROMPT = 'send_refinement_prompt'
    PREPARE_CACHE_CYCLE = 'prepare_cache_cycle'
    PREPARE_SEARCH_CYCLE = 'prepare_search_cycle'

    # 상품 정보 조회 관련 노드
    PRODUCT_INFO_AGENT = 'product_info_agent'

    # 테스트 관련 노드
    TEST_SEARCH_NODE = 'test_search_node'

    # 상품 정보 조회 관련 노드
    CUSTOM_PRE_MODEL_NODE = 'custom_pre_model_node'


class StateName(StrEnum):
    MESSAGES = 'messages'
    CLOTH_SEARCH = 'cloth_search'
    IS_INFO_GATHERING_COMPLETE = 'is_info_gathering_complete'
    PRODUCT_ID = 'product_id'
    INTENT = 'intent'
    USER_MESSAGE = 'user_message'
    LAST_UPDATED_FIELDS = 'last_updated_fields'
    EXPERT_OPINIONS = 'expert_opinions'
    EXPERTS_TO_RUN = 'experts_to_run'
    CURRENT_EXPERT = 'current_expert'

    EXPERT_OFFSETS = 'expert_offsets'
    EXPERT_SEARCH_CACHE = 'expert_search_cache'
    SHOWN_IN_PRODUCT_IDS = 'shown_in_product_ids'
    CACHE_CYCLABLE = 'cache_cyclable'

    USER_NAME = 'user_name'
    IS_PREDEFINED_TEMPLATE = 'is_predefined_template'
    IS_UNCLEAR_FALLBACK = 'is_unclear_fallback'


class RouterReturnNames(StrEnum):
    # master router에서 사용
    CLASSIFY_INTENT = 'classify_intent'
    CUSTOM_PRE_MODEL_NODE = 'custom_pre_model_node'
    PREPARE_TEMPLATE_SEARCH = 'prepare_template_search'

    INFORMATION_GATHERING = 'information_gathering'
    INFORMATION_UPDATE = 'information_update'
    HANDLE_INAPPROPRIATE = 'handle_inappropriate'
    CHATBOT = 'chatbot'
    INFO_QA = 'info_qa'

    START_EXPERT_LOOP = 'start_expert_loop'
    GO_CACHED_LOOP = 'go_cached_loop'
    GET_CACHED_ITEM = 'get_cached_item'
    RUN_EXPERT_EVALUATION = 'run_expert_evaluation'
    SEND_REFINEMENT_PROMPT = 'send_refinement_prompt'

    # 검색 메시지 준비 라우팅
    PREPARE_SEARCH_MESSAGE = 'prepare_search_message'

    # search_subgraph 에서 초기 라우팅
    PREPARE_CACHE_CYCLE = 'prepare_cache_cycle'
    PREPARE_SEARCH_CYCLE = 'prepare_search_cycle'

    # 캐시 준비 후 라우팅
    CONTINUE_LOOP = 'continue_loop'
    NO_MORE_ITEMS = 'no_more_items'
