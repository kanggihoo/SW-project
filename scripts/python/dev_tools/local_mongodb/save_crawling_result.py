"""
로컬에서 가지고 있어야 하는거
1. 크롤링 결과 데이터 (simple , detail) json 파일
2. dynmodb로 부터 선택된 대표 이미지 정보
3. 대표 이미지로 부터 생성한 캡션 정보
4. 캡션 정보로 부터 생성한 임베딩 정보

mongodb atlas에 저장해야 하는 것?

"""

"""
simple_product_summary.csv 이 가지고 있는 정보 

detail_product_summary.csv 이 가지고 있는 정보 


"""
import logging
import pandas as pd
import json
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s : %(filename)s - %(lineno)d', datefmt='%Y-%m-%d %H:%M:%S'
)
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
logger = logging.getLogger(__name__)
from aws.dynamodb import DynamoDBManager
from db import create_fashion_repo
from aws.config import Config
from tqdm import tqdm
from pymongo import UpdateOne
from enum import Enum


class ProcessingDataStage(Enum):
    CR = 'crawling_complete'  # 크롤링한 결과를 local mongodb에 저장
    DOWN = 'image_download'  # 이미지 다운로드
    AWS = 'aws_upload'  # aws s3에 저장
    RE = 'representative_image'  # 대표 이미지 정보 저장
    EB = 'embedding_generation'  # 임베딩 정보 저장


class DataSaveStatus(Enum):
    CR_SUM = 'CR_SUM'  # 크롤링 summary 완료
    CR_DET = 'CR_DET'  # 크롤링 detail 완료
    IMG_DOWN = 'IMG_DOWN'  # 크롤링한 결과에 대한 이미지 다운로드 완료
    AWS_UPL = 'AWS_UPL'  # 다운로드 한 이미지 aws에 업로드 완료
    RE_COMP = 'RE_COMP'  # 대표 이미지 정보 저장 완료
    CA_COMP = 'CA_COMP'  # 선정된 대표 이미지에 대해 캡션 정보 저장 완료
    EB_COMP = 'EB_COMP'  # 캡션 완료된 제품에 대한 임베딩 정보 저장 완료


class DataSavePipeline:
    def __init__(self):
        self.ddb_config = Config().get_dynamodb_config()
        self.dynamodb_client = DynamoDBManager(self.ddb_config['region_name'], self.ddb_config['table_name'], self.ddb_config)
        self.mongodb = create_fashion_repo(use_atlas=False)

    def save_crawling_data(
        self,
        file_path: str | Path,
        is_already_uploaded: bool = False,
    ):
        """
        크롤링 결과를 local mongodb에 저장
        Args:
            file_path (str|Path): 크롤링 결과가 저장된 파일 경로
            is_already_uploaded (bool, optional): 이미지 다운로드 여부. Defaults to False.
        """
        input_data = {
            'file_path': file_path,
            'is_already_uploaded': is_already_uploaded,
        }
        if self._validate_data(input_data, ProcessingDataStage.CR):
            self._save_crawling_data(**input_data)

        else:
            raise ValueError(f'크롤링 결과 저장하기 위해 제공된 인자값에 오류가 있습니다. : {input_data}')

    def save_image_download_data(self, base_dir: str | Path, main_category: str | int):
        """크롤링한 이미지를 다운로드 한 결과를 로컬 mongodb에 반영 (data_status 업데이트)"""
        input_data = {
            'base_dir': base_dir,
            'main_category': main_category,
        }
        if self._validate_data(input_data, ProcessingDataStage.DOWN):
            data_dir = Path(base_dir) / main_category
            self._save_image_download_data(data_dir)
        else:
            raise ValueError(f'이미지 다운로드 결과 저장하기 위해 제공된 인자값에 오류가 있습니다. : {input_data}')

    def save_aws_upload_data(self, **kwargs):
        pass

    def save_representative_image_data(self, **kwargs):
        pass

    def save_emb_generation_data(self, **kwargs):
        pass

    def _save_crawling_data(self, file_path: str | Path, is_already_uploaded: bool):
        """크롤링한 결과를 로컬 mongodb에 저장"""
        df = self._load_json_to_df(file_path)
        df = self._process_df(df)

        BATCH_SIZE = 1000
        for batch_index in range(0, len(df), BATCH_SIZE):
            batch_df = df.iloc[batch_index : batch_index + BATCH_SIZE]
            logger.info(f'✅ 배치 완료 : {batch_index} - {batch_index + BATCH_SIZE}')
            updates_map = {}
            for row in batch_df.itertuples(index=True):
                index = row.Index
                product_id = str(row[1])
                sub_category = int(row.sub_category)
                if is_already_uploaded:
                    # 이미 S3에 업로드 되어 있는 main/sub category인 경우 => 해당 product_id가 실제로 존재하는지 확인
                    result_dynamo = self.dynamodb_client.get_item(sub_category=sub_category, product_id=product_id)
                    if result_dynamo is None:
                        logger.error(f'❌ {product_id} 데이터가 dynamoDB에 존재하지 않습니다.')
                        update_data['data_status'] = DataSaveStatus.CR_DET.value
                        updates_map[index] = update_data
                    else:
                        curation_status = result_dynamo.get('curation_status')
                        update_data = {}
                        if curation_status == 'COMPLETED':
                            # 누군가가 curation 작업을 완료 한 경우 : 대표 이미지 조회
                            representative_assets = result_dynamo.get('representative_assets')
                            update_data['representative_assets'] = representative_assets
                            update_data['data_status'] = DataSaveStatus.RE_COMP.value
                            updates_map[index] = update_data
                        elif curation_status == 'PASS' or curation_status == 'PENDING':
                            # dynamodb에 데이터가 존재하는 경우
                            update_data['data_status'] = DataSaveStatus.AWS_UPL.value
                            updates_map[index] = update_data
                        else:
                            logger.error(f'❌ curation_status 값이 올바르지 않습니다. : {curation_status}')

                # else: # 처음 크롤링한 결과를 반영하는 경우
                #     update_data["data_status"] = DataSaveStatus.CR_DET.value
                #     updates_map[index] = update_data

            if updates_map:
                update_df = pd.DataFrame.from_dict(updates_map, orient='index')
                batch_df.update(update_df)
            logger.info(f'배치 완료 : {batch_index} - {batch_index + BATCH_SIZE}')

            # mongodb 에 저장
            mongo_operations = []
            batch_docs = batch_df.to_dict(orient='records')

            for doc in batch_docs:
                filter_query = {'_id': str(doc['_id'])}
                update_data = {k: v for k, v in doc.items() if k != '_id'}
                update_operation = {'$set': update_data}
                mongo_operations.append(UpdateOne(filter_query, update_operation, upsert=True))

            if mongo_operations:
                try:
                    # ordered=False로 설정하여 일부 실패해도 계속 진행
                    result = self.mongodb.collection.bulk_write(mongo_operations, ordered=False)

                    # 성공한 작업들 로깅
                    logger.info(f'✅ 배치 {batch_index}-{batch_index + BATCH_SIZE} bulk_write 성공:')
                    logger.info(f'   - 수정된 문서: {result.modified_count}')
                    logger.info(f'   - 삽입된 문서: {result.upserted_count}')
                    logger.info(f'   - 매칭된 문서: {result.matched_count}')

                    # 실패한 작업들 처리
                    if hasattr(result, 'bulk_api_result') and 'writeErrors' in result.bulk_api_result:
                        failed_docs = []
                        for error in result.bulk_api_result['writeErrors']:
                            error_index = error['index']
                            error_doc = batch_docs[error_index]
                            failed_docs.append({'_id': str(error_doc['_id']), 'error_code': error['code'], 'error_message': error['errmsg']})
                            logger.error(f'❌ 문서 저장 실패 - _id: {error_doc["_id"]}, 오류: {error["errmsg"]}')

                        # 실패한 문서들을 별도 파일로 저장
                        if failed_docs:
                            failed_file_path = f'failed_docs_batch_{batch_index}_{batch_index + BATCH_SIZE}.json'
                            with open(failed_file_path, 'w', encoding='utf-8') as f:
                                json.dump(failed_docs, f, ensure_ascii=False, indent=2)
                            logger.warning(f'⚠️ 실패한 문서 {len(failed_docs)}개를 {failed_file_path}에 저장했습니다.')

                except Exception as e:
                    logger.error(f'❌ 배치 {batch_index}-{batch_index + BATCH_SIZE} bulk_write 중 예외 발생: {e}')
                    # 예외 발생 시에도 실패한 문서들을 저장
                    failed_docs = []
                    for i, doc in enumerate(batch_docs):
                        failed_docs.append({'_id': str(doc['_id']), 'error_code': 'EXCEPTION', 'error_message': str(e)})

                    failed_file_path = f'failed_docs_batch_{batch_index}_{batch_index + BATCH_SIZE}_exception.json'
                    with open(failed_file_path, 'w', encoding='utf-8') as f:
                        json.dump(failed_docs, f, ensure_ascii=False, indent=2)
                    logger.error(f'❌ 배치 전체 실패 - {len(failed_docs)}개 문서를 {failed_file_path}에 저장했습니다.')

                logger.info(f'배치 완료 : {batch_index} - {batch_index + BATCH_SIZE}')

    # def _save_image_download_data(self , data_dir:Path|str):
    #     '''크롤링한 이미지를 다운로드 한 결과를 로컬 mongodb에 반영 (data_status 업데이트)'''
    #     ...

    def _validate_data(self, input_data: dict, data_stage: ProcessingDataStage) -> bool:
        if data_stage == ProcessingDataStage.CR:
            file_path = input_data.get('file_path')
            if Path(file_path).exists() and Path(file_path).suffix == '.json':
                logger.info(f'✅ {file_path} 파일이 존재하고 확장자가 .json 입니다.')
            else:
                logger.error(f'❌ {file_path} 파일이 존재하지 않거나 확장자가 .json 이 아닙니다.')
                return False
            return True
        elif data_stage == ProcessingDataStage.DOWN:
            base_dir = input_data.get('base_dir')
            main_category = input_data.get('main_category')
            if main_category is not None:
                logger.info(f'✅ {main_category} 카테고리 정보가 존재합니다.')
            else:
                logger.error(f'❌ {main_category} 카테고리 정보가 존재하지 않습니다.')
                return False
            base_dir = Path(base_dir)
            data_dir = base_dir / main_category

            if base_dir.exists() and data_dir.exists():
                logger.info(f'✅ {data_dir} 디렉토리가 존재합니다.')
            else:
                logger.error(f'❌ {data_dir} 디렉토리가 존재하지 않습니다.')
                return False
            return True

        # elif data_stage == ProcessingDataStage.AWS:
        #     ...
        # elif data_stage == ProcessingDataStage.RE:
        #     ...
        # elif data_stage == ProcessingDataStage.EMB:
        #     ...

    def _load_json_to_df(self, file_path: str, index_column_name: str = 'product_id') -> pd.DataFrame:
        """
        JSON 파일을 pandas DataFrame으로 읽어서 product_id를 인덱스로 설정

        Args:
            file_path (str): JSON 파일 경로

        Returns:
            pd.DataFrame: product_id를 인덱스로 가진 DataFrame
        """
        try:
            df = pd.read_json(file_path, encoding='utf-8')

            # # product_id가 존재하는지 확인
            # if 'product_id' not in df.columns:
            #     raise ValueError(f"product_id 컬럼이 {file_path}에 존재하지 않습니다.")

            # # product_id를 인덱스로 설정
            # df.set_index(index_column_name, inplace=True)

            logger.info(f'✅ {file_path} 로드 완료 - {len(df)} 개의 제품 데이터')
            logger.info(f'📊 컬럼: {list(df.columns)}')

            return df

        except FileNotFoundError:
            logger.error(f'❌ 파일을 찾을 수 없습니다: {file_path}')
            return pd.DataFrame()
        except json.JSONDecodeError:
            logger.error(f'❌ JSON 파일 형식이 올바르지 않습니다: {file_path}')
            return pd.DataFrame()
        except Exception as e:
            logger.error(f'❌ 파일 로드 중 오류 발생: {e}')
            return pd.DataFrame()

    def _default_csv_projection_fields(self, columns: list[str]) -> list[str]:
        columns = set(columns)
        projection_columns = [
            'product_id',
            'product_price',
            'product_original_price',
            'product_brand_name',
            'product_name',
            'num_likes',
            'avg_rating',
            'review_count',
            'category_main',
            'category_sub',
            'gender',
            'detail_text',
            'review_texts',
            'size_detail_info',
            'fit_info',
            'color_size_info',
            'success_status',
        ]

        if all(col in columns for col in projection_columns):
            logger.info(f'summary_csv_projection_fields 에 필요한 컬럼이 모두 있습니다. : {projection_columns}')
            return projection_columns
        else:
            raise ValueError(f'summary_csv_projection_fields 에 필요한 컬럼이 없습니다. : {columns}')

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        mapping_columns = {
            'category_main': 'main_category',
            'category_sub': 'sub_category',
            'success_status': 'crawling_status',
            # mongoDB 호환성
            'product_id': '_id',
        }
        if all(col in df.columns for col in mapping_columns.keys()):
            try:
                df = df.rename(columns=mapping_columns)
                logger.info(f'컬럼명 변경완료 : {mapping_columns}')
                return df
            except Exception as e:
                raise ValueError(f'rename_columns 도중 오류 발생: {e}')
        else:
            missing_cols = [col for col in mapping_columns.keys() if col not in df.columns]
            raise ValueError(f'rename_columns에 필요한 컬럼이 DataFrame에 없습니다: {missing_cols}')

    def _add_new_columns(self, df: pd.DataFrame, new_columns: str = None) -> pd.DataFrame:
        if new_columns is None:
            new_columns = 'data_status'

        df[new_columns] = df.apply(
            lambda x: DataSaveStatus.CR_DET.value if x['crawling_status'] == 'success' else DataSaveStatus.CR_SUM.value, axis=1
        )
        return df

    def _add_new_none_columns(self, df: pd.DataFrame, new_columns: str = None) -> pd.DataFrame:
        if new_columns is None:
            new_columns = 'representative_assets'

        df[new_columns] = None
        return df

    def _process_df(self, df: pd.DataFrame) -> pd.DataFrame:
        projection_columns = self._default_csv_projection_fields(df.columns)
        df = df[projection_columns]
        df = self._rename_columns(df)
        df = self._add_new_columns(df, new_columns='data_status')
        df = self._add_new_none_columns(df, new_columns='representative_assets')
        return df


if __name__ == '__main__':
    data_save_pipeline = DataSavePipeline()
    main_category = '상의'
    sub_category = '민소매티셔츠'
    is_already_uploaded = False
    BASE_DIR = Path('/Users/kkh/Desktop/musinsa-crawling/data')
    detail_json_file_name = f'musinsa_product_detail_{main_category}_{sub_category}.json'
    detail_json_file_path = BASE_DIR / detail_json_file_name
    data_save_pipeline.save_crawling_data(file_path=detail_json_file_path, is_already_uploaded=is_already_uploaded)
