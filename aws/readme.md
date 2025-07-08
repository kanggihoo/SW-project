📦 ProductAssets 테이블 구조
ProductAssets 테이블은 상품 애셋 정보 관리, 큐레이션 상태 모니터링, 카테고리별 통계 집계, S3 연동 최적화를 위한 구조로 설계되었습니다.

## 🔑 기본 키 구조

| 키        | 유형 | 필드명        | 타입 | 설명                                                                                   |
| --------- | ---- | ------------- | ---- | -------------------------------------------------------------------------------------- |
| 파티션 키 | (PK) | sub\*category | N    | 서브 카테고리 ID. 메타데이터 항목은 0으로 고정                                         |
| 정렬 키   | (SK) | product_id    | S    | 고유한 상품 ID 또는 STATUS_STATS*{main*category}\*{sub_category} 형식의 메타 데이터 키 |

## 🗃️ 주요 필드 설명

| 필드명                             | 타입 | 설명                                                                                 |
| ---------------------------------- | ---- | ------------------------------------------------------------------------------------ |
| **representative_assets**          | M    | 대표 이미지(전면, 후면, 색상 변형 등). 단, curation_status가 PASS이면 해당 필드 없음 |
| **curation_status**                | S    | 큐레이션 상태 (COMPLETED, PENDING, PASS)                                             |
| **main_category**                  | S    | 메인 카테고리 정보                                                                   |
| **detail, segment, summary, text** | L    | S3 객체 이름 리스트. DynamoDB에서 존재 여부 확인 후 S3 접근                          |
| **recommendation_order**           | S    | 추천 순위 (7자리 제로 패딩: 예 0000001)                                              |
| **created_at**                     | S    | 애셋 생성 시각                                                                       |
| **completed_by**                   | S    | 큐레이션 완료자                                                                      |
| **pass_reason**                    | S    | PASS 상태인 경우에만 존재하는 필드. 패스 이유 설명                                   |

## 📊 메타 데이터 전용 필드

| 필드명               | 타입 | 설명                               |
| -------------------- | ---- | ---------------------------------- |
| completed_count      | N    | COMPLETED 상태 상품 수             |
| recommendation_order | N    | 메타 정보 내에서 평균 추천 순위 등 |
| pass_count           | N    | PASS 상태 상품 수                  |
| pending_count        | N    | PENDING 상태 상품 수               |
| target_sub_category  | N    | 메타 통계 대상 sub_category        |
| total_products       | N    | 총 상품 수                         |

- 메타 데이터 항목은 항상 sub*category = 0을 가지며, SK = STATUS_STATS*{main*category}*{sub_category} 형식을 따릅니다.

## 🔍 글로벌 보조 인덱스 (GSI)

**CurrentStatus-RecommendationOrder-GSI**

- 파티션 키: curation_status (S)
- 정렬 키: recommendation_order + # + product_id (S)

활용: 이 GSI는 특정 curation_status를 가진 상품들을 recommendation_order 순으로 효율적으로 정렬하여 조회할 때 사용됩니다. 예를 들어, "현재 PENDING 상태인 상품들 중 추천 순위가 높은 순서대로 목록을 가져오고 싶을 때" 이 인덱스를 활용하면 매우 빠르게 데이터를 검색할 수 있습니다. #product_id를 추가하여 recommendation_order가 동일한 경우에도 고유성을 보장하고 안정적인 정렬을 가능하게 합니다.

## 주요 활용처 및 장점

- 효율적인 상품 애셋 조회: sub_category와 product_id를 통해 특정 상품의 애셋 정보를 빠르게 가져올 수 있습니다.

- 실시간 큐레이션 상태 모니터링: GSI를 활용하여 특정 큐레이션 상태(예: PENDING)의 상품들을 추천 순위별로 조회함으로써, 큐레이션 작업 진행 상황을 효과적으로 모니터링하고 우선순위에 따라 작업을 할당할 수 있습니다.

- 카테고리별 통계 제공: 메타 데이터 항목을 통해 특정 메인/서브 카테고리 내의 전체 상품 수, 그리고 각 큐레이션 상태별 상품 수를 신속하게 집계하여 대시보드나 보고서에 활용할 수 있습니다.

- S3 연동 최적화: detail, segment, summary, text 필드에 S3 객체 이름을 저장함으로써, S3에 직접 접근하기 전 DynamoDB에서 애셋 존재 여부를 저렴하고 빠르게 확인하여 비용과 성능을 모두 최적화할 수 있습니다. 이는 불필요한 S3 API 호출을 줄이는 효과적인 전략입니다.
