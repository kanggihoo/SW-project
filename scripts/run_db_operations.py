import argparse
import asyncio
import logging
import os
import sys

# This allows the script to be run from the project root and find other modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from db.repository.fashion_async import AsyncFashionRepository

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def main():
    """Parses command-line arguments and runs the selected database operation."""

    parser = argparse.ArgumentParser(
        description="""
        Command-line tool to perform bulk operations on the fashion database.
        This tool requires MongoDB connection details to be set as environment variables:
        - MONGO_CONNECTION_STRING: The full MongoDB connection string.
        - MONGO_DATABASE_NAME: The name of the database to connect to.
        - MONGO_COLLECTION_NAME: The name of the collection to operate on.
        """,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # --- Sub-parser for 'add_bson' ---
    parser_add = subparsers.add_parser(
        'add_bson', help='Convert a vector field to BSON format and add it as a new field.', formatter_class=argparse.RawTextHelpFormatter
    )
    parser_add.add_argument('--dtype', type=str, required=True, choices=['float32', 'int8'], help='Data type of the vector.')
    parser_add.add_argument('--source', type=str, required=True, help='The name of the source field containing the vector list.')
    parser_add.add_argument('--target', type=str, required=True, help='The name of the target field to store the BSON vector.')
    parser_add.add_argument('--batch-size', type=int, default=500, help='Number of documents to process in a batch (default: 500).')

    # --- Sub-parser for 'remove_field' ---
    parser_remove = subparsers.add_parser(
        'remove_field', help='Remove a specific field from all documents in the collection.', formatter_class=argparse.RawTextHelpFormatter
    )
    parser_remove.add_argument('--field', type=str, required=True, help='The name of the field to remove.')

    args = parser.parse_args()

    # --- Get Database Configuration from Environment Variables ---
    connection_string = os.getenv('MONGO_CONNECTION_STRING')
    database_name = os.getenv('MONGO_DATABASE_NAME')
    collection_name = os.getenv('MONGO_COLLECTION_NAME')

    if not all([connection_string, database_name, collection_name]):
        logging.error('One or more required environment variables are not set.')
        logging.error('Please set MONGO_CONNECTION_STRING, MONGO_DATABASE_NAME, and MONGO_COLLECTION_NAME.')
        return

    # --- Initialize Repository ---
    # The repository handles its own connection management within its methods.
    repo = AsyncFashionRepository(connection_string=connection_string, database_name=database_name, collection_name=collection_name)

    # --- Execute Command ---
    try:
        if args.command == 'add_bson':
            logging.info(f"Starting 'add_bson' operation...")
            logging.info(f"Source: '{args.source}', Target: '{args.target}', DType: '{args.dtype}', Batch Size: {args.batch_size}")

            modified_count = await repo.add_bson_vector_field(
                vector_dtype_str=args.dtype, source_field=args.source, target_field=args.target, batch_size=args.batch_size
            )
            logging.info(f"'add_bson' operation completed. Total documents updated: {modified_count}")

        elif args.command == 'remove_field':
            logging.info(f"Starting 'remove_field' operation for field: '{args.field}'")

            modified_count = await repo.remove_field(field_name=args.field)

            logging.info(f"'remove_field' operation completed. Total documents updated: {modified_count}")
    except Exception as e:
        logging.error(f'An error occurred during the operation: {e}')


if __name__ == '__main__':
    # To run this script:
    # 1. Set environment variables for your MongoDB connection.
    #    export MONGO_CONNECTION_STRING="mongodb+srv://..."
    #    export MONGO_DATABASE_NAME="your_db_name"
    #    export MONGO_COLLECTION_NAME="your_collection_name"
    #
    # 2. Run from the command line.
    #    Example for adding BSON field:
    #    python run_db_operations.py add_bson --dtype float32 --source embedding_field --target bson_embedding_field
    #
    #    Example for removing a field:
    #    python run_db_operations.py remove_field --field old_embedding_field

    asyncio.run(main())
