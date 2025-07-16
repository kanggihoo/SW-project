import os
from dotenv import load_dotenv

load_dotenv()
class Config(dict):
    def __init__(self):
        _mongodb_local_dict = {
            "MONGODB_LOCAL_DATABASE_NAME": "fashion_db",
            "MONGODB_LOCAL_COLLECTION_NAME": "products",
            "MONGODB_LOCAL_CONNECTION_STRING": "mongodb://localhost:27017/"
        }
        _mongodb_atlas_dict = {
            "MONGODB_ATLAS_DATABASE_NAME": "fashion_db",
            "MONGODB_ATLAS_COLLECTION_NAME": "products",
            "MONGODB_ATLAS_CONNECTION_STRING": os.getenv("MONGODB_ATLAS_URI")
        }

        
        super().__init__()
        self.update(_mongodb_local_dict)
        self.update(_mongodb_atlas_dict)
        
    