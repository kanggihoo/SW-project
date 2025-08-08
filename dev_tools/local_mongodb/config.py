import os
from dotenv import load_dotenv

class Config(dict):
    def __init__(self):
        _mongodb_local_dict = {
            "MONGODB_LOCAL":
             {
                "DATABASE_NAME": "fashion_db",
                "COLLECTION_NAME": "products",
                "CONNECTION_STRING": "mongodb://localhost:27017/"
            },
            "MONGODB_LOCAL_META":
            {
                "DATABASE_NAME": "fashion_db",
                "COLLECTION_NAME": "product_metadata",
                "CONNECTION_STRING": "mongodb://localhost:27017/"
            }
        }
    

        
        super().__init__()
        self.update(_mongodb_local_dict)
    
    def get_mongodb_local_dict(self):
        return self["MONGODB_LOCAL"]
    
    def get_mongodb_local_meta_dict(self):
        return self["MONGODB_LOCAL_META"]
    
    
    

        
    