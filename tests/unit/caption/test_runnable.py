from caption.prompt.color_analysis_prompt_template import ColorCaptionPrompt 
from caption.prompt.image_deep_captioning_prompt_template import DeepImageCaptionPrompt
from caption.fashion_caption_generator import FashionCaptionGenerator
from langchain_core.runnables import RunnableParallel , RunnableLambda

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

def test_fashion_caption_generator():
    p1 = DeepImageCaptionPrompt()
    p2 = ColorCaptionPrompt()
    
    # 병렬 체인 구성
    chain = RunnableParallel(
        deep_captioning= RunnableLambda(p1.extract_chain_input) | p1,
        color_analysis= RunnableLambda(p2.extract_chain_input) | p2
    )
    
    # 각각의 입력에 맞는 데이터 전달
    input_data = {
        "category": "상의",
        "image_data": "실제_base64_인코딩된_이미지_데이터",
        "count": 1  # ColorCaptionPrompt에서만 사용
    }
    result = chain.invoke(input_data)
       
    print(result)
