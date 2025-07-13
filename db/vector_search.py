import pymongo


#TODO: 벡터값으로 만들 필드 가져오기
import pymongo

# Connect to your Atlas cluster
mongo_client = pymongo.MongoClient("<connection-string>")
db = mongo_client["sample_airbnb"]
collection = db["listingsAndReviews"]

# Define a filter to exclude documents with null or empty 'summary' fields
filter = { 'summary': { '$exists': True, "$nin": [ None, "" ] } }

# Get a subset of documents in the collection
documents = collection.find(filter, {'_id': 1, 'summary': 1}).limit(50)


# TODO: 벡터값 Binary 형태로 저장
from bson.binary import Binary 
from bson.binary import BinaryVectorDtype

# Define a function to generate BSON vectors
def generate_bson_vector(vector, vector_dtype):
   return Binary.from_vector(vector, vector_dtype)

# Generate BSON vector from the sample float32 embedding
bson_float32_embedding = generate_bson_vector(embedding, BinaryVectorDtype.FLOAT32)

# Print the converted embedding
print(f"The converted BSON embedding is: {bson_float32_embedding}")

#TODO : 임베딩 변환 메서드 정의 후 update 하기 

from pymongo import UpdateOne

# Generate the list of bulk write operations
operations = []
for doc in documents:
   summary = doc["summary"]
   # Generate embeddings for this document
#    embedding = get_embedding(summary)

   # Uncomment the following line to convert to BSON vectors
   embedding = generate_bson_vector(embedding, BinaryVectorDtype.FLOAT32)

   # Add the update operation to the list
   operations.append(UpdateOne(
      {"_id": doc["_id"]},
      {"$set": {
         "embedding": embedding
      }}
   ))

# Execute the bulk write operation
if operations:
   result = collection.bulk_write(operations)
   updated_doc_count = result.modified_count

print(f"Updated {updated_doc_count} documents.")


#TODO : 벡터 검색을 위한 인덱스 생성
from pymongo.operations import SearchIndexModel
# Create your index model, then create the search index
search_index_model = SearchIndexModel(
  definition = {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "similarity": "dotProduct",
        "numDimensions": 768
      }
    ]
  },
  name="vector_index",
  type="vectorSearch"
)
collection.create_search_index(model=search_index_model)