#TODO : 캐쉬 디렉토리에 있는지 확인 후 없으면 s3에서 다운로드 후 캐쉬 디렉토리에 저장


cache_dir = "C:\Users\11kkh\.cache\ai_dataset_curation\product_images"


def load_image_from_cache(product_id: str, folder: str, filename: str):
    ...
    

def download_image_from_s3(url: str):
    ...

