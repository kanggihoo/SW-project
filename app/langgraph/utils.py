
from typing import Any
from langgraph.graph import StateGraph

def embedding_query(query: str) -> list[float]:
    return [hash(word) / 1e18 for word in query.split()][:5]


def search_vector_db(query: str , k:int = 3) -> list[dict[str, Any]]:
    return [
        {"product_id": "item_A", "name": "Classic White Shirt", "description": "A timeless white shirt."},
        {"product_id": "item_B", "name": "Ripped Denim Jeans", "description": "Stylish ripped jeans."},
        {"product_id": "item_C", "name": "Summer Floral Dress", "description": "Light and airy summer dress for warm weather."},
        {"product_id": "item_D", "name": "Silk Blouse", "description": "Elegant silk blouse."},
        {"product_id": "item_E", "name": "Slim-fit Jeans", "description": "Modern slim-fit jeans."},
        {"product_id": "item_F", "name": "Evening Gown", "description": "Formal evening gown."},
        {"product_id": "item_G", "name": "Casual T-shirt", "description": "Comfortable casual t-shirt."},
    ][:k]
    

def get_product_details(product_ids: list[str]) -> list[dict[str, Any]]:
    return [
        {"product_id": "item_A", "name": "Classic White Shirt", "description": "A timeless white shirt."},
        {"product_id": "item_B", "name": "Ripped Denim Jeans", "description": "Stylish ripped jeans."},
        {"product_id": "item_C", "name": "Summer Floral Dress", "description": "Light and airy summer dress for warm weather."},
    ]

def rerank_items(
    items_with_metadata: list[dict[str, Any]],
    external_info: dict[str, Any]
    ) -> list[dict[str, Any]]:
    
    return items_with_metadata


def modify_query(query: str, user_feedback: str) -> str:
    return f"{query} | {user_feedback}"

def save_graph_image(graph: StateGraph , file_name: str):
    graph.get_graph().draw_mermaid_png(file_name)
