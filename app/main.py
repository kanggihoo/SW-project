from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from dotenv import load_dotenv

from .router import websocket

load_dotenv()
# os.environ["LANGSMITH_TRACING"] = "true"
# os.environ["LANGSMITH_PROJECT"] = "langgraph-test"


app = FastAPI(
    title="Clothing Recommendation API",
    description="An API for clothing recommendations using LangGraph",
    version="1.0.0"
)

app.include_router(websocket.router)


@app.get("/" , tags=["root"])
async def root():
    return {"message": "Welcome to the Clothing Recommendation API"}

