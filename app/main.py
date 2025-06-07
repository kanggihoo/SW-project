from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from dotenv import load_dotenv

from .graph import builder, ClothingRAGState
from .utils import embedding_query 

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Clothing Recommendation API",
    description="An API for clothing recommendations using LangGraph",
    version="1.0.0"
)



@app.get("/" , tags=["root"])
async def root():
    test = embedding_query("I want to buy a white shirt")
    return {"message": "Welcome to the Clothing Recommendation API" , "test": test}


