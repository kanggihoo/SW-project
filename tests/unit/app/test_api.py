import pytest
from app.config.settings import Settings

class TestAPI:
    def test_settings(self):
        settings = Settings()
        print(settings.model_dump())
