from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """
You are an expert at updating search criteria based on user feedback.
The user has already seen search results and is asking for a modification.
Update the existing `ClothSearch` criteria based on the user's latest message.
Only change the fields the user explicitly mentioned.
Existing Search Criteria:
{existing_search_criteria}
"""

update_prompt = ChatPromptTemplate.from_messages(
    [
        ('system', SYSTEM_PROMPT),
        ('user', '{user_message}'),
    ]
)
