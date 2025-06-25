from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
import base64
from dotenv import load_dotenv
import os

load_dotenv()

# 1. 이미지 파일 → base64 변환
def image_to_base64(path):
    with open(path, "rb") as f:
        image_bytes = f.read()
    return base64.b64encode(image_bytes).decode("utf-8")

def extract_text_from_image(image_path):
    # Gemini 2.0 Flash 모델 설정
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-001",
        temperature=0,  # 정확한 텍스트 추출을 위해 temperature를 0으로 설정
    )
    
    # 이미지를 base64로 변환
    image_b64 = image_to_base64(image_path)
    
    # 프롬프트 구성
    prompt = [
        SystemMessage(content=
                      """You are a precise OCR assistant. Extract ONLY visible Korean or English text from the image.
        - If there is no text visible in the image, return an empty string.
        - Do not describe the image or add any additional information.
        - Only return the exact text found in the image.
        - Preserve the original formatting and line breaks of the text."""),
        HumanMessage(content=[
            {
                "type": "text",
                "text": "Extract only Korean or English text from this image. If no text is found, return an empty string:"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }
            }
        ])
    ]
    
    # 실행
    response = llm.invoke(prompt)
    return response.content.strip()

if __name__ == "__main__":
    image_path = "split_segment_1_4.png"  # 분석할 이미지 경로
    extracted_text = extract_text_from_image(image_path)
    if extracted_text:
        print("추출된 텍스트:")

        print(extracted_text)
    else:
        print("이미지에서 텍스트를 찾을 수 없습니다.")
