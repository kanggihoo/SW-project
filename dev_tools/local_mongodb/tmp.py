import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
logger = logging.getLogger(__name__)
from db import create_fashion_repo 

mongo_local = create_fashion_repo(use_atlas=False)




result = mongo_local.collection.aggregate([
    {
        "$match": {
            "main_category" : {"$exists" : False}
        }
    },
    {
        "$group": {
            "_id": {
                "main_category": "$category_main",
                "sub_category": "$category_sub"
            },
            "count": {"$sum": 1}
        }
    },
    {
        "$project": {
            "_id": 0,
            "main_category": "$_id.main_category",
            "sub_category": "$_id.sub_category",
            "count": 1
        }
    }
])

for doc in result:
    print(doc)

