from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage , SystemMessage
from langchain_core.prompts import ChatPromptTemplate 
from dotenv import load_dotenv
import re
import requests
import json
import os
load_dotenv()

def fetch_gemini_models_and_save():
    """
    Google Gemini API에서 사용 가능한 모델 목록을 HTTP 요청으로 가져와서 JSON 파일로 저장
    """
    # 환경변수에서 API 키 가져오기
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        return None
    
    # Gemini API 엔드포인트
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        # HTTP GET 요청 보내기
        response = requests.get(url)
        response.raise_for_status()  # HTTP 에러가 있으면 예외 발생
        
        # JSON 응답 파싱
        models_data = response.json()
        
        # 모델명만 추출하기
        model_names = []
        real_model_names = []
        
        if 'models' in models_data:
            for model in models_data['models']:
                model_names.append(model['name'])
                # 'models/' 접두사 제거
                real_name = model['name'].split('/')[-1]
                real_model_names.append(real_name)
        
        # 결과를 다양한 형태로 저장
        result = {
            "timestamp": requests.utils.default_headers()['User-Agent'],
            "total_models": len(model_names),
            "full_response": models_data,
            "model_names_with_prefix": model_names,
            "model_names_only": real_model_names,
            "model_names_comma_separated": ",".join(real_model_names)
        }
        
        # JSON 파일로 저장
        output_file = "gemini_models.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 모델 목록이 {output_file}에 저장되었습니다.")
        print(f"📊 총 {len(model_names)}개의 모델을 찾았습니다.")
        
        # 사용 가능한 주요 모델들 출력
        print("\n🔥 주요 사용 가능한 모델들:")
        for name in real_model_names[:10]:  # 처음 10개만 출력
            print(f"  - {name}")
        
        if len(real_model_names) > 10:
            print(f"  ... 및 {len(real_model_names) - 10}개 더")
            
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP 요청 오류: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return None


if __name__ == "__main__":
    print("🚀 Gemini 모델 목록 가져오기 시작...")
    
    # Gemini API에서 모델 목록 가져오기
    gemini_result = fetch_gemini_models_and_save()
    
    print("\n" + "="*50)
    

    
