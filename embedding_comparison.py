import asyncio
import csv
import os
import json
from dotenv import load_dotenv
import httpx

# Import necessary modules from the project
# Add project root to path to allow sibling imports
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from db.config.config import get_config
from db.config.database import DatabaseManager
from embedding.embedding import JinaEmbedding
from embedding.other_api import GeminiEmbedding

async def main():
    """
    Compares Jina and Gemini embedding models on product descriptions from MongoDB
    and saves the results to a single CSV file.
    """
    # 1. Load environment variables
    load_dotenv()
    print("Loaded environment variables.")

    # 2. Set up MongoDB connection
    print("Connecting to MongoDB...")
    try:
        config = get_config()
        atlas_config = config.get_atlas_config()
        db_manager = DatabaseManager(
            connection_string=os.getenv("MONGODB_ATLAS_URI"),
            database_name=atlas_config["MONGODB_ATLAS_DATABASE_NAME"],
            collection_name=atlas_config["MONGODB_ATLAS_COLLECTION_NAME"]
        )
        products_collection = db_manager.get_collection()
        print("Successfully connected to MongoDB.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return

    # 3. Fetch data from MongoDB
    print("Fetching product descriptions from the database...")
    try:
        # Fetch a limited number of documents for testing purposes.
        # Remove .limit(100) to process all documents.
        cursor = products_collection.find().limit(1)            

        descriptions = [
            doc.get("captions", {}).get("comprehensive_description")
            for doc in cursor
        ]
        print(f"Found {len(descriptions)} descriptions to process.")
    except Exception as e:
        print(f"Failed to fetch data from MongoDB: {e}")
        db_manager.close()
        return
    finally:
        db_manager.close()
        print("MongoDB connection closed.")

    if not descriptions:
        print("No descriptions found in the database. Exiting.")
        return

    # 4. Initialize models and generate embeddings
    rows_to_write = []
    jina_embeddings = []
    gemini_embeddings = []

    async with httpx.AsyncClient() as session:
        try:
            # Jina Embeddings
            print("Generating Jina embeddings...")
            jina_embedder = JinaEmbedding(session=session)
            jina_result = await jina_embedder.get_embedding(descriptions)
            jina_embeddings = jina_result["embeddings"]
            print(f"Successfully generated {len(jina_embeddings)} Jina embeddings.")
        except Exception as e:
            print(f"An error occurred during Jina embedding generation: {e}")

        try:
            # Gemini Embeddings
            print("Generating Gemini embeddings...")
            gemini_embedder = GeminiEmbedding()
            gemini_embeddings = await gemini_embedder.get_embedding(descriptions)
            print(f"Successfully generated {len(gemini_embeddings)} Gemini embeddings.")
        except Exception as e:
            print(f"An error occurred during Gemini embedding generation: {e}")

    # 5. Combine results for CSV writing
    for i, description in enumerate(descriptions):
        if i < len(jina_embeddings):
            rows_to_write.append({
                'model': 'jina',
                'text': description,
                'embedding': json.dumps(jina_embeddings[i])
            })
        if i < len(gemini_embeddings):
            rows_to_write.append({
                'model': 'gemini',
                'text': description,
                'embedding': json.dumps(gemini_embeddings[i])
            })

    # 6. Write to a single CSV file
    output_filename = 'embedding_comparison.csv'
    print(f"Saving comparison results to {output_filename}...")
    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as f:
            if rows_to_write:
                writer = csv.DictWriter(f, fieldnames=rows_to_write[0].keys())
                writer.writeheader()
                writer.writerows(rows_to_write)
        print("Comparison results saved successfully.")
    except IOError as e:
        print(f"Error writing to CSV file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during CSV writing: {e}")


    print("Embedding comparison script finished.")

if __name__ == "__main__":
    # This allows the script to be run from the command line.
    # e.g., python embedding_comparison.py
    asyncio.run(main())
