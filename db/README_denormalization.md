# MongoDB 데이터 비정규화 가이드

이 문서는 MongoDB Atlas Vector Search의 성능을 극대화하기 위해 기존의 product-centric 데이터 구조를 SKU-centric 구조로 변환하는 과정을 설명합니다.

## 개요

### 기존 구조 (As-Is): 상품 중심 모델
- **문서 키**: `product_id` (`_id`)
- **구조**: 하나의 상품 문서에 여러 SKU 정보가 배열로 저장
- **한계**: 특정 색상으로 필터링하기 어려움

### 목표 구조 (To-Be): SKU 중심 모델
- **문서 키**: `sku_id` (`_id`)
- **구조**: 각 SKU마다 별도의 문서로 분리
- **장점**: 색상별 필터링과 인덱싱이 용이

## 파일 구조

```
db/
├── denormalization.py          # 비정규화 서비스 클래스
├── run_denormalization.py      # 실행 스크립트
├── config/
│   └── config.py              # 업데이트된 설정 (products_by_sku 지원)
└── README_denormalization.md   # 이 문서
```

## 설정 변경사항

`db/config/config.py`에 새로운 설정이 추가되었습니다:

```python
_mongodb_atlas_sku_dict = {
    "MONGODB_ATLAS_SKU" : {
        "MONGODB_ATLAS_DATABASE_NAME": "fashion_db",
        "MONGODB_ATLAS_COLLECTION_NAME": "products_by_sku",
        "MONGODB_ATLAS_CONNECTION_STRING": os.getenv("MONGODB_ATLAS_URI")
    }
}
```

## 사용법

### 1. 기본 실행 (테스트용 - 10개 상품만)
```bash
python run_denormalization.py --limit 10
```

### 2. 전체 데이터 마이그레이션
```bash
python run_denormalization.py
```

### 3. 검증만 실행
```bash
python run_denormalization.py --verify-only
```

### 4. 특정 개수만 처리
```bash
python run_denormalization.py --limit 100
```

## 스크립트 옵션

- `--limit N`: 처리할 최대 상품 수 (기본값: None, 모든 상품 처리)
- `--verify-only`: 마이그레이션 없이 검증만 실행

## 데이터 변환 과정

### 1. 소스 데이터 읽기
- `products` 컬렉션에서 상품 문서들을 순차적으로 읽어옴

### 2. 데이터 변환
각 상품 문서에 대해:
- 공통 정보 추출: `products`, `embedding`, `reviews`, `images`
- `product_skus` 배열을 개별 SKU 문서로 분해
- 각 SKU마다 새로운 문서 생성

### 3. 배치 처리
- 100개씩 배치로 묶어서 `products_by_sku` 컬렉션에 삽입
- 성능 최적화를 위한 `insert_many()` 사용

### 4. 검증
- 소스와 타겟 컬렉션의 문서 수 비교
- 샘플 데이터 검증으로 변환 정확성 확인

## 예시 데이터 변환

### 입력 (기존 구조)
```json
{
  "_id": "4149670",
  "products": { "product_name": "SL01 섬머 데님 와이드 팬츠", ... },
  "product_skus": {
    "sku_id": ["4149670_그레이", "4149670_데님", "4149670_화이트"],
    "color_name": ["그레이", "데님", "화이트"],
    ...
  },
  "embedding": { ... }
}
```

### 출력 (변환된 구조)
```json
// 문서 1
{
  "_id": "4149670_그레이",
  "products": { "product_name": "SL01 섬머 데님 와이드 팬츠", ... },
  "product_sku": {
    "sku_id": "4149670_그레이",
    "color_name": "그레이",
    ...
  },
  "embedding": { ... }
}

// 문서 2
{
  "_id": "4149670_데님",
  "products": { "product_name": "SL01 섬머 데님 와이드 팬츠", ... },
  "product_sku": {
    "sku_id": "4149670_데님",
    "color_name": "데님",
    ...
  },
  "embedding": { ... }
}
```

## 주의사항

1. **원본 데이터 보존**: 기존 `products` 컬렉션은 수정하지 않음
2. **새 컬렉션 생성**: `products_by_sku` 컬렉션에 변환된 데이터 저장
3. **롤백 가능**: 문제 발생 시 원본 데이터는 그대로 보존
4. **배치 처리**: 메모리 효율성을 위한 배치 단위 처리
5. **에러 처리**: 개별 문서 처리 실패 시에도 전체 프로세스 계속

## 성능 고려사항

- **배치 크기**: 기본 100개 (메모리 상황에 따라 조정 가능)
- **인덱싱**: 변환 후 적절한 인덱스 생성 권장
- **모니터링**: 처리 진행 상황과 에러 로그 확인

## 문제 해결

### 일반적인 문제들

1. **연결 실패**: MongoDB Atlas 연결 문자열 확인
2. **메모리 부족**: 배치 크기 줄이기
3. **중복 키 에러**: 이미 처리된 데이터 확인

### 로그 확인
```bash
# 상세 로그와 함께 실행
python run_denormalization.py --limit 10 2>&1 | tee migration.log
```

## 다음 단계

1. **인덱스 생성**: `product_sku.color_name` 등에 인덱스 생성
2. **벡터 검색 설정**: 새로운 구조에 맞는 벡터 검색 인덱스 생성
3. **애플리케이션 업데이트**: 새로운 컬렉션을 사용하도록 코드 수정
4. **성능 테스트**: 변환된 데이터로 검색 성능 확인
