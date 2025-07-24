from .config.config import Config
from .repository.fashion import FashionRepository

_config = Config()
_mongodb_atlas_config = _config.get_atlas_config()
_mongodb_local_config = _config.get_local_config()
def create_fashion_repo_atlas()->FashionRepository:
    return FashionRepository(connection_string=_mongodb_atlas_config["MONGODB_ATLAS_CONNECTION_STRING"],
                            database_name=_mongodb_atlas_config["MONGODB_ATLAS_DATABASE_NAME"],
                            collection_name=_mongodb_atlas_config["MONGODB_ATLAS_COLLECTION_NAME"])

def create_fashion_repo_local()->FashionRepository:
    return FashionRepository(connection_string=_mongodb_local_config["MONGODB_LOCAL_CONNECTION_STRING"],
                            database_name=_mongodb_local_config["MONGODB_LOCAL_DATABASE_NAME"],
                            collection_name=_mongodb_local_config["MONGODB_LOCAL_COLLECTION_NAME"])

def create_fashion_repo(use_atlas: bool = False):
    if use_atlas:
        return create_fashion_repo_atlas()
    else:
        return create_fashion_repo_local()

