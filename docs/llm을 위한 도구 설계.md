### **스마트한 LLM 에이전트를 위한 견고한 도구(Tool) 설계: Service-Adapter-Handler 아키텍처**

LLM(거대 언어 모델) 에이전트가 외부 세계와 소통하기 위한 '도구'를 만들 때, 가장 흔히 저지르는 실수는 API 호출 코드를 그대로 도구에 연결하는 것입니다. 이 방식은 API 응답 구조가 조금만 바뀌어도 에이전트가 오작동하고, 불필요한 데이터 전송으로 비용이 증가하며, 코드를 테스트하고 유지보수하기 어렵게 만듭니다.

이 글에서는 이런 문제를 해결하고, 실제 프로덕션 환경에서도通用될 수 있는 견고한 아키텍처인 **"Service-Adapter-Handler"** 패턴을 소개합니다.

### **핵심 아이디어: 역할을 명확히 분리하라**

우리는 도구의 복잡한 작업을 세 가지 전문 영역으로 나눕니다.

1. **Service (데이터 공급자):** 외부 API에서 원본 데이터를 가져오는 역할만 전담합니다.
2. **Adapter (LLM 어댑터):** Service가 가져온 원본 데이터를 LLM이 가장 이해하기 쉬운 형태로 '변환'하고 '개조'합니다.
3. **Handler (요청 핸들러):** LLM 에이전트의 도구 호출 요청을 '처리'하며, Service와 Adapter를 지휘하여 최종 결과를 만들어냅니다.

이 구조는 소프트웨어 공학의 기본 원칙인 **관심사의 분리(Separation of Concerns)**를 충실히 따릅니다.

*(설명을 돕기 위한 가상 다이어그램)*

**[데이터 흐름]**`LLM 에이전트` -> `3. Handler` -> `1. Service` -> `외부 API외부 API` -> `1. Service` -> `3. Handler` -> `2. Adapter` -> `LLM 에이전트`

---

### **각 계층의 역할과 코드 예시**

### **1. Service 계층: 순수한 데이터 공급자**

- **역할:** 외부 API와의 통신을 책임집니다.
- **핵심 원칙:** 반환 값은 가공되지 않은, 그러나 구조화된 Python 객체(`dict`)입니다. **Adapter나 Handler의 존재를 전혀 알지 못합니다.**

**`src/app/services/musinsa_service.py`**


### **2. Adapter 계층: 능숙한 데이터 변환 전문가**

- **역할:** 이름 그대로, 한쪽(Service)의 인터페이스를 다른 쪽(LLM)이 기대하는 인터페이스로 '개조(adapt)'합니다. 
- **핵심 원칙:** 데이터의 '형태'를 바꾸는 데만 집중합니다. Service가 반환한 `dict`를 받아 필요한 내용만 llm에게 전달하고,  LLM이 이해하기 쉬운 구조 `str` or 'dict' 변환합니다.

**`src/graph/tools/adapters/product_adapter.py`**

### **3. Handler 계층: 똑똑한 요청 처리자**

- **역할:** LLM 에이전트의 도구 호출을 직접 받아 '처리(handle)'합니다. 어떤 Service를 호출하고, 어떤 Adapter를 사용해서 결과를 반환할지 결정하는 오케스트레이터입니다.
- **핵심 원칙:** 실제 로직은 다른 계층에 위임하고, 전체 작업 흐름을 조율하는 역할에 집중합니다.

**`src/graph/tools/handlers/product_handlers.py`**
```python
from src.app.services.musinsa_service import MusinsaService
from src.graph.tools.adapters.product_adapter import ProductAdapter

class ProductToolHandlers:
    def __init__(self, musinsa_service: MusinsaService):
        self.service = musinsa_service

    async def handle_get_product_stock(self, product_id: int) -> str:
        # 1. Service에 데이터 요청
        raw_data = await self.service.get_product_option_stock(product_id)
        # 2. Adapter에 변환 요청
        adapted_result = ProductAdapter.adapt_stock_info_for_llm(raw_data)
        # 3. 최종 결과 반환
        return adapted_result
```

### **2. 전체 동작 흐름**

이 아키텍처가 프로젝트에서 어떻게 유기적으로 동작하는지 데이터의 흐름을 따라가며 살펴보겠습니다.

**[전체 데이터 흐름도]**
```
(FastAPI 시작)
      |
      v
1. httpx.AsyncClient 생성 (애플리케이션 수명주기 동안 단 한번)
      |
      v
2. Graph Builder에 Client 전달 (`build_before_search_graph`)
      |
      v
3. Subgraph Builder에 Client 전달 (`build_product_info_agent_subgraph`)
      |
      v
4. [Service] MusinsaAPIWrapper 인스턴스 생성 (with Client)
      |
      v
5. [Handler] ProductToolHandlers 인스턴스 생성 (with MusinsaAPIWrapper)
      |
      v
6. [Tool] LangChain 도구 생성 (Handler의 메서드와 도구 명세를 연결)
      |
      v
7. LLM 에이전트 생성 (with Tools)
      |
      |--- (에이전트 실행 단계) ---
      |
      v
8. LLM이 도구 호출 결정 (예: "상품 재고 조회")
      |
      v
9. [Handler] 연결된 핸들러 메서드 실행 (`handle_get_product_stock`)
      |
      v
10. [Service] 핸들러가 서비스 메서드 호출 (`musinsa_service.get_product_option_stock`)
      |
      v
11. [외부 API] 서비스가 httpx.AsyncClient로 Musinsa API에 실제 HTTP 요청
      |
      v
12. [Adapter] 서비스가 받은 원본 데이터를 어댑터로 전달 (`ProductAdapter.adapt_stock_info`)
      |
      v
13. LLM에 최종 결과(가공된 문자열) 반환

```

### **3. 구현 단계별 상세 설명**

- **1단계: 비동기 클라이언트 공유**
FastAPI 애플리케이션이 시작될 때(`lifespan` 이벤트) `httpx.AsyncClient` 객체가 단 하나 생성됩니다. 이 객체는 API 요청에 재사용되어 효율성을 높이며, `build_before_search_graph` 빌더 함수에 인자로 전달됩니다.
- **2-5단계: 의존성 주입**
전달받은 `AsyncClient`는 `build_before_search_graph` -> `build_product_info_agent_subgraph`로 연쇄적으로 전달됩니다. 최종적으로 `build_product_info_agent_subgraph` 내부에서 이 `AsyncClient`를 사용하여 **Service**(`MusinsaAPIWrapper`)의 인스턴스를 생성합니다. 그리고 이 서비스 인스턴스를 **Handler**(`ProductToolHandlers`)의 생성자에 주입합니다. 이로써 핸들러는 서비스를 통해 외부 API와 통신할 수 있게 됩니다.
- **6-7단계: 도구 생성 및 에이전트 탑재**
LLM이 사용할 도구의 명세(이름, 설명, 인자)를 별도로 정의합니다. 그리고 LangChain의 `StructuredTool.from_function`을 사용하여 이 명세와 **Handler**의 특정 메서드를 하나로 묶어줍니다. 이렇게 생성된 최종 도구 목록을 `create_react_agent`에 전달하여 에이전트를 완성합니다.
- **8-13단계: 실제 도구 호출**
사용자 질문에 따라 LLM이 "상품 재고 조회" 도구를 호출하면, 실제로는 연결된 **Handler**의 `handle_get_product_stock` 메서드가 실행됩니다. 이 메서드는 내부에 주입된 **Service**(`MusinsaAPIWrapper`)를 사용해 Musinsa API에서 원본 재고 데이터를 가져옵니다. 그 후, 가져온 원본 데이터를 **Adapter**에게 넘겨 LLM이 이해하기 쉬운 간결한 문자열로 가공하고, 이 최종 결과물을 LLM에게 반환합니다.

### **결론**

이처럼 **Service-Adapter-Handler** 아키텍처는 각 계층이 하나의 책임만 갖도록 역할을 명확히 분리합니다. 이를 통해 우리는 다음과 같은 장점을 얻을 수 있습니다.

- **유지보수성:** API 명세가 변경되면 `Service`와 `Adapter`만 수정하면 되므로 영향 범위가 명확하고 적습니다.
- **테스트 용이성:** 각 계층을 독립적으로 테스트할 수 있습니다. (예: `Service`가 실제 API와 통신하는지, `Adapter`가 데이터를 잘 변환하는지 등)
- **비용 효율성:** `Adapter`를 통해 LLM에게 꼭 필요한 최소한의 정보만 전달하므로 불필요한 토큰 사용을 줄일 수 있습니다.
- **코드 재사용성:** `Service` 계층은 다른 도구나 애플리케이션의 다른 부분에서도 재사용될 수 있습니다.

이러한 방식으로 우리는 더 안정적이고, 확장 가능하며, 효율적인 LLM 에이전트를 구축할 수 있습니다.
