"""
Langchain Gemini 모델을 사용한 패션 상품 이미지 분석 메인 코드
"""

import os
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv


from utils import setup_logger
from .langchain_utils import (
    setup_langsmith_tracing,
    setup_gemini_model
)
from .models import DeepCaptioningTopOutput, SimpleAttributeOutput
from .prompt import ColorCaptionPrompt, DeepImageCaptionPrompt

def analyze_fashion_images_deep_captioning(
    image_paths: list[str], 
    target_size: int = 224,
    category: str = "상의",
    model_name: str = "gemini-2.5-flash-lite-preview-06-17"
) -> DeepCaptioningTopOutput:
    """
    딥 캡셔닝을 위한 패션 이미지 분석
    
    Args:
        image_paths: 분석할 이미지 파일 경로 리스트
        category: 상품 카테고리 (상의, 하의 등)
        model_name: 사용할 Gemini 모델명
    
    Returns:
        DeepCaptioningOutput: 분석 결과
    """
    print(f"\n🔍 딥 캡셔닝 분석 시작 - 카테고리: {category}")
    
    # 이미지 결합 및 Base64 인코딩
    base64_image = images_to_base64(image_paths, target_size=target_size)
    print(f"✅ 이미지 Base64 인코딩 완료 (길이: {len(base64_image)})")
    
    # 3. Gemini 모델 설정
    model = setup_gemini_model(model_name)
    structured_model = model.with_structured_output(DeepCaptioningTopOutput)
    
    # chain 생성
    deep_chain = DeepImageCaptionPrompt().create_image_captioning_chain(structured_model)
    
    
    # chain의 입력 생성
    deep_chain_input = DeepImageCaptionPrompt().get_chain_input(category=category, image_data=base64_image)
    print("🚀 VLM 분석 시작...")
    
    # 6. 모델 호출
    try:
        # 메시지들을 직접 모델에 전달
        response = deep_chain.invoke(deep_chain_input)
        print(f"✅ VLM 응답 수신 완료")
        return response
        
    except Exception as e:
        print(f"❌ VLM 분석 중 오류 발생: {e}")
        raise


def analyze_fashion_images_simple_attributes(
    image_paths: list[str],
    target_size: int = 224,
    product_group_id: str = "",
    category: str = "상의",
    model_name: str = "gemini-2.5-flash-lite-preview-06-17"
) -> SimpleAttributeOutput:
    """
    단순 속성 추출 (색상)을 위한 패션 이미지 분석
    
    Args:
        image_paths: 분석할 이미지 파일 경로 리스트
        product_group_id: 상품 그룹 ID
        sku_info: SKU 정보
        model_name: 사용할 Gemini 모델명
    
    Returns:
        SimpleAttributeOutput: 분석 결과
    """
    print(f"\n🎨 색상 속성 분석 시작 - 상품 그룹: {product_group_id}")
    
    # 1. 이미지 결합
    base64_image = images_to_base64(image_paths, target_size=target_size)

    print(f"✅ 이미지 Base64 인코딩 완료")
    
    # 3. Gemini 모델 설정
    model = setup_gemini_model(model_name , temperature=0)
    structured_model = model.with_structured_output(SimpleAttributeOutput)
    
    # chain 생성
    color_chain = ColorCaptionPrompt().create_color_captioning_chain(structured_model)
    
    # chain의 입력 생성
    color_chain_input = ColorCaptionPrompt().get_chain_input(count=len(image_paths), category=category, image_data=base64_image)
    
    # 5. 메시지 생성
    print("🚀 VLM 분석 시작...")
    
    # 6. 모델 호출
    try:
        response = color_chain.invoke(color_chain_input)
        print(f"✅ VLM 응답 수신 완료")
        
        # 7. 응답 파싱
        # result = validate_and_fix_vlm_output(raw_output, SimpleAttributeOutput)
        # print("✅ 응답 파싱 완료")
        return response
        
        
    except Exception as e:
        print(f"❌ VLM 분석 중 오류 발생: {e}")
        raise


# def print_analysis_results(result, analysis_type: str):
#     """분석 결과를 보기 좋게 출력"""
#     print(f"\n{'='*60}")
#     print(f"📊 {analysis_type} 분석 결과")
#     print(f"{'='*60}")
    
#     if isinstance(result, DeepCaptioningOutput):
#         print(f"\n🏷️ 주관적 속성:")
#         print(f"  • 핏: {result.subjective_attributes.fit}")
#         print(f"  • 스타일 태그: {', '.join(result.subjective_attributes.style_tags) if result.subjective_attributes.style_tags else 'N/A'}")
#         print(f"  • TPO 태그: {', '.join(result.subjective_attributes.tpo_tags) if result.subjective_attributes.tpo_tags else 'N/A'}")
        
#         print(f"\n📐 구조적 속성:")
#         print(f"  • 소매 길이: {result.structured_attributes.common.sleeve_length}")
#         print(f"  • 넥라인: {result.structured_attributes.common.neckline}")
#         print(f"  • 정면 패턴: {result.structured_attributes.front.pattern.type}")
#         print(f"  • 후면 패턴: {result.structured_attributes.back.pattern.type}")
        
#         print(f"\n📝 임베딩 캡션:")
#         print(f"  • 정면 설명: {result.embedding_captions.front_text_specific[:100]}...")
#         print(f"  • 후면 설명: {result.embedding_captions.back_text_specific[:100]}...")
#         print(f"  • 스타일 설명: {result.embedding_captions.style_vibe_description[:100]}...")
        
#     elif isinstance(result, SimpleAttributeOutput):
#         print(f"\n🎨 색상 정보:")
#         for color in result.colors:
#             print(f"  • {color.color_name} (HEX: {color.hex_code})")
#             print(f"    - 유형: {color.color_type}")
#             print(f"    - 설명: {color.description}")


def main():
    # 환경변수 로드
    load_dotenv()
    
    # LangSmith tracing 설정
    # setup_langsmith_tracing(
    #     enable_tracing=True,  # 필요에 따라 False로 변경
    #     project_name="fashion-caption-analysis"  # 원하는 프로젝트 이름으로 변경
    # )
    
    # """메인 실행 함수"""
    print("🚀 Langchain Gemini를 사용한 패션 이미지 분석 시작\n")

    
    # DATA_DIR = Path(__file__).parent / "data"
    # sample_images = [
    #     DATA_DIR / "front.jpg",  # 정면 누끼 이미지
    #     DATA_DIR / "back.jpg",   # 후면 누끼 이미지  
    #     DATA_DIR / "model.jpg"   # 모델 착용 이미지
    # ]
    
    # # 실제 테스트용 이미지가 있는지 확인
    existing_images = []
    for img_path in sample_images:
        if os.path.exists(img_path):
            existing_images.append(img_path)
        else:
            print(f"⚠️  이미지 파일이 없습니다: {img_path}")
    
    
    try:
        # 1. 딥 캡셔닝 분석
        # gemini-2.5-flash-lite-preview-06-17
        # gemini-2.5-pro-preview-06-05
        # gemini-2.5-flash
        # print(f"\n1️⃣ 딥 캡셔닝 분석 ({len(existing_images)}개 이미지)")
        # deep_result = analyze_fashion_images_deep_captioning(
        #     image_paths=existing_images,
        #     target_size=384,
        #     category="상의",
        #     model_name="gemini-2.5-flash-lite-preview-06-17"
        # )
        # print(deep_result)
        
        
        # 2. 색상 속성 분석
        print(f"\n\n2️⃣ 색상 속성 분석")
        color_result = analyze_fashion_images_simple_attributes(
            image_paths=existing_images[:2],
            target_size=224,
            product_group_id="TEST_001",
            category="상의",
            model_name="gemini-2.0-flash"
        )
        print(color_result)
        
        # print(f"\n✅ 모든 분석이 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # main()
    import logging
    from processing.image_processor import download_images_sync
    from aws.aws_manager import AWSManager
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    aws_manager = AWSManager()
    pagenator = aws_manager.dynamodb_manager.get_product_pagenator(sub_category=1005 , condition={"curation_status":"COMPLETED"})
    for page in pagenator:
        items = page.get('Items')
        logger.info(f"현재 총 제품 수 : {page.get('Count')}")
        if items:
            for item in items:
                print(item.get('product_id') , item.get('sub_category') , item.get('main_category') , item.get('representative_assets') , item.get('text') )
                images = aws_manager.get_product_images_from_paginator(item)
                logger.info(f"이미지 정보 리스트 : {images}")   
                download_images_sync(images)
                print(images)
                break
        break
    
            

    
