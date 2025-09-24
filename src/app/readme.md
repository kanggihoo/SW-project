# FastAPI 프로젝트 구조 
``` 
project_root/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 초기화 및 라우터 등록
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # 앱 설정 (Pydantic Settings)
│   │   └── dependencies.py     # FastAPI 의존성 주입
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── products.py      # 상품 CRUD API
│   │   │   │   ├── search.py        # 검색 API (텍스트, 벡터)
│   │   │   │   ├── recommendations.py # 추천 API
│   │   │   │   └── health.py        # 헬스체크 API
│   │   │   └── api.py               # v1 라우터 통합
│   │   └── deps.py                  # API 의존성
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py        # 커스텀 예외 클래스
│   │   ├── middleware.py        # 미들웨어 (CORS, 로깅 등)
│   │   └── security.py          # 인증/보안 관련
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py          # API 요청 모델 (Pydantic)
│   │   ├── responses.py         # API 응답 모델 (Pydantic)
│   │   └── domain.py            # 도메인 모델
│   ├── services/
│   │   ├── __init__.py
│   │   ├── product_service.py   # 상품 비즈니스 로직
│   │   ├── search_service.py    # 검색 비즈니스 로직
│   │   ├── embedding_service.py # 임베딩 생성 서비스
│   │   └── recommendation_service.py # 추천 서비스
│   └── router/
│       ├── __init__.py
│       └── websocket.py         # 기존 WebSocket (LangGraph)
├── db/                          # 기존 DB 모듈 유지
└── tests/                       # 테스트 코드
```

# 🔧 각 모듈별 역할과 책임
## 1. app/main.py
- 역할: FastAPI 앱 초기화, 라우터 등록, 미들웨어 설정
- 포함 내용:
  - FastAPI 앱 생성 및 설정
  - CORS, 로깅 미들웨어 등록
  - API v1, WebSocket 라우터 등록
  - 예외 핸들러 등록
  - OpenAPI 문서 커스터마이징


## 2. app/config/settings.py
- 역할: 앱 전체 설정 관리
- 포함 내용:
  - Pydantic Settings 기반 환경변수 관리
  - MongoDB 연결 설정
  - API 키 관리 (OpenAI, Jina, Gemini)
  - 임베딩 모델 설정
  - 로깅 설정
  
## 3. app/api/v1/endpoints/
### products.py
```
역할: 상품 CRUD API 엔드포인트
# 엔드포인트:
# - GET /api/v1/products/{product_id}        # 단일 상품 조회
# - GET /api/v1/products                     # 상품 목록 조회 (페이징, 필터)
# - POST /api/v1/products                    # 상품 등록
# - PUT /api/v1/products/{product_id}        # 상품 수정
# - DELETE /api/v1/products/{product_id}     # 상품 삭제
# - POST /api/v1/products/bulk               # 상품 일괄 등록
```

### search.py
```
# 역할: 검색 API 엔드포인트
# 엔드포인트:
# - POST /api/v1/search/text                 # 텍스트 기반 검색
# - POST /api/v1/search/vector               # 벡터 유사도 검색
# - POST /api/v1/search/hybrid               # 하이브리드 검색
# - GET /api/v1/search/filters               # 검색 필터 옵션 조회
```

### recommendations.py
```
역할: 추천 API 엔드포인트
# 엔드포인트:
# - POST /api/v1/recommendations/similar     # 유사 상품 추천
# - POST /api/v1/recommendations/style       # 스타일 기반 추천
# - POST /api/v1/recommendations/occasion    # 상황별 추천
```

## 4. app/models/
### requests.py
- 역할: API 요청 데이터 검증 및 직렬화
- 모델:
    - ProductCreateRequest
    - ProductUpdateRequest  
    - SearchRequest
    - VectorSearchRequest
    - RecommendationRequest
  
### responses.py
- 역할: API 응답 데이터 구조 정의
- 모델:
  - ProductResponse
  - SearchResponse
  - PaginatedResponse
  - ErrorResponse
  - RecommendationResponse
  
## 5. app/services/
### product_service.py
- 역할: 상품 관련 비즈니스 로직
- 기능:
  - 상품 데이터 검증 및 변환
  - 상품 생성/수정/삭제 로직
  - 상품 메타데이터 처리
  - FashionRepository와 연동
  - 
### search_service.py
- 역할: 검색 관련 비즈니스 로직
- 기능:
  - 검색 쿼리 분석 및 최적화
  - 필터 조합 로직
  - 검색 결과 후처리
  - 랭킹 및 정렬 로직
  
### embedding_service.py
- 역할: 임베딩 생성 및 관리
- 기능:
  - 다양한 임베딩 모델 지원 (OpenAI, Jina, Gemini)
  - 임베딩 캐싱 전략
  - 배치 임베딩 처리
  - db/utils.py의 임베딩 함수들을 래핑
  
## 6. app/config/dependencies.py
- 역할: FastAPI 의존성 주입 관리
- 포함:
  - MongoDB 연결 의존성
  - Repository 인스턴스 의존성
  - 설정 의존성
  - 인증 의존성
  
## 🔄 데이터 흐름
1. 일반적인 API 요청 흐름
Client Request → FastAPI Router → Service Layer → Repository → MongoDB → Response
1. 검색 API 흐름
User Query → Search Endpoint → SearchService → EmbeddingService → 
FashionRepository → VectorSearch → Results Processing → Response
