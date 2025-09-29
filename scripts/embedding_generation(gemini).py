import logging
from db.config import Config
from db.repository.fashion_async import AsyncFashionRepository
from datetime import datetime
import asyncio
from embedding.other_api import GeminiEmbedding
from pymongo import UpdateOne

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EmbeddingGenerationService:
    """
    A service to generate and update embeddings for product descriptions.
    It connects to MongoDB, fetches products, generates embeddings using Gemini,
    and stores them back in the database.
    """

    def __init__(self, batch_size: int = 32):
        """
        Initializes the service, setting up configuration, repository, and embedding model.
        """
        self.config = Config()
        self.atlas_config = self.config.get_atlas_sku_config()

        # Initialize the repository
        self.repo = AsyncFashionRepository(
            connection_string=self.atlas_config['MONGODB_ATLAS_CONNECTION_STRING'],
            database_name=self.atlas_config['MONGODB_ATLAS_DATABASE_NAME'],
            collection_name=self.atlas_config['MONGODB_ATLAS_COLLECTION_NAME'],
        )

        # Initialize Gemini Embedding model
        self.gemini_embedding = GeminiEmbedding()
        self.batch_size = batch_size
        logger.info('EmbeddingGenerationService initialized.')

    async def connect(self):
        """Connects to the database."""
        try:
            if hasattr(self.repo, 'connect') and callable(self.repo.connect):
                await self.repo.connect()
            logger.info('Successfully connected to MongoDB.')
        except Exception as e:
            logger.error(f'Failed to connect to MongoDB: {e}', exc_info=True)
            raise

    async def close(self):
        """Closes the database connection."""
        if hasattr(self.repo, 'close') and callable(self.repo.close):
            await self.repo.close()
            logger.info('MongoDB connection closed.')
        elif self.repo.client:  # Fallback for repository pattern without explicit close
            self.repo.client.close()
            logger.info('MongoDB connection closed.')

    async def process_batch(self, batch: list[dict], embedding_model: str, output_dimension: int, task_type: str):
        """
        Processes a single batch of documents to generate and store embeddings.
        """
        if not batch:
            return

        logger.info(f'Processing a batch of {len(batch)} documents.')

        docs_to_process = []
        for doc in batch:
            try:
                product_id = doc['_id']
                sku_id = doc['product_skus']['sku_id']
                description = doc['products']['captions']['comprehensive_description']
                if product_id and description:
                    docs_to_process.append({'product_id': product_id, 'description': description})
            except KeyError:
                logger.warning(f'Skipping document with missing data: {doc.get("_id")}')
                continue

        if not docs_to_process:
            logger.warning('Batch has no valid documents to process.')
            return

        descriptions = [doc['description'] for doc in docs_to_process]
        product_ids = [doc['product_id'] for doc in docs_to_process]

        try:
            logger.info(f'Generating embeddings for {len(descriptions)} descriptions...')
            embedding_vectors = await self.gemini_embedding.get_embedding(texts=descriptions, output_dimension=output_dimension, task_type=task_type)

            if len(embedding_vectors) != len(product_ids):
                logger.error(f'Mismatch between embeddings ({len(embedding_vectors)}) and texts ({len(product_ids)}). Skipping batch.')
                return

            updates = []
            for i, product_id in enumerate(product_ids):
                embedding_data = {
                    'model_name': self.gemini_embedding.model_name,
                    'dimension': output_dimension,
                    'vector': embedding_vectors[i],
                    'modified_at': datetime.now().isoformat(),
                }
                updates.append(UpdateOne({'_id': product_id}, {'$set': {'embedding.comprehensive_description': embedding_data}}))

            if updates:
                logger.info(f'Performing bulk update for {len(updates)} products.')
                result = await self.repo.collection.bulk_write(updates)
                logger.info(f'Bulk write result: modified_count={result.modified_count}')

        except Exception as e:
            logger.error(f'An error occurred while processing batch: {e}', exc_info=True)

    async def generate_and_update_embeddings(self, embedding_model: str, output_dimension: int, task_type: str):
        """
        Fetches products from MongoDB in batches, generates embeddings for 'comprehensive_description',
        and updates the documents. This script is idempotent.
        """
        query = {
            'products.captions.comprehensive_description': {'$exists': True, '$ne': ''},
            # "embedding.comprehensive_descriptionv2": {"$exists": False}
        }
        projection = {'_id': 1, 'product_skus.sku_id': 1, 'products.captions.comprehensive_description': 1}
        try:
            cursor = self.repo.collection.find(query, projection)

            batch = []
            total_processed = 0
            logger.info('Starting embedding generation and update process...')

            async for doc in cursor:
                batch.append(doc)
                if len(batch) >= self.batch_size:
                    await self.process_batch(batch, embedding_model, output_dimension, task_type)
                    total_processed += len(batch)
                    logger.info(f'Total documents processed so far: {total_processed}')
                    batch = []

            if batch:
                await self.process_batch(batch, embedding_model, output_dimension, task_type)
                total_processed += len(batch)

            logger.info(f'Finished embedding generation. Total documents processed in this run: {total_processed}')

        except Exception as e:
            logger.error(f'An error occurred during the embedding generation process: {e}', exc_info=True)


async def main():
    """Main function to run the embedding generation service."""
    service = EmbeddingGenerationService()
    try:
        await service.connect()
        await service.generate_and_update_embeddings(
            embedding_model='gemini-embedding-001',
            output_dimension=3072,
            task_type='RETRIEVAL_DOCUMENT',
        )
    except Exception as e:
        logger.error(f'Main process failed: {e}', exc_info=True)
    finally:
        await service.close()


if __name__ == '__main__':
    asyncio.run(main())
