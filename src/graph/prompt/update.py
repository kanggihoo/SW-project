from langchain_core.prompts import ChatPromptTemplate

"""
Examples:
- "다른 거 보여줘" / "다음 보여줘" / "다른 옷" → {{tpo: null, color: null, style: null}}
- "비슷한 거 더" / "다른 추천" → {{tpo: null, color: null, style: null}}
- "파란색 말고 빨간색으로" → {{color: "빨간색", tpo: null, style: null}}
- "청바지 대신 슬랙스" → {{style: "슬랙스", tpo: null, color: null}}
- "비슷한 거" / "이런 스타일" → {{tpo: null, color: null, style: null}}
- "더 밝은 색" → Interpret as color modification
- "좀 더 캐주얼하게" → {{style: "캐주얼", tpo: null, color: null}}
"""

SYSTEM_PROMPT = """
You are an expert at updating search criteria based on user feedback.
The user has already seen search results and is asking for a modification.
Update the existing `ClothSearch` criteria based on the user's latest message.
Only change the fields the user explicitly mentioned.

**Critical Classification:**
1. If the user asks for "다른 거", "다음", "another", "more" without specifying changes
   → Return ALL fields as `null` (this triggers cache cycling)
2. Only update fields the user explicitly mentioned changing

Examples:
- "다른 거 보여줘" → {{tpo: null, color: null, style: null}}
- "파란색 말고 빨간색으로" → {{color: "빨간색", tpo: null, style: null}}

Existing Search Criteria:
{existing_search_criteria}
"""

update_prompt = ChatPromptTemplate.from_messages(
    [
        ('system', SYSTEM_PROMPT),
        ('user', '{user_message}'),
    ]
)
