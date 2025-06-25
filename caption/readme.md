**[기술 문서] VLM 기반 의류 속성 및 캡션 데이터 구조 명세서**

### 1. 문서의 목적

본 문서는 VLM(Vision-Language Model)을 통해 **의류 이미지로부터 추출하는 데이터의 표준 JSON 구조를 정의**합니다. 이 데이터 구조는 의류 상품의 객관적 속성과 주관적 해석, 그리고 다양한 검색 전략에 활용될 임베딩용 캡션 정보를 포함합니다. 본 문서는 모든 관련 팀이 데이터의 의미와 활용 방안을 명확히 이해하고, 일관성 있는 시스템을 구축하는 것을 목표로 합니다.

### 2. 데이터 구조의 목표

- **단일 소스(Single Source of Truth):** **단 한 번의 VLM 추출 작업을 통해, 향후 모든 데이터 활용의 기준이 되는 원천 데이터를 생성**합니다.
- **미래 확장성(Future-Proofing):** 초기 단일 임베딩 검색부터 향후 다중 임베딩, 개인화 추천 등 고도화된 기능까지 지원할 수 있도록 설계되었습니다.
- **역할과 책임의 분리:** 객관적 사실과 주관적 해석, 필터링용 데이터와 임베딩용 데이터를 명확히 분리하여 데이터의 활용 목적을 명확히 합니다.

### 3. 최상위 키(Key) 구조

마스터 JSON 객체는 다음과 같은 3개의 최상위 키로 구성됩니다.

- `product_info`: 데이터의 메타 정보를 관리합니다.
- `structured_attributes`: 검색 필터링, UI 구성, 정형 데이터 분석에 사용될 구조화된 속성 정보를 포함합니다.
- `embedding_captions`: 벡터 검색 모델의 임베딩에 사용될 다양한 목적의 자연어 캡션들을 포함합니다.

### 4. 필드별 상세 설명

4.1. `product_info`

상품 및 데이터 자체에 대한 메타 정보입니다.

| Key Path | 데이터 타입 | 설명 | 값 예시 |
| --- | --- | --- | --- |
| `product_info.product_id` | String | 상품 고유 식별자입니다. | `"P0001-BLUE"` |
| `product_info.vlm_extraction_date` | String | VLM이 이 데이터를 추출한 날짜 및 시간(ISO 8601 형식)입니다. | `"2025-06-24T10:37:31+09:00"` |

4.2. `structured_attributes`

필터링 및 정형 분석을 위한 객관적/주관적 속성 정보입니다.

4.2.1. `common`

이미지의 어느 뷰에서나 공통적으로 식별 가능한 객관 정보입니다.

| Key Path | 데이터 타입 | 설명 | 값 예시 |
| --- | --- | --- | --- |
| `common.category_l1` | String | 상품의 대분류입니다. | `"상의"` |
| `common.category_l2` | String | 상품의 세부 분류입니다. | `"셔츠"` |
| `common.color` | Object | 색상 정보를 담는 객체입니다. | `(아래 객체 참조)` |
| `common.color.primary` | Object | 가장 넓은 면적을 차지하는 주요 색상 정보입니다. | `{"name": "블루", "hex": "#4A90E2"}` |
| `common.color.secondary` | Array of Objects | 포인트가 되는 보조 색상 정보 리스트입니다. 없을 경우 `[]`. | `[{"name": "화이트", "hex": "#FFFFFF"}]` |
| `common.sleeve_length` | String (enum) | 소매 기장 정보입니다. **선택지:** `민소매`, `반소매`, `5부`, `7부`, `긴소매` | `"긴소매"` |
| `common.body_length` | String (enum) | 상의/원피스의 전체 기장 정보입니다. **선택지:** `크롭`, `레귤러(골반선)`, `롱(힙 덮음)`, `맥시` | `"레귤러(골반선)"` |

4.2.2. `front`

정면 뷰에서 주로 식별 가능한 객관 정보입니다.

| Key Path | 데이터 타입 | 설명 | 값 예시 |
| --- | --- | --- | --- |
| `front.neckline` | String (enum) | 넥라인 형태 정보입니다. **선택지:** `라운드넥`, `V넥`, `U넥`, `스퀘어넥`, `셔츠 칼라`, `하이넥` | `"셔츠 칼라"` |
| `front.pattern` | Object | 패턴 정보를 담는 객체입니다. | `(아래 객체 참조)` |
| `front.pattern.type` | String (enum) | 패턴의 종류입니다. **선택지:** `없음`, `스트라이프`, `도트`, `체크`, `플로럴`, `그래픽` | `"스트라이프"` |
| `front.pattern.description` | String | 패턴에 대한 상세 서술입니다. | `"세로 방향의 가는 스트라이프 프린팅"` |
| `front.closures_and_embellishments` | Array of Objects | 정면의 여밈 및 장식 요소 정보 리스트입니다. 없을 경우 `[]`. | `[{"type": "버튼", "position": "중앙 여밈", "description": "흰색 플라스틱 단추 7개"}]` |

4.2.3. `back`

후면 뷰에서 주로 식별 가능한 객관 정보입니다.

| Key Path | 데이터 타입 | 설명 | 값 예시 |
| --- | --- | --- | --- |
| `back.pattern` | Object | 후면의 패턴 정보입니다. 정면과 동일할 수 있습니다. | `{"type": "스트라이프", "description": "뒷면까지 이어지는 스트라이프"}` |
| `back.closures_and_embellishments` | Array of Objects | 후면의 장식 요소 정보 리스트입니다. 없을 경우 `[]`. | `[{"type": "플리츠", "position": "등 중앙", "description": "활동성을 위한 센터 플리츠"}]` |

4.2.4. `subjective`

모델 착용샷 등 전체적인 이미지를 통해 VLM이 해석한 주관적 정보입니다. **주로 패싯(Faceted) 필터링에 사용됩니다.**

| Key Path | 데이터 타입 | 설명 | 값 예시 |
| --- | --- | --- | --- |
| `subjective.fit` | String (enum) | 전체적인 핏감입니다. **선택지:** `슬림핏`, `레귤러핏`, `오버핏`, `릴렉스핏` | `"레귤러핏"` |
| `subjective.silhouette` | String (enum) | 전체적인 실루엣입니다. **선택지:** `A라인`, `H라인`, `I라인`, `X라인`, `머메이드` | `"H라인"` |
| `subjective.style_tags` | Array of Strings | VLM이 판단한 스타일 키워드 리스트입니다. (최대 3개) | `["캐주얼", "미니멀", "프렌치시크"]` |
| `subjective.mood_tags` | Array of Strings | VLM이 판단한 분위기 키워드 리스트입니다. (최대 3개) | `["단정한", "산뜻한", "차분한"]` |
| `subjective.tpo_tags` | Array of Strings | VLM이 추천하는 TPO 키워드 리스트입니다. (최대 3개) | `["데일리룩", "오피스룩", "데이트룩"]` |

4.3. `embedding_captions`

벡터 검색 모델의 임베딩 소스로 사용될, 다양한 목적을 가진 자연어 캡션입니다.

| Key Path | 데이터 타입 | 설명 |
| --- | --- | --- |
| `embedding_captions.clip_text_front` | String | **(목적: CLIP 등 모델 학습용)** 정면 이미지의 객관적 시각 특징을 상세히 서술한 캡션입니다. |
| `embedding_captions.design_details_description` | String | **(목적: 다중 임베딩 - 디자인 축)** 의류의 구조, 패턴, 디테일 등 객관적 디자인 요소를 종합하여 서술한 캡션입니다. |
| `embedding_captions.style_vibe_description` | String | **(목적: 다중 임베딩 - 스타일 축)** 의류의 스타일과 분위기를 감성적으로 서술한 캡션입니다. |
| `embedding_captions.tpo_context_description` | String | **(목적: 다중 임베딩 - TPO 축)** 의류의 추천 활용 상황(TPO)을 맥락에 맞게 서술한 캡션입니다. |
| `embedding_captions.comprehensive_description` | String | **(목적: 단일 임베딩 - 초기 모델용)** 모든 정보를 종합하여 작성한, 가장 풍부한 통합 설명문입니다. 상품 상세페이지 설명으로도 활용 가능합니다. |
