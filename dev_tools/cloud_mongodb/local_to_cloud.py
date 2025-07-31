import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
import logging
from db import create_fashion_repo
from pymongo import UpdateOne

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

local = create_fashion_repo(use_atlas=False)
cloud = create_fashion_repo(use_atlas=True)


# 로컬로부터 데이터 가져오기 
result_cursor = local.find_by_data_status("RE_COMP")

BATCH_SIZE = 50 
operations = []
local_id_to_update = []
#TODO : altas에 어떤식으로 데이터 저장할지 구조화 
def data_process(doc):
    return doc

for doc in result_cursor:
    processed_doc = data_process(doc.copy())
    update_data = {k:v for k ,v in processed_doc.items() if k != "_id"}
    operations.append(UpdateOne({"_id": doc["_id"]}, {"$set": update_data} , upsert=True))
    local_id_to_update.append(processed_doc["_id"])

    if len(operations) >= BATCH_SIZE:
        try:
            #TODO : 예외처리가 좀더 필요할거 같은데 , 2번의 bulk_write 중 하나라도 실패하면 어디서 실패하는지? 어떻게 알지 
            result = cloud.collection.bulk_write(operations , ordered=False)
            # 성공한 작업들 로깅
            logger.info(f"✅ Cloud DB에  {BATCH_SIZE} 개 bulk_write 성공:")
            logger.info(f"   - 수정된 문서: {result.modified_count}")
            logger.info(f"   - 삽입된 문서: {result.upserted_count}")
            logger.info(f"   - 매칭된 문서: {result.matched_count}")
            # 로컴에서도 데이터 반영 
            local_update_operations = [UpdateOne({"_id": local_id}, {"$set": {"data_status": "CL_COMP"}}) for local_id in local_id_to_update]
            local.collection.bulk_write(local_update_operations , ordered=False)

            logger.info(f"✅ Local DB에  {BATCH_SIZE} 개 bulk_write 성공(data_status 업데이트):")
            logger.info(f"   - 수정된 문서: {result.modified_count}")
            logger.info(f"   - 삽입된 문서: {result.upserted_count}")
            logger.info(f"   - 매칭된 문서: {result.matched_count}")
        except Exception as e:
            logger.error(f"❌ 배치 중 예외 발생: {e}")
        
        finally:
            operations = []
            local_id_to_update = []

if operations:
    try:
        result = cloud.collection.bulk_write(operations , ordered=False)
        logger.info(f"✅ Cloud DB에  {len(operations)} 개 bulk_write 성공:")
        logger.info(f"   - 수정된 문서: {result.modified_count}")
        logger.info(f"   - 삽입된 문서: {result.upserted_count}")
        logger.info(f"   - 매칭된 문서: {result.matched_count}")

        local_update_operations = [UpdateOne({"_id": local_id}, {"$set": {"data_status": "CL_COMP"}}) for local_id in local_id_to_update]
        local.collection.bulk_write(local_update_operations , ordered=False)

        logger.info(f"✅ Local DB에  {len(local_id_to_update)} 개 bulk_write 성공(data_status 업데이트):")
        logger.info(f"   - 수정된 문서: {result.modified_count}")
        logger.info(f"   - 삽입된 문서: {result.upserted_count}")
        logger.info(f"   - 매칭된 문서: {result.matched_count}")
    except Exception as e:
        logger.error(f"❌ 배치 중 예외 발생: {e}")

        
        
        
        

    

    
    
    





    








