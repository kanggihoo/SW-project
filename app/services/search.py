# from app.config.dependencies import S3ManagerDep , RepositoryDep
import logging

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self , s3_manager , repository):
        self.s3_manager = s3_manager
        self.repository = repository

    def vector_search(self, query: str, limit: int = 5):
        #TODO : 유사도 검색할 후보 개수 받을 수 있도록 변경하고 
        max_similarity_data= self.repository.vector_search(query)[0]
        print(max_similarity_data)
        representative_image_url = self._parsing_representative_image_url(max_similarity_data)
        max_similarity_data["image_url"] = representative_image_url
        return max_similarity_data

    def _parsing_representative_image_url(self , data:dict):
        try:
            representative_image = data.get("representative_assets")["color_variant"][0]
            product_id = data.get("product_id")
            main_category = data.get("main_category")
            sub_category = data.get("sub_category")
            s3_key = f"{main_category}/{sub_category}/{product_id}/{representative_image}"
            print(s3_key)
            return self._generate_s3_url(s3_key)
        except Exception as e:
            logger.error(f"Error parsing representative image: {e}")
            return None


    def _generate_s3_url(self , s3_key:str):
        s3_url = self.s3_manager.generate_presigned_url(s3_key)
        return s3_url
        
        
