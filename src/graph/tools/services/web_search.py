# tabily , exa search의 결과에 맞게 parsing 해서 service 로직 정의
# 초기화 할때 client 전달받아서 사용하도록 하기

import httpx


class WebSearchService:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def search_by_query(self, query: str) -> dict:
        pass
