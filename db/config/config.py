class Config(dict):
    def __init__(self):
        _mongodb_dict = {
            "MONGODB_DATABASE_NAME": "test_sw",
            "MONGODB_COLLECTION_NAME": "test_collections"
        }
        
        super().__init__()
        self.update(_mongodb_dict)
        
    