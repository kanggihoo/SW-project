# VLM Output Models

VLM(Vision-Language Model)을 활용한 상품 데이터 추출을 위한 Pydantic 모델들입니다.

## 📂 구조

```
app/models/
├── __init__.py              # 패키지 초기화 및 export
├── base_types.py           # 기본 타입과 열거형 정의
├── product_attributes.py   # 상품 속성 모델들
├── variant_models.py       # 상품 변형(색상별) 모델들
├── master_data.py          # 마스터 데이터 및 단계별 출력 모델들
├── langchain_utils.py      # Langchain 통합 유틸리티
└── README.md               # 이 파일
```

## 🚀 사용법

### 1. 기본 임포트

```python
from app.models import (
    ProductMasterData,
    DeepCaptioningOutput,
    SimpleAttributeOutput,
    CombinedVLMOutput
)
```

### 2. Langchain과 함께 사용하기

```python
from app.models.langchain_utils import (
    create_deep_captioning_prompt,
    create_simple_attribute_prompt,
    validate_and_fix_vlm_output
)

# 딥 캡셔닝 프롬프트 생성
deep_prompt = create_deep_captioning_prompt()

# VLM 체인 구성
chain = deep_prompt | vlm_model | StrOutputParser()

# VLM 실행 및 결과 파싱
raw_result = chain.invoke({"image_data": image_base64})
parsed_result = validate_and_fix_vlm_output(raw_result, DeepCaptioningOutput)
```

### 3. 단계별 처리

```python
# 1단계: 딥 캡셔닝 (공통 정보 추출)
deep_result = DeepCaptioningOutput(
    base_product_info=BaseProductInfo(...)
)

# 2단계: 단순 속성 추출 (색상 정보)
simple_result = SimpleAttributeOutput(
    variants=[ProductVariant(...), ...]
)

# 3단계: 결과 결합
combined = CombinedVLMOutput(
    product_group_id="P0001",
    deep_captioning_result=deep_result,
    simple_attribute_result=simple_result
)

# 4단계: 마스터 데이터로 변환
master_data = combined.to_master_data()
```

### 4. JSON 직렬화/역직렬화

```python
# JSON으로 저장
json_data = master_data.model_dump_json(indent=2)

# JSON에서 복원
restored = ProductMasterData.model_validate_json(json_data)
```

## 📋 주요 모델 설명

### `ProductMasterData`

- 전체 상품 데이터의 최종 형태
- 상품 그룹 ID, 추출 날짜, 기본 정보, 변형 정보 포함

### `DeepCaptioningOutput`

- 딥 캡셔닝 단계의 출력 (색상 제외한 공통 정보)
- 고비용 VLM으로 그룹당 1회만 실행

### `SimpleAttributeOutput`

- 단순 속성 추출 단계의 출력 (색상 정보만)
- 저비용으로 SKU별로 실행

### `BaseProductInfo`

- 구조화된 속성 + 임베딩용 캡션
- 검색 최적화를 위한 다양한 설명문 포함

## 🎨 색상 및 스타일 분류

### 색상 분류 체계

- **Level 1**: 16가지 기본 색상 (`PrimaryColor`)
- **Level 2**: 명도, 채도, 톤감 속성 (`ColorAttribute`)

### 스타일 분류

- **핏**: 슬림/레귤러/오버사이즈
- **스타일**: 모던, 캐주얼, 포멀 등 9가지
- **TPO**: 데일리, 오피스, 파티 등 8가지

## 🔧 고급 기능

### 1. 출력 검증 및 수정

```python
from app.models.langchain_utils import validate_and_fix_vlm_output

# VLM 출력이 완벽하지 않을 때 자동 수정
try:
    result = validate_and_fix_vlm_output(raw_vlm_output, DeepCaptioningOutput)
except ValueError as e:
    print(f"파싱 실패: {e}")
```

### 2. 스키마 정보 출력

```python
from app.models.langchain_utils import get_model_schema_description

# 모델 구조를 사람이 읽기 쉬운 형태로 출력
schema_desc = get_model_schema_description(ProductMasterData)
print(schema_desc)
```

### 3. 커스텀 검증

```python
from pydantic import validator

class CustomProductVariant(ProductVariant):
    @validator('color')
    def validate_color_consistency(cls, v):
        # 커스텀 색상 검증 로직
        return v
```

## 📝 예시 데이터

```python
example_data = ProductMasterData(
    product_group_id="P0001",
    base_product_info=BaseProductInfo(
        structured_attributes=StructuredAttributes(
            common=CommonAttributes(
                category_l1="상의",
                category_l2="셔츠",
                sleeve_length=SleeveLength.LONG,
                neckline=Neckline.COLLAR
            ),
            front=FrontAttributes(
                pattern=PatternInfo(
                    type=PatternType.STRIPE,
                    description="세로 스트라이프"
                )
            ),
            back=BackAttributes(),
            subjective=SubjectiveAttributes(
                fit=FitType.REGULAR,
                style_tags=[StyleTag.CASUAL, StyleTag.MODERN],
                mood_tags=["단정한", "산뜻한"],
                tpo_tags=[TPOTag.DAILY, TPOTag.OFFICE]
            )
        ),
        embedding_captions=EmbeddingCaptions(
            design_details_description="클래식한 셔츠 칼라와 세로 스트라이프 패턴",
            style_vibe_description="캐주얼하면서도 미니멀한 스타일",
            tpo_context_description="데일리룩과 오피스룩에 적합"
        )
    ),
    variants=[
        ProductVariant(
            sku_id="P0001-BLUE",
            is_representative=True,
            product_image_url="https://example.com/p0001_blue.jpg",
            color=ColorDetail(
                primary=ColorInfo(
                    name=PrimaryColor.BLUE,
                    hex="#4A90E2",
                    attributes=[ColorAttribute.VIVID, ColorAttribute.COOL]
                ),
                secondary=[],
                all_colors=["블루", "화이트"],
                all_color_attributes=["선명한", "쿨톤", "밝은"]
            ),
            embedding_captions=VariantEmbeddingCaptions(
                front_text_specific="블루 스트라이프 셔츠의 정면 이미지"
            )
        )
    ]
)
```

## ⚠️ 주의사항

1. **색상 분리**: 딥 캡셔닝에서는 색상 정보를 절대 포함하지 않음
2. **모듈 독립성**: 각 모델은 독립적으로 사용 가능하도록 설계
3. **확장성**: 새로운 카테고리나 속성 추가시 enum 클래스만 수정
4. **검증**: Pydantic의 자동 검증 기능을 최대한 활용
