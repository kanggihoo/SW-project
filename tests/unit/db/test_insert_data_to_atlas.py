import pytest
from db.config.database import DatabaseManager
import logging 
from dotenv import load_dotenv
import sys
@pytest.fixture(scope="session" , autouse=True)
def setup():
    load_dotenv()
    root = logging.getLogger()
    root.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def sample_data():
    d = {}
    d["deep_caption"] = {
        "image_captions": {
            "comprehensive_description": "라운드넥에 긴소매 기장을 가진 블랙 색상의 상의입니다. 정면은 심플하며 후면에 텍스트 레터링이 있어 포인트를 더했습니다. 레귤러 핏으로 편안하게 착용 가능하며, 캐주얼하고 모던한 스타일을 연출하기 좋습니다. 데일리룩이나 편안한 주말룩으로 활용하기 좋습니다.",
            "design_details_description": "라운드넥에 긴소매 기장을 가진 블랙 색상의 상의입니다. 정면은 심플하며 후면에 텍스트 레터링이 있어 포인트를 더했습니다.",
            "back_text_specific": "후면에 텍스트 레터링이 있는 블랙 색상의 상의",
            "front_text_specific": "심플한 디자인의 블랙 색상 상의",
            "tpo_context_description": "데일리룩이나 편안한 주말룩으로 활용하기 좋습니다.",
            "style_description": "라운드넥에 긴소매 기장을 가진 상의로, 레귤러 핏으로 편안하게 착용 가능하며, 캐주얼하고 모던한 스타일을 연출하기 좋습니다."
        },
        "structured_attributes": {
            "common": {
                "sleeve_length": "긴소매",
                "neckline": "라운드넥"
            },
            "front": {
                "closures_and_embellishments": {
                    "description": "정면 중앙에 별도의 여밈이나 장식 요소 없음",
                    "type": "여밈 없음"
                },
                "pattern": {
                    "description": "정면은 무지 디자인",
                    "type": "무지/솔리드"
                }
            },
            "back": {
                "closures_and_embellishments": {
                    "description": "후면에 텍스트 레터링 있음",
                    "type": "여밈 없음"
                },
                "pattern": {
                    "description": "후면에 텍스트 레터링",
                    "type": "타이포그래피/레터링"
                }
            },
            "subjective": {
                "fit": "레귤러 핏/스탠다드 핏",
                "style_tags": [
                    "모던/미니멀",
                    "캐주얼"
                ],
                "tpo_tags": [
                    "데일리",
                    "데이트/주말"
                ]
            }
        }
    }

    d["color_images"] = {
        "color_info": [
            {
                "name": "블랙",
                "attributes": {
                    "saturation": "아주 낮음",
                    "brightness": "아주 어두움"
                },
                "hex": "#000000"
            },
            {
                "name": "화이트",
                "attributes": {
                    "saturation": "아주 낮음",
                    "brightness": "아주 어두움"
                },
                "hex": "#000000"
            }
        ]
    }
    d["text_images"] = {
        "size_info": {
            "is_exist": True,
            "size_measurements": "{\"SIZE 1\": {\"총장\": \"67cm\", \"가슴단면\": \"61cm\", \"어깨너비\": \"63cm\", \"소매길이\": \"60cm\"}, \"SIZE 2\": {\"총장\": \"69cm\", \"가슴단면\": \"64cm\", \"어깨너비\": \"65cm\", \"소매길이\": \"62cm\"}}"
        },
        "care_info": "찬물로 단독 손세탁 하십시오.\n소재 특성상 세탁 후 약간의 수축이 있을수 있습니다.",
        "product_description": "FUNDAMENTAL을 위해 개발된 800G/Y 이상 헤비 코튼 스웨트 원단으로 텐타, 덤블 방축 가공 및 바이오 워싱 처리가 되어 터치감이 부드럽고 표면은 기모감 없이 깨끗합니다. 수많은 가공으로 세탁 후에도 옷의 형태감 유지 및 봉제 변형 방지, 컬러 변화 최소화. 안정적인 견뢰도의 리플렉티브 필름 프레스 작업으로 세탁 후에도 반사광 유지.",
        "material_info": "COTTON 100%"
    }
    d["representative_assets"] = {
        "back": "segment/1_1.jpg",
        "color_variant": ["segment/1_0.jpg" , "segment/1_1.jpg"],
        "front": "segment/1_0.jpg",
        "model": "segment/0_1.jpg"
    }
    d["product_id"] = "123456"
    d["main_category"] = "TOP"
    d["sub_category"] = "1005"

    return d 

def make_new_id(product_id , color_name):
    return f"{product_id}_{color_name}"

def denormalize_data(sample_data):
    if len(sample_data["color_images"]["color_info"]) == 1:
        id = make_new_id(sample_data["product_id"], sample_data["color_images"]["color_info"][0]["name"])
        d = {}
        d["_id"] = id
        d["text_images"] = sample_data["text_images"]
        d["color_info"] = sample_data["color_images"]["color_info"][0]
        d["representative_image"] = sample_data["representative_assets"]["color_variant"][0]
        d["deep_caption"] = sample_data["deep_caption"]
        d["product_id"] = sample_data["product_id"]
        d["main_category"] = sample_data["main_category"]
        d["sub_category"] = sample_data["sub_category"]
        d["representative_image_s3_key"] = f"{d["main_category"]}/{d["sub_category"]}/{d["representative_image"]}"
        return [d]
    else:
        total = len(sample_data["color_images"]["color_info"])
        ids = [make_new_id(sample_data["product_id"], color_info["name"]) for color_info in sample_data["color_images"]["color_info"]]
        result = []
        for idx  in range(total):
            d = {}
            d["_id"] = ids[idx]
            d["text_images"] = sample_data["text_images"]
            d["color_info"] = sample_data["color_images"]["color_info"][idx]
            d["representative_image"] = sample_data["representative_assets"]["color_variant"][idx]
            d["deep_caption"] = sample_data["deep_caption"]
            d["product_id"] = sample_data["product_id"]
            d["main_category"] = sample_data["main_category"]
            d["sub_category"] = sample_data["sub_category"]
            d["representative_image_s3_key"] = f"{d["main_category"]}/{d["sub_category"]}/{d["representative_image"]}"
            result.append(d)
        return result

@pytest.fixture(scope="session")
def db_manager():
    from db.config.config import Config
    config = Config()
    db = DatabaseManager(connection_string=config["MONGODB_ATLAS_CONNECTION_STRING"] , database_name=config["MONGODB_ATLAS_DATABASE_NAME"] , collection_name=config["MONGODB_ATLAS_COLLECTION_NAME"])
    yield db



def test_insert_data_to_atlas(db_manager , sample_data):
    denormalized_data = denormalize_data(sample_data)
    collection = db_manager.get_collection()
    logger.info(f"Inserting {len(denormalized_data)} documents to MongoDB")
    for d in denormalized_data:
        collection.insert_one(d)
    logger.info(f"Inserted {len(denormalized_data)} documents to MongoDB")





