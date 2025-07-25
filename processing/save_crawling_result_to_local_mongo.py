'''
로컬에서 가지고 있어야 하는거 
1. 크롤링 결과 데이터 (simple , detail) json 파일 
2. dynmodb로 부터 선택된 대표 이미지 정보 
3. 대표 이미지로 부터 생성한 캡션 정보 
4. 캡션 정보로 부터 생성한 임베딩 정보 

mongodb atlas에 저장해야 하는 것?

'''

'''
simple_product_summary.csv 이 가지고 있는 정보 

detail_product_summary.csv 이 가지고 있는 정보 


'''
import logging
import pandas as pd
import json
from typing import Dict, Any, Optional
import logging
from pathlib import Path
logging.basicConfig(level=logging.INFO , format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s : %(filename)s - %(lineno)d' , datefmt='%Y-%m-%d %H:%M:%S')
import sys
sys.path.append(str(Path(__file__).parent.parent))
logger = logging.getLogger(__name__)
from aws.dynamodb import DynamoDBManager
from db import create_fashion_repo
from aws.config import Config
from tqdm import tqdm
from pymongo import UpdateOne

def load_json_to_df(file_path: str , index_column_name: str = "product_id") -> pd.DataFrame:
    """
    JSON 파일을 pandas DataFrame으로 읽어서 product_id를 인덱스로 설정
    
    Args:
        file_path (str): JSON 파일 경로
        
    Returns:
        pd.DataFrame: product_id를 인덱스로 가진 DataFrame
    """
    try:
        df = pd.read_json(file_path , encoding="utf-8")
        
        # # product_id가 존재하는지 확인
        # if 'product_id' not in df.columns:
        #     raise ValueError(f"product_id 컬럼이 {file_path}에 존재하지 않습니다.")
        
        # # product_id를 인덱스로 설정
        # df.set_index(index_column_name, inplace=True)
        
        logger.info(f"✅ {file_path} 로드 완료 - {len(df)} 개의 제품 데이터")
        logger.info(f"📊 컬럼: {list(df.columns)}")
        
        return df
        
    except FileNotFoundError:
        logger.error(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return pd.DataFrame()
    except json.JSONDecodeError:
        logger.error(f"❌ JSON 파일 형식이 올바르지 않습니다: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"❌ 파일 로드 중 오류 발생: {e}")
        return pd.DataFrame()

def _default_csv_projection_fields(columns: list[str])->list[str]:
    columns = set(columns)
    projection_columns = [
        "product_id",
        "product_price",
        "product_original_price",
        "product_discount_price",
        "product_brand_name",
        "product_name",
        "num_likes",
        "avg_rating",
        "review_count",
        "category_main",
        "category_sub",
        "gender",
        "detail_text",
        "review_texts",
        "size_detail_info",
        "fit_info",
        "color_size_info",
        "success_status"
    ]
    
    if all(col in columns for col in projection_columns):
        logger.info(f"summary_csv_projection_fields 에 필요한 컬럼이 모두 있습니다. : {projection_columns}")
        return projection_columns
    else:
        raise ValueError(f"summary_csv_projection_fields 에 필요한 컬럼이 없습니다. : {columns}")
# def _default_dynamodb_projection_fields(columns: list[str])->list[str]:
#     columns = set(columns)
#     projection_columns = [
#         "caption_status",
#         "curation_status",
#         "product_original_price",
#         "product_discount_price",
#     ]

def _rename_columns(df: pd.DataFrame)->pd.DataFrame:

    mapping_columns = {
        "category_main": "main_category",
        "category_sub": "sub_category",
        "success_status" : "crawling_status",
        # mongoDB 호환성 
        "product_id" : "_id",
    }
    if all(col in df.columns for col in mapping_columns.keys()):
        try:
            df = df.rename(columns=mapping_columns)
            logger.info(f"컬럼명 변경완료 : {mapping_columns}")
            return df
        except Exception as e:
            raise ValueError(f"rename_columns 도중 오류 발생: {e}")
    else:
        missing_cols = [col for col in mapping_columns.keys() if col not in df.columns]
        raise ValueError(f"rename_columns에 필요한 컬럼이 DataFrame에 없습니다: {missing_cols}")
        

def _add_new_columns(df: pd.DataFrame , new_columns: str=None)->pd.DataFrame:
    if new_columns is None:
        new_columns = "data_status"

    df[new_columns] = df.apply(lambda x : "CR_DET" if x["crawling_status"]=="success" else "CR_SUM" , axis = 1)
    return df
def _add_new_none_columns(df: pd.DataFrame , new_columns: str=None)->pd.DataFrame:
    if new_columns is None:
        new_columns = "representative_assets"

    df[new_columns] = None
    return df
def _process_df(df: pd.DataFrame)->pd.DataFrame:
    projection_columns = _default_csv_projection_fields(df.columns)
    df = df[projection_columns]
    df = _rename_columns(df)
    df = _add_new_columns(df , new_columns="data_status")
    df = _add_new_none_columns(df , new_columns="representative_assets")
    return df

if __name__ == "__main__":

    # 초기 설정
    ddb_config = Config().get_dynamodb_config()
    dynamodb_client = DynamoDBManager(ddb_config["region_name"],ddb_config["table_name"] , ddb_config)
    mongodb = create_fashion_repo(use_atlas=False)
    # =============================================================================
    # 데이터 경로 설정 
    # =============================================================================
    BASE_DIR = Path("/Users/kkh/Desktop/musinsa-crawling/data")
    main_category = "상의"
    sub_category = "셔츠-블라우스"
    detail_json_file_name = f"musinsa_product_detail_{main_category}_{sub_category}.json"
    detail_json_path = BASE_DIR / detail_json_file_name

    # =============================================================================
    # 데이터 로드 및 초기 전처리 
    # ============================================================================
    product_detail_df = load_json_to_df(detail_json_path)
    product_detail_df = _process_df(product_detail_df)
    total = len(product_detail_df)
    # =============================================================================
    # 반복문을 통해 dynamodb로 부터 데이터 조회 
    # =============================================================================
    BATCH_SIZE = 1000
    # with tqdm(total=len(product_detail_df), desc="데이터 조회 중") as pbar:
    for batch_index in range(0, total, BATCH_SIZE):
        batch_df = product_detail_df.iloc[batch_index:batch_index+BATCH_SIZE]
        updates_map = {}
        for row in batch_df.itertuples(index=True):
            index = row.Index
            product_id = str(row[1])
            sub_category = int(row.sub_category)
            result_dynamo = dynamodb_client.get_item(sub_category=sub_category, product_id=product_id)
            if result_dynamo is None:
                continue
            curation_status = result_dynamo.get("curation_status")
            update_data = {}
            if curation_status == "COMPLETED":
                # 누군가가 curation 작업을 완료 한 경우 : 대표 이미지 조회 
                representative_assets = result_dynamo.get("representative_assets")
                update_data["representative_assets"] = representative_assets
                update_data["data_status"] = "RE_COMP"
                updates_map[index] = update_data
            elif curation_status == "PASS" or curation_status == "PENDING":
                # dynamodb에 데이터가 존재하는 경우 
                update_data["data_status"] = "AWS_UPL"
                updates_map[index] = update_data
            else:
                raise ValueError(f"curation_status 값이 올바르지 않습니다. : {curation_status}")

        if updates_map:
            update_df = pd.DataFrame.from_dict(updates_map, orient="index")
            batch_df.update(update_df)
            logger.info(f"배치 완료 : {batch_index} - {batch_index+BATCH_SIZE}")

        # mongodb 에 저장 
        mongo_operations = [] 
        batch_docs = batch_df.to_dict(orient="records")

        for doc in batch_docs:
            filter_query = {"_id": str(doc["_id"])}
            update_data = {k:v for k ,v in doc.items() if k != "_id"}
            update_operation = {"$set" : update_data}
            mongo_operations.append(
                UpdateOne(filter_query, update_operation , upsert=True)
            )

        if mongo_operations:
            try:
                # ordered=False로 설정하여 일부 실패해도 계속 진행
                result = mongodb.collection.bulk_write(mongo_operations, ordered=False)
                
                # 성공한 작업들 로깅
                logger.info(f"✅ 배치 {batch_index}-{batch_index+BATCH_SIZE} bulk_write 성공:")
                logger.info(f"   - 수정된 문서: {result.modified_count}")
                logger.info(f"   - 삽입된 문서: {result.upserted_count}")
                logger.info(f"   - 매칭된 문서: {result.matched_count}")
                
                # 실패한 작업들 처리
                if hasattr(result, 'bulk_api_result') and 'writeErrors' in result.bulk_api_result:
                    failed_docs = []
                    for error in result.bulk_api_result['writeErrors']:
                        error_index = error['index']
                        error_doc = batch_docs[error_index]
                        failed_docs.append({
                            '_id': str(error_doc['_id']),
                            'error_code': error['code'],
                            'error_message': error['errmsg']
                        })
                        logger.error(f"❌ 문서 저장 실패 - _id: {error_doc['_id']}, 오류: {error['errmsg']}")
                    
                    # 실패한 문서들을 별도 파일로 저장
                    if failed_docs:
                        failed_file_path = f"failed_docs_batch_{batch_index}_{batch_index+BATCH_SIZE}.json"
                        with open(failed_file_path, 'w', encoding='utf-8') as f:
                            json.dump(failed_docs, f, ensure_ascii=False, indent=2)
                        logger.warning(f"⚠️ 실패한 문서 {len(failed_docs)}개를 {failed_file_path}에 저장했습니다.")
                
            except Exception as e:
                logger.error(f"❌ 배치 {batch_index}-{batch_index+BATCH_SIZE} bulk_write 중 예외 발생: {e}")
                # 예외 발생 시에도 실패한 문서들을 저장
                failed_docs = []
                for i, doc in enumerate(batch_docs):
                    failed_docs.append({
                        '_id': str(doc['_id']),
                        'error_code': 'EXCEPTION',
                        'error_message': str(e)
                    })
                
                failed_file_path = f"failed_docs_batch_{batch_index}_{batch_index+BATCH_SIZE}_exception.json"
                with open(failed_file_path, 'w', encoding='utf-8') as f:
                    json.dump(failed_docs, f, ensure_ascii=False, indent=2)
                logger.error(f"❌ 배치 전체 실패 - {len(failed_docs)}개 문서를 {failed_file_path}에 저장했습니다.")
            
            logger.info(f"배치 완료 : {batch_index} - {batch_index+BATCH_SIZE}")


  