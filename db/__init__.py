from .config.config import Config
from .repository.fashion_sync import FashionRepository as SyncFashionRepository
from .repository.fashion_async import AsyncFashionRepository

_config = Config()
_mongodb_atlas_config = _config.get_atlas_config()
_mongodb_local_config = _config.get_local_config()

# ===================================================================
# 비동기/FastAPI 환경을 위한 팩토리 함수
# ===================================================================

async def get_async_fashion_repo() -> AsyncFashionRepository:
    """
    [비동기] Atlas DB에 연결하는 비동기 Fashion Repository를 반환합니다.
    FastAPI와 같은 비동기 프레임워크에서 사용하기 위해 설계되었습니다.
    """
    repo = AsyncFashionRepository(
        connection_string=_mongodb_atlas_config["MONGODB_ATLAS_CONNECTION_STRING"],
        database_name=_mongodb_atlas_config["MONGODB_ATLAS_DATABASE_NAME"],
        collection_name=_mongodb_atlas_config["MONGODB_ATLAS_COLLECTION_NAME"]
    )
    await repo.connect()  # 비동기 연결 초기화
    return repo

# ===================================================================
# 동기/개인 작업 환경을 위한 팩토리 함수 (기존 코드 호환성 유지)
# ===================================================================

def create_fashion_repo_atlas() -> SyncFashionRepository:
    """
    [동기] Atlas DB에 연결하는 동기 Fashion Repository를 반환합니다.
    개인 스크립트, 테스트, 데이터 분석 등 동기 환경에서 사용합니다.
    """
    return SyncFashionRepository(
        connection_string=_mongodb_atlas_config["MONGODB_ATLAS_CONNECTION_STRING"],
        database_name=_mongodb_atlas_config["MONGODB_ATLAS_DATABASE_NAME"],
        collection_name=_mongodb_atlas_config["MONGODB_ATLAS_COLLECTION_NAME"]
    )

def create_fashion_repo_local() -> SyncFashionRepository:
    """
    [동기] 로컬 DB에 연결하는 동기 Fashion Repository를 반환합니다.
    """
    return SyncFashionRepository(
        connection_string=_mongodb_local_config["MONGODB_LOCAL_CONNECTION_STRING"],
        database_name=_mongodb_local_config["MONGODB_LOCAL_DATABASE_NAME"],
        collection_name=_mongodb_local_config["MONGODB_LOCAL_COLLECTION_NAME"]
    )

def create_fashion_repo(use_atlas: bool = False) -> SyncFashionRepository:
    """
    [동기] `use_atlas` 플래그에 따라 Atlas 또는 로컬 DB에 연결하는
    동기 Fashion Repository를 선택적으로 반환합니다.
    """
    if use_atlas:
        return create_fashion_repo_atlas()
    else:
        return create_fashion_repo_local()

# --- 별칭 (Alias) ---
# 새로운 이름으로도 접근 가능하도록 별칭을 제공합니다.
get_sync_fashion_repo = create_fashion_repo_local
