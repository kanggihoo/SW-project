## **✅ FastAPI 적용을 위한 완성형 워크플로우**

### **1단계: 핵심 로직 리팩토링 및 클래스화**

`musinsa_api_func.py` 에 작성된 함수 기반 코드를 하나의 서비스 클래스 `MusinsaAPIWrapper`로 통합하여 작성.

- **중복 제거**: `httpx.AsyncClient`, 공통 헤더 등 중복되는 요소는 클래스의 속성(`self.client`, `self.headers`)으로 관리하여 재사용성을 높입니다.
- **응집도 향상**: 관련된 스크레이핑 로직을 클래스 메서드로 묶어 코드의 응집도를 높이고 관리를 용이하게 합니다.

### **2단계: 애플리케이션 생명주기를 이용한 싱글톤 관리**

FastAPI의 `lifespan` 컨텍스트 관리자를 사용하여 애플리케이션 시작 시 서비스 클래스의 인스턴스를 **단 한 번만 생성**하고, `app.state`에 저장하여 전역적으로 접근할 수 있도록 합니다. 앱 종료 시에는 `httpx.AsyncClient`와 같은 리소스를 안전하게 정리(`close`)합니다.

### **3단계: 의존성 주입(Dependency Injection) 설계**

API 엔드포인트에서 `app.state`에 저장된 싱글톤 인스턴스를 깔끔하게 가져올 수 있도록 의존성 함수(예: `get_musinsa_api_wrapper`)를 구현합니다. 이 함수는 `Request` 객체를 인자로 받아 `request.app.state.get_musinsa_api_wrapper`를 반환하는 역할을 합니다.

### **4단계: RESTful API 엔드포인트 설계 및 구현 (신규 추가)**

의존성 주입 함수가 준비되면, 이제 실제 API의 '창구' 역할을 하는 **경로 작동 함수(엔드포인트)**를 정의합니다. 이때 API의 경로는 **RESTful 디자인 원칙**을 따라 직관적이고 일관성 있게 설계

- **RESTful 경로 설계**: 리소스(Resource)를 기반으로 경로를 설계합니다. 예를 들어, 특정 '상품(Product)'에 대한 정보는 `GET /products/{product_id}`로, 그 상품의 '통계(stats)'라는 하위 리소스는 `GET /products/{product_id}/stats`와 같이 명사 중심으로 구성합니다.
- **엔드포인트 구현**: 각 엔드포인트는 의존성 주입(3단계)을 통해 서비스 클래스 인스턴스를 받고, 해당 인스턴스의 적절한 메서드를 호출하여 비즈니스 로직을 수행한 뒤 결과를 반환합니다.

### **5. 사용자 데이터 검증 및 직렬화 (Pydantic 모델)**

사용자의 요청(Request Body, Query/Path Parameters)과 서버의 응답(Response Body) 데이터 구조를 Pydantic 모델로 명확하게 정의합니다.

- **데이터 유효성 검사**: `gt`, `min_length` 등 유효성 검사 옵션을 사용하여 API의 안정성을 높입니다.
- **상세한 스키마 문서화**: `Field`를 사용하여 각 데이터 필드에 대한 상세 설명(`description`)과 예시(`example`)를 추가합니다.
- **경로/쿼리 파라미터**: `Annotated`를 `Path`, `Query`와 함께 사용하여 경로 및 쿼리 파라미터에 대한 유효성 검사와 메타데이터(설명, 예시 등)를 추가합니다.

```python
from typing import Annotated
from fastapi import Path

async def get_item(
    item_id: Annotated[int, Path(description="조회할 상품 ID", gt=0, example=123)]
):
    # ...
```

### **6단계: 풍부한 API 문서 자동화**

현재 `musinsa_api_func.py` 의 docstring 에 작성된 내용을 참고하여, 각 엔드포인트 데코레이터에 다양한 파라미터를 추가하여 API 문서를 상세하고 사용자 친화적으로 만듭니다.

- **기본 정보**: `summary`, `description`으로 각 API의 목적과 기능을 명확히 설명합니다.
- **응답 스키마**: `response_model`로 성공 시의 응답 구조를 정의합니다.
- **시나리오별 응답**: `responses`를 사용하여 `404 Not Found`와 같은 예외 상황의 응답 구조와 설명을 문서화합니다.