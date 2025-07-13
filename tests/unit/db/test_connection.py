import pytest
from db.config.database import DatabaseManager
from dotenv import load_dotenv
import logging
import os
import sys
from db.repository.base import BaseRepository
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
class TestConnection:
    def test_connection(self):
        with DatabaseManager(connection_string=os.getenv("MONGODB_ATLAS_URI")) as db:
            assert db.is_connected()
            logger.info(f"Connected to MongoDB: {db.database_name}")

