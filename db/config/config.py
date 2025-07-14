class Config(dict):
    def __init__(self):
        _mongodb_dict = {
            "MONGODB_LOCAL_DATABASE_NAME": "fashion_db",
            "MONGODB_LOCAL_COLLECTION_NAME": "products",
            "MONGODB_LOCAL_CONNECTION_STRING": "mongodb://localhost:27017/"
        }
        
        super().__init__()
        self.update(_mongodb_dict)
        
    