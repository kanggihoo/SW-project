# 패션 상품 벡터 검색 시스템 구현 계획

## 🎯 프로젝트 목표
VLM으로 추출한 패션 상품 데이터를 MongoDB Atlas에 저장하고, 사용자의 텍스트 질의에 대해 벡터 검색을 통해 관련 의류 이미지 URL을 반환하는 시스템 구축

## 📋 현재 상황 분석
기존 시스템

- 데이터 소스: VLM을 통해 추출된 구조화된 패션 상품 정보

- 데이터 저장: AWS DynamoDB (메타데이터) + S3 (이미지)

- 데이터 형태: result.json에서 확인할 수 있는 구조화된 속성 및 캡션

추출된 데이터 구조
```json

{ 
    "deep_caption":{
        "structured_attributes": {
            "common": {
                "sleeve_length": "긴소매",
                "neckline": "라운드넥"
            },
            "front": {
                "pattern": {
                    "type": "무지/솔리드",
                    "description": "없음"
                },
                "closures_and_embellishments": {
                    "type": "여밈 없음",
                    "description": "없음"
                }
            },
            "back": {
                "pattern": {
                    "type": "무지/솔리드",
                    "description": "없음"
                },
                "closures_and_embellishments": {
                    "type": "여밈 없음",
                    "description": "없음"
                }
            },
            "subjective": {
                "fit": "레귤러 핏/스탠다드 핏",
                "style_tags": [
                    "모던/미니멀",
                    "심플 베이직",
                    "캐주얼"
                ],
                "tpo_tags": [
                    "데일리",
                    "여행/휴가",
                    "데이트/주말"
                ]
            }
        },
        "image_captions": {
            "front_text_specific": "정면은 라운드넥에 긴소매를 가진 검은색 맨투맨 티셔츠입니다. 특별한 패턴이나 장식 없이 깔끔한 무지 디자인입니다.",
            "back_text_specific": "후면은 깔끔한 디자인으로 특별한 디테일 없이 무지 형태로 제작되었습니다.",
            "design_details_description": "검은색 맨투맨 티셔츠로, 라운드넥과 긴소매 디자인입니다. 정면과 후면 모두 무지 솔리드 패턴이며, 별도의 여밈이나 장식 요소는 없습니다.",
            "style_description": "이 맨투맨 티셔츠는 심플하고 베이직한 디자인으로, 모던하고 미니멀한 스타일을 연출합니다. 캐주얼하면서도 깔끔한 느낌을 주어 다양한 하의와 매치하기 좋습니다.",
            "tpo_context_description": "데일리로 편안하게 착용하기 좋으며, 주말이나 여행 시에도 활동적인 느낌을 줄 수 있습니다. 캐주얼한 모임이나 실내 활동에도 잘 어울립니다.",
            "comprehensive_description": "이 제품은 라운드넥에 긴소매를 가진 검은색 맨투맨 티셔츠입니다. 정면과 후면 모두 무지 디자인이며, 특별한 여밈이나 장식 요소는 없습니다. 레귤러 핏으로 편안하게 착용할 수 있으며, 캐주얼하고 모던한 스타일을 연출하기 좋습니다. 데일리룩이나 편안한 주말 활동에 적합합니다."
        }
    },
    "color_images" :{
        "color_info": [
            {
                "name": "블랙",
                "hex": "#000000",
                "attributes": {
                    "brightness": "아주 어두움",
                    "saturation": "낮음"
                }
            },
            {
                "name": "블랙",
                "hex": "#000000",
                "attributes": {
                    "brightness": "아주 어두움",
                    "saturation": "낮음"
                }
            }
        ]
    },
    "text_images" : {
        "care_info" : "찬물로 단독 손세탁 하십시오. 소재 특성상 세탁 후 약간의 수축이 있을수 있습니다 ",
        "marerial_info" : "COTTON 100%",
        "product_description" : "FUNDAMENTAL을 위해 개발된 800G/Y 이상 헤비 코튼 스웨트 원단으로 텐타, 덤블 방축 가공 및 바이오 워싱 처리가 되어 터치감이 부드럽고 표면은 기모감 없이 깨끗합니다. 수많은 가공으로 세탁 후에도 옷의 형태감 유지 및 봉제 변형 방지, 컬러 변화 최소화. 안정적인 견뢰도의 리플렉티브 필름 프레스 작업으로 세탁 후에도 반사광 유지.",
        "size_info" : {
            "is_exist" : true ,
            "size_measurements" : '{"SIZE 1": {"총장": "67cm", "가슴단면": "61cm", "어깨너비": "63cm", "소매길이": "60cm"}, "SIZE 2": {"총장": "69cm", "가슴단면": "64cm", "어깨너비": "65cm", "소매길이": "62cm"}}'
        }
    }
}
```

## 🚀 구현 단계별 계획

### Phase 1: 단순 벡터 검색 (현재 목표)
#### 1.1 데이터 저장
- 플랫폼: MongoDB Atlas
- 벡터화 대상: image_captions.comprehensive_description
- 임베딩 모델: OpenAI text-embedding-ada-002 또는 유사 모델

#### 1.2 검색 워크플로우

- 사용자 질의 접수: "편안한 검은색 상의"
- 질의 벡터화: 동일한 임베딩 모델로 사용자 텍스트 변환
- 벡터 유사도 검색: MongoDB Atlas Vector Search 활용
- 결과 반환: 유사도 상위 N개 이미지 URL 제공

#### 1.3 기술 스택

- 벡터 DB: MongoDB Atlas (Vector Search 기능)
- 임베딩: OpenAI Embeddings API
- 백엔드: Python FastAPI
- 벡터 검색: cosine similarity 기반

### Phase 2: 고도화 계획 (향후)
#### 2.1 텍스트 분석 및 사전 필터링

- 질의 분석기: 사용자 텍스트에서 구조화된 속성 추출
    - 색상, 스타일, TPO, 카테고리 등 식별

- 하이브리드 검색: 구조화된 필터 + 벡터 검색 조합

#### 2.2 다중 벡터 필드 활용
```json
{
    "vectors": {
        "comprehensive_vector": [...], // 종합 설명
        "style_vector": [...], // 스타일 중심
        "design_vector": [...], // 디자인 디테일 중심
        "tpo_vector": [...] // 용도/상황 중심
    }
}
```

#### 2.3 지능형 검색 전략

의도 분류: 스타일 검색 vs 기능 검색 vs 상황별 검색
가중치 조합: 질의 유형에 따른 벡터 필드별 가중치 적용
개인화: 사용자 선호도 학습 및 반영

## 🔧 구현 우선순위
## 즉시 구현(Phase 1)
### 1. MongoDB Atlas 설정
- Vector Search 인덱스 생성
- 컬렉션 스키마 설계


### 2. 검색 API 개발

- 텍스트 입력 → 벡터 변환 → 유사도 검색
- 이미지 URL 반환 엔드포인트

### 3.성능 최적화

- 인덱스 튜닝
- 검색 속도 및 정확도 측정

## 향후 확장 (Phase 2)

질의 분석 모듈
다중 벡터 필드 인덱싱
하이브리드 검색 로직
사용자 피드백 수집 및 학습

📊 예상 검색 시나리오
단순 질의 (Phase 1 대응)

"검은색 맨투맨"
"편안한 상의"
"데일리룩 티셔츠"

복합 질의 (Phase 2 대응)

"오피스에서 입을 수 있는 깔끔한 블라우스"
"주말 데이트에 어울리는 캐주얼한 상의"
"여행갈 때 편한 긴팔 티셔츠"

🎯 성공 지표

검색 정확도: 사용자 의도와 결과 이미지의 일치도
응답 속도: 평균 검색 응답 시간 < 500ms
사용자 만족도: 클릭률, 체류시간 등 행동 지표
시스템 확장성: 상품 수 증가에 따른 성능 유지
