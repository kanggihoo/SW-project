import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
logger = logging.getLogger(__name__)
from db import create_fashion_repo 

mongo_local = create_fashion_repo(use_atlas=False)




result =mongo_local.collection.find({
    "$expr": {
        "$ne": [
            { "$size": { "$ifNull": ["$representative_assets.color_variant", []] } },
            { "$size": { "$ifNull": ["$caption_info.color_images.color_info", []] } }
    ]
  }
})

for doc in result:
    print(doc["_id"])