import uvicorn 
import sys
from app.config.settings import settings
import logging
if __name__ == "__main__":
    print(sys.path)
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s - %(filename)s - %(lineno)d', datefmt='%H:%M:%S')
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload= settings.is_dev() , log_level="debug")