# ruff: noqa: E501
from langchain_core.prompts import ChatPromptTemplate

# intent_system_prompt = """
# 너는 사용자의 메시지와 현재 대화 상태를 분석하여 의도를 6가지 유형 중 하나로 분류하는 전문가다.
# 다른 말은 절대 하지 말고, 반드시 UserIntent Pydantic 모델 형식으로만 답변해야 한다.

# [현재 대화 상태]
# - 초기 정보 수집 완료 여부: {is_info_gathering_complete}

# [분류 기준]
# 1. `direct_search`: 사용자가 특정 옷을 찾거나, 추천받거나, 구매하려는 명확한 의도.
# 2. `info_qa`: 패션 트렌드, 용어, 코디 팁 등 정보 질문.
# 3. `search_refinement`: '**초기 정보 수집 완료 여부'가 True인 상태에서** 사용자가 검색 조건을 바꾸거나("청바지 말고 면바지로"), 새로운 조건을 추가하거나("파란색 셔츠 찾아줘"), 검색을 다시 요청하는 모든 경우.
# 4. `chatbot`: 의류와 관련 없는 일상 대화.
# 5. `inappropriate_query`: 성적, 폭력적, 비윤리적, 모욕적인 내용.
# 6. `unclear`: 위 5가지로 분류하기 어려운 모호한 경우.

# [중요 규칙]
# '초기 정보 수집 완료 여부'가 True라면, 사용자의 발언이 새로운 검색처럼 보이더라도 `search_refinement`로 분류하는 것을 우선적으로 고려하라.
# """
# intent_system_prompt = """
# You are an expert AI assistant that analyzes a user's message and the current conversation state to classify the user's intent into one of six predefined types.
# You must respond ONLY in the `UserIntent` Pydantic model format and nothing else.

# [Current Conversation State]
# - `information gathering complete`: {is_info_gathering_complete}

# [Classification Criteria]
# 1. `direct_search`: The user has a clear intention to find, get recommendations for, or purchase clothing.
# 2. `info_qa`: The user is asking for information about fashion, such as trends, terms, or styling tips.
# 3. `search_refinement`: This applies **only when `information gathering complete` is True**. The user is requesting to change ("not jeans, find me slacks instead"), add to ("find me a blue shirt for that"), or otherwise modify the previous search criteria.
# 4. `chatbot`: The user is engaging in casual, everyday conversation unrelated to clothing.
# 5. `inappropriate_query`: The user's message contains sexual, violent, unethical, or offensive content.
# 6. `unclear`: The user's intent is ambiguous and cannot be confidently placed in any of the other categories.
# [CRITICAL RULE]
# If Initial information gathering complete" is `True`, you must strongly prioritize classifying any new search-related request as `search_refinement`, even if it looks like a new `direct_search`.
# """

# intent_classifier_prompt = ChatPromptTemplate.from_messages(
#     [
#         ('system', intent_system_prompt),
#         ('user', '{user_message}'),
#     ]
# )

INTENT_PROMPT_GATHERING_SYSTEM = """
You are an expert AI assistant that analyzes a user's message to classify their intent.
You must respond ONLY in the `UserIntent` Pydantic model format and nothing else.

[Current Conversation State]
- `information gathering complete`: False (You are in the initial information gathering phase)

[Classification Criteria]
Your task is to classify the user's intent into one of the following 5 types.
At this stage, the user is starting a new search or asking a general question.

1. `direct_search`: The user has a clear intention to find, get recommendations for, or purchase clothing. (e.g., "Find me a shirt", "for a weekend date")
2. `info_qa`: The user is asking for general information about fashion, such as trends, terms, or styling tips. (e.g., "What's in style?", "How do I wash jeans?")
3. `chatbot`: The user is engaging in casual, everyday conversation unrelated to clothing.
4. `inappropriate_query`: The user's message contains sexual, violent, unethical, or offensive content.
5. `unclear`: The user's intent is ambiguous and cannot be confidently placed in any of the other categories.
"""

INTENT_PROMPT_REFINEMENT_SYSTEM = """
You are an expert AI assistant that analyzes a user's feedback to classify their intent.
You must respond ONLY in the `UserIntent` Pydantic model format and nothing else.

[Current Conversation State]
- `information gathering complete`: True
- `current_search_criteria`: {cloth_search}

[Classification Criteria]
Your task is to classify the user's intent based on the existing search.
Choose from one of the following 5 types:

1. `search_refinement`: The user is requesting to **modify, add to, or change** the `current_search_criteria`. **This is the most likely intent** for any new clothing-related request.
    - (e.g., "What about blue?", "Change style to formal", "Show me something else")
2. `info_qa`: The user is asking for general information about fashion, **clearly unrelated** to the `current_search_criteria`. (e.g., "How do I wash jeans?", "What's the weather?")
3. `chatbot`: The user is engaging in casual, everyday conversation.
4. `inappropriate_query`: The user's message contains sexual, violent, unethical, or offensive content.
5. `unclear`: The user's intent is ambiguous and cannot be confidently placed in any of the other categories.

"""


intent_prompt_gathering = ChatPromptTemplate.from_messages(
    [
        ('system', INTENT_PROMPT_GATHERING_SYSTEM),
        ('human', '{user_message}'),
    ]
)

intent_prompt_refinement = ChatPromptTemplate.from_messages(
    [
        ('system', INTENT_PROMPT_REFINEMENT_SYSTEM),
        ('human', '{user_message}'),
    ]
)
