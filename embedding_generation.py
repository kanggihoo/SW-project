import logging
from db.config import Config
from db import create_fashion_repo
from embedding import get_embedding_with_jina
from datetime import datetime
import asyncio
import aiohttp
from typing import Iterator
from embedding.embedding import JinaEmbedding
#TODO : 그냥 data_status로만 가져올지, 아니면 main , sub , data_status 조합으로 가져올지 ? (인덱스는 있음)



async def producer(queue:asyncio.Queue , cursor:Iterator) -> int:
    total_count = 0
    for doc in cursor:
        await queue.put(doc)
        total_count += 1
    logger.info(f"Producer: Finished putting all doc. Total count: {total_count}")
    return total_count

async def consumer(queue:asyncio.Queue,session:aiohttp.ClientSession , semaphore:asyncio.Semaphore):
    success_count = 0
    failed_count = 0
    while True:
        doc = await queue.get()
        if doc is None:
            queue.put_nowait(None)
            logger.info(f"Consumer: Finished processing all docs. Total count: {success_count} , Failed count: {failed_count}")
            break
        try:
            if doc.get("caption_info") is None:
                logger.error(f"data_status 가 CA_COMP 이지만 caption_info 가 없는 제품 : {doc['product_id']}")
                continue
            async with semaphore:
                embedding_type = "comprehensive_description"
                embedding_field = doc.get("caption_info")["deep_caption"]["image_captions"][embedding_type]
                emb_result = await jina_embedding.get_embedding(embedding_field , session)
                result = {
                    "embedding": {
                        embedding_type: {
                            "model_name": emb_result["model_name"],
                            "demension": emb_result["dimensions"],
                            "vector": emb_result["embeddings"][0],
                            "status": "COMPLETED",
                            "generated_at": datetime.now().isoformat()
                        }
                    },
                }
                result["data_status"] = "EB_COMP"
                product_id = doc["product_id"]
                mongo_local.update_by_id(product_id, result)
            success_count += 1
        except Exception as e:
            logger.error(f"Error generating embedding for product {doc['product_id']}: {e}")
            failed_count += 1
        finally:
            queue.task_done()
    return success_count , failed_count


async def generate_embedding(q_maxsize:int,
                             num_consumers:int,
                             max_concurrent_requests:int,
                             session:aiohttp.ClientSession,
                             )->tuple[int,int,int]:
    """
    Args:
        q_maxsize (int): 큐의 최대 크기
        num_consumers (int): 소비자 수 
        max_concurrent_requests (int): 동시 요청 수 (세마포)
        session (aiohttp.ClientSession): 세션

    Returns:
        tuple[int,int,int]: 총 개수, 성공 개수, 실패 개수
    """
    success_count = 0
    failed_count = 0
    # 큐 , 세마포어 생성 
    queue = asyncio.Queue(maxsize=q_maxsize)
    semaphore = asyncio.Semaphore(max_concurrent_requests)
    # mongo_local 에서 데이터 가져오기 
    cursor = mongo_local.find_by_data_status("CA_COMP")
    
    producer_task = asyncio.create_task(producer(queue , cursor))
    consumers = []
    for i in range(num_consumers):
        consumers.append(asyncio.create_task(consumer(queue , session , semaphore)))

    total_count = await producer_task

    # 모든 소비자가 큐의 항목 처리할떄 까지 대기 
    await queue.join()

    # 소비자들에게 종료 신호 보내기
    await queue.put(None)
    
    #모든 소비자 태스크가 실제로 종료될 때까지 기다립니다.
    results = await asyncio.gather(*consumers , return_exceptions=True)
    for result in results:
        success_count += result[0]
        failed_count += result[1]
    return total_count , success_count , failed_count

async def main():
    async with aiohttp.ClientSession() as session:
        results = await generate_embedding(q_maxsize=100,
                                          num_consumers=10,
                                          max_concurrent_requests=5,
                                          session=session)
        logger.info(f"Total results: {results[0]} , Success results: {results[1]} , Failed results: {results[2]}")
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    mongo_local = create_fashion_repo(use_atlas=False)
    jina_embedding = JinaEmbedding()
    asyncio.run(main())







# total_count = 0
# success_count = 0
# fail_count = 0
# for doc in cursor:
#     try:
#         if doc.get("caption_info") is None:
#             logger.error(f"data_status 가 CA_COMP 이지만 caption_info 가 없는 제품 : {doc['product_id']}")
#             continue
#         embedding_field = doc.get("caption_info")["deep_caption"]["image_captions"]["comprehensive_description"]
#         embedding = get_embedding_with_jina(embedding_field)[0]
#         product_id = doc["product_id"]

#         #TODO : 이부분은 쿼리 builder에 작성 해서 간단하게 
#         result = {
#             "embedding": {
#                 "comprehensive_description": {
#                     "vector": embedding,
#                     "status": "COMPLETED",
#                     "generated_at": datetime.now().isoformat()
#                 }
#             },

#         }
#         # mongo_local.update_by_id(product_id, result)
#         success_count += 1
#     except Exception as e:
#         logger.error(f"Error generating embedding for product {doc['product_id']}: {e}")
#         fail_count += 1

# logger.info(f"Total count: {success_count + fail_count}, Success count: {success_count}, Fail count: {fail_count}")
    

    

