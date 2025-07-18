import pytest
from dotenv import load_dotenv
import logging
import os
import sys
from db import create_fashion_repo

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
   def test_connection_local(self):
      repo = create_fashion_repo(use_atlas=False)
      assert repo.db_manager.is_connected()
      logger.info(f"Connected to MongoDB: {repo.db_manager.database_name}")

   def test_connection_atlas(self):
      repo = create_fashion_repo(use_atlas=True)
      assert repo.db_manager.is_connected()
      logger.info(f"Connected to MongoDB: {repo.db_manager.database_name}")

