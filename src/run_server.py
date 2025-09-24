import uvicorn 
import sys
from app.config.settings import settings

if __name__ == "__main__":
    print(sys.path)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload= settings.is_dev() , log_level="debug")