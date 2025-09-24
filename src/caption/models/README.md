# VLM Output Models

VLM(Vision-Language Model)을 활용한 상품 데이터 추출을 위한 Pydantic 모델들입니다.

이 문서는 VLM(Vision-Language Model)에서 출력되는 두 가지 주요 데이터 구조인 `DeepCaptioningTopOutput`과 `SimpleAttributeOutput`의 JSON 스키마를 설명합니다.

---

## 1. `DeepCaptioningTopOutput`

상의 의류에 대한 깊이 있는 분석 결과를 담는 JSON 구조입니다. 의류의 구조화된 속성과 다양한 용도의 텍스트 캡션을 포함합니다.

### 전체 구조

```json
{
  "structured_attributes": {
    "common": {
      "sleeve_length": "민소매",
      "neckline": "라운드넥"
    },
    "front": {
      "pattern": {
        "type": "스트라이프",
        "description": "세로 스트라이프"
      },
      "closures_and_embellishments": {
        "type": "버튼/단추",
        "description": "앞면 중앙 버튼 3개"
      }
    },
    "back": {
      "pattern": {
        "type": "스트라이프",
        "description": "세로 스트라이프"
      },
      "closures_and_embellishments": {
        "type": "여밈 없음",
        "description": ""
      }
    },
    "subjective": {
      "fit": "레귤러 핏/스탠다드 핏",
      "style_tags": ["캐주얼", "심플 베이직"],
      "tpo_tags": ["데일리", "데이트/주말"]
    }
  },
  "image_captions": {
    "front_text_specific": "정면에서 본 이 옷은 라운드넥과 버튼 여밈이 특징인 반소매 상의입니다. 파란색 바탕에 흰색 세로 스트라이프 패턴이 들어가 있습니다.",
    "back_text_specific": "후면은 특별한 여밈이나 장식 없이 깔끔한 디자인이며, 정면과 동일한 스트라이프 패턴이 이어집니다.",
    "design_details_description": "이 상의는 라운드넥, 반소매 디자인을 가지고 있습니다. 전면에 버튼 여밈이 있으며, 전체적으로 세로 스트라이프 패턴이 적용되었습니다.",
    "style_description": "심플한 스트라이프 패턴과 베이직한 디자인으로 캐주얼하면서도 단정한 느낌을 줍니다.",
    "tpo_context_description": "일상적인 데일리룩이나 편안한 주말 데이트룩으로 활용하기 좋으며, 다양한 하의와 쉽게 매치할 수 있습니다.",
    "comprehensive_description": "파란색과 흰색의 조화가 돋보이는 이 라운드넥 반소매 상의는 레귤러 핏으로 편안한 착용감을 제공합니다. 앞면의 버튼 디테일과 전체적인 세로 스트라이프 패턴이 특징이며, 캐주얼한 데일리룩이나 주말 나들이 룩에 잘 어울립니다."
  }
}
```

### 상세 설명

- **`structured_attributes`**: 의류의 객관적 속성을 체계적으로 분류합니다.
    - **`common`**: 앞/뒤 공통 속성 (소매 길이, 넥라인).
    - **`front`**: 정면 디자인 요소 (패턴, 여밈/장식).
    - **`back`**: 후면 디자인 요소 (패턴, 여밈/장식).
    - **`subjective`**: 주관적 평가 정보 (핏, 스타일, TPO).
- **`image_captions`**: 다양한 관점에서 생성된 텍스트 설명입니다.
    - **`front_text_specific`**: 정면 이미지 기반 상세 설명.
    - **`back_text_specific`**: 후면 이미지 기반 상세 설명.
    - **`design_details_description`**: 모든 디자인 요소를 종합한 설명.
    - **`style_description`**: 스타일과 분위기에 초점을 맞춘 설명.
    - **`tpo_context_description`**: 추천 착용 상황(TPO)에 대한 설명.
    - **`comprehensive_description`**: 모든 정보를 종합한 완전한 설명.

---

## 2. `SimpleAttributeOutput`

의류의 색상 정보에 특화된 분석 결과를 담는 JSON 구조입니다.

### 전체 구조

```json
{
  "color_info": [
    {
      "name": "블루",
      "hex": "#4A90E2",
      "attributes": {
        "brightness": "밝음",
        "saturation": "높음"
      }
    },
    {
      "name": "화이트",
      "hex": "#FFFFFF",
      "attributes": {
        "brightness": "아주 밝음",
        "saturation": "아주 낮음"
      }
    }
  ]
}
```

### 상세 설명

- **`color_info`**: 의류에서 식별된 색상 정보의 배열(`list`)입니다. 하나의 의류에 여러 색상이 사용된 경우, 각 색상에 대한 정보가 객체로 추가됩니다.
    - **`name`**: 대표 색상 이름 (예: "블루").
    - **`hex`**: 해당 색상의 HEX 코드 (예: "#4A90E2").
    - **`attributes`**: 색상의 세부 속성.
        - **`brightness`**: 명도 (밝기).
        - **`saturation`**: 채도 (선명도).


## ⚠️ 주의사항

1. **색상 분리**: 딥 캡셔닝에서는 색상 정보를 절대 포함하지 않음
2. **모듈 독립성**: 각 모델은 독립적으로 사용 가능하도록 설계
3. **확장성**: 새로운 카테고리나 속성 추가시 enum 클래스만 수정
4. **검증**: Pydantic의 자동 검증 기능을 최대한 활용
