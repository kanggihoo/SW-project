from .config.config import Config
from .repository.fashion import FashionRepository


def create_fashion_repo_atlas():
    config = Config()
    return FashionRepository(connection_string=config["MONGODB_ATLAS_CONNECTION_STRING"],
                            database_name=config["MONGODB_ATLAS_DATABASE_NAME"],
                            collection_name=config["MONGODB_ATLAS_COLLECTION_NAME"])

def create_fashion_repo_local():
    config = Config()
    return FashionRepository(connection_string=config["MONGODB_LOCAL_CONNECTION_STRING"],
                            database_name=config["MONGODB_LOCAL_DATABASE_NAME"],
                            collection_name=config["MONGODB_LOCAL_COLLECTION_NAME"])

def create_fashion_repo(use_atlas: bool = False):
    if use_atlas:
        return create_fashion_repo_atlas()
    else:
        return create_fashion_repo_local()

