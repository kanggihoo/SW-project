from caption.prompt.color_analysis_prompt_template import ColorCaptionPrompt 
from caption.prompt.image_deep_captioning_prompt_template import DeepImageCaptionPrompt
from caption.prompt.text_image_ocr_prompt_template import TextImageOCRPrompt
from caption.fashion_caption_generator import FashionCaptionGenerator
from caption.config import  LLMInputKeys
from langchain_core.runnables import RunnableParallel , RunnableLambda
import logging

logger = logging.getLogger(__name__)

def test_color_caption_prompt():
    prompt = ColorCaptionPrompt()
    input = {
        "count": 1,
        "category": "상의",
        "image_data": "base64_image_data"
    }
    result = prompt.invoke(input)
    print(result)

def test_deep_image_caption_prompt():
    prompt = DeepImageCaptionPrompt()
    input = {
        "category": "상의",
        "image_data": "base64_image_data",
        "count": 1,
        "sdsd" : 10
    }
    result = prompt.invoke(input)
    print(result)

def test_text_image_ocr_prompt():
    prompt = TextImageOCRPrompt()
    llm_input = {
        LLMInputKeys.TEXT_IMAGES: {
            "image_data": "base64_image_data",
        }
    }
    input = {
        "image_data": "base64_image_data",
    }
    result =  RunnableLambda(prompt.extract_chain_input) | prompt 
    print(result.invoke(llm_input))


def test_fashion_caption_generator():
    p1 = DeepImageCaptionPrompt()
    p2 = ColorCaptionPrompt()
    p3 = TextImageOCRPrompt()

    llm_input = {
        LLMInputKeys.DEEP_CAPTION: {
            "category": "12345",
            "image_data": "base64_image_data",
            "count": 1,
        },
        LLMInputKeys.COLOR_IMAGES: {
            "count": 1,
            "category": "qwert123",
            "image_data": "base64_image_data",
            "a" : 10
        },
        LLMInputKeys.TEXT_IMAGES: {
            "image_data": "base64_image_data",
            "asdas" : 23
        }
    }
    
    # 병렬 체인 구성
    chain = RunnableParallel(
        deep_captioning= RunnableLambda(p1.extract_chain_input) | p1,
        color_analysis= RunnableLambda(p2.extract_chain_input) | p2,
        text_image_ocr= RunnableLambda(p3.extract_chain_input) | p3
    )
    
    # 각각의 입력에 맞는 데이터 전달
    result = chain.invoke(llm_input)
       
    print(result["deep_captioning"])
    print("*"*100)
    print(result["color_analysis"])
    print("*"*100)
    print(result["text_image_ocr"])


