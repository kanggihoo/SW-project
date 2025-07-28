import logging
from db.config import Config
from db import create_fashion_repo
from datetime import datetime
logging.basicConfig()
logger = logger = logging.getLogger(__name__)

mongo_local = create_fashion_repo(use_atlas=False)
mongo_atlas = create_fashion_repo(use_atlas=True)

cursor = mongo_local.find_by_caption_status("COMPLETED")


def make_new_id(product_id , color_name):
    return f"{product_id}_{color_name}"

def denormalize_data(doc):
    #TODO : tests/unit/db/test_insert_data_to_atlas.py 참고 
    # if len(doc["caption_info"]["color_images"]["color_info"]) == 1:
    #     id = make_new_id(doc["product_id"], doc["caption_info"]["color_images"]["color_info"][0]["name"])
        
    #     d = {}
    #     d["representative_assets"] = doc["representative_assets"]
    #     d["_id"] = id
    #     caption_info = doc["caption_info"]
    #     d["text_images"] = caption_info["caption_info"]["text_images"]
    #     d["color_info"] = caption_info["caption_info"]["color_images"]["color_info"][0]
    #     d["deep_caption"] = caption_info["caption_info"]["deep_caption"]
    #     d["product_id"] = caption_info["product_id"]
    # else:
    #     total = len(doc["caption_info"]["color_images"]["color_info"])
    #     ids = [make_new_id(doc["product_id"], color_info["name"]) for color_info in doc["caption_info"]["color_images"]["color_info"]]
    #     result = []
    #     for idx in range(total):
    #         d = {}
    #         d["_id"] = ids[idx]
    #         d["text_images"] = doc["caption_info"]["text_images"]
    ...
for doc in cursor:
    mongo_atlas.create(doc)



