import logging
from db.config import Config
from db import create_fashion_repo
from embedding import get_embedding_with_jina
from datetime import datetime
logging.basicConfig()
logger = logger = logging.getLogger(__name__)

mongo_local = create_fashion_repo(use_atlas=False)
cursor = mongo_local.find_by_caption_status("COMPLETED")

total_count = 0
success_count = 0
fail_count = 0
for doc in cursor:
    try:
        embedding_field = doc.get("caption_info")["deep_caption"]["image_captions"]["comprehensive_description"]
        embedding = get_embedding_with_jina(embedding_field)[0]
        product_id = doc["product_id"]

        #TODO : 이부분은 쿼리 builder에 작성 해서 간단하게 
        result = {
            "embedding": {
                "comprehensive_description": {
                    "vector": embedding,
                    "status": "COMPLETED",
                    "generated_at": datetime.now().isoformat()
                }
            },

        }
        mongo_local.update_by_id(product_id, result)
        success_count += 1
    except Exception as e:
        logger.error(f"Error generating embedding for product {doc['product_id']}: {e}")
        fail_count += 1

logger.info(f"Total count: {success_count + fail_count}, Success count: {success_count}, Fail count: {fail_count}")
    

    





