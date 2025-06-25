from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage , SystemMessage
from langchain_core.prompts import ChatPromptTemplate 
from dotenv import load_dotenv
load_dotenv()

model_names_only= [
    "embedding-gecko-001",
    "gemini-1.0-pro-vision-latest",
    "gemini-pro-vision",
    "gemini-1.5-pro-latest",
    "gemini-1.5-pro-002",
    "gemini-1.5-pro",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash-8b-001",
    "gemini-1.5-flash-8b-latest",
    "gemini-2.5-pro-exp-03-25",
    "gemini-2.5-pro-preview-03-25",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.5-flash",
    "gemini-2.5-flash-preview-04-17-thinking",
    "gemini-2.5-flash-lite-preview-06-17",
    "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-pro-preview-06-05",
    "gemini-2.5-pro",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-exp-image-generation",
    "gemini-2.0-flash-lite-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-preview-image-generation",
    "gemini-2.0-flash-lite-preview-02-05",
    "gemini-2.0-flash-lite-preview",
    "gemini-2.0-pro-exp",
    "gemini-2.0-pro-exp-02-05",
    "gemini-exp-1206",
    "gemini-2.0-flash-thinking-exp-01-21",
    "gemini-2.0-flash-thinking-exp",
    "gemini-2.0-flash-thinking-exp-1219",
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
    "learnlm-2.0-flash-experimental",
    "gemma-3-1b-it",
    "gemma-3-4b-it",
    "gemma-3-12b-it",
    "gemma-3-27b-it",
    "gemma-3n-e4b-it",
    "embedding-001",
    "text-embedding-004",
    "gemini-embedding-exp-03-07",
    "gemini-embedding-exp",
    "aqa"
  ],

MODEL_NAME = {
    "embedding" : [
        "embedding-001",
        "text-embedding-004",
        "gemini-embedding-exp-03-07",
        "gemini-embedding-exp",
        
    ],
    "1.5-pro" : [
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro",
    ],
    "1.5-flash" : [
        "gemini-1.5-flash",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-8b-001",
        "gemini-1.5-flash-8b-latest",

    ],
    "2.0-flash" : [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-2.0-flash-lite-preview",
        "gemini-2.0-flash-thinking-exp-01-21",
        "gemini-2.0-flash-thinking-exp",
    ],
    "2.0-pro" : [
        "gemini-2.0-pro-exp",
        "gemini-2.0-pro-exp-02-05",
    ],
    "2.5-flash" : [
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-flash",
        "gemini-2.5-flash-preview-04-17-thinking",
        "gemini-2.5-flash-lite-preview-06-17",
    ],
    "2.5-pro" : [
        "gemini-2.5-pro-exp-03-25",
        "gemini-2.5-pro-preview-03-25",
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.5-pro-preview-06-05",
        "gemini-2.5-pro",
    ],
}


# 기존 테스트 코드
print("🧪 LangChain으로 모델 테스트...")
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-8b-001",
        temperature=0,
    )
    
    result = llm.invoke("you must answer 'yes' or 'no'")
    print(f"✅ 모델 응답: {result.content}")
except Exception as e:
    print(f"❌ 모델 테스트 오류: {e}")
    
