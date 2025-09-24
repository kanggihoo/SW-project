from fastapi import APIRouter, Body, HTTPException, status
from typing import Annotated, Dict, Any, List
from app.config.dependencies import RepositoryDep
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["mongodb"],
)

@router.get("/ping", summary="Check database connection")
async def db_ping(repo: RepositoryDep):
    """
    Pings the database to check for a successful connection.
    This is done by attempting to find a single document.
    """
    try:
        # Attempt a lightweight operation to check the connection
        is_connected = await repo.is_connected()
        return {"status": "ok", "message": "Successfully connected to the database." , "data" : {"is_connected": is_connected , "database_name" : repo.database_name , "collection_name" : repo.collection_name }}
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

@router.post("/documents", status_code=status.HTTP_201_CREATED, summary="Create a new document")
async def create_document(
    repo: RepositoryDep,
    document: Annotated[Dict[str, Any], Body(..., description="Document to be created. Must include '_id'.")]
):
    """
    Create a new document in the fashion collection.
    The document body must be a valid JSON object with an `_id` field.
    """
    if "_id" not in document:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document must contain an '_id' field.")
    
    try:
        doc_id = await repo.create(document)
        if doc_id is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Document with ID '{document['_id']}' already exists.")
        return {"message": "Document created successfully", "document_id": doc_id}
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/documents/{doc_id}", summary="Read a document by ID")
async def read_document(repo: RepositoryDep, doc_id: str):
    """
    Retrieve a single document from the fashion collection by its ID.
    """
    document = await repo.find_by_id(doc_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID '{doc_id}' not found.")
    return document

@router.get("/documents", summary="List all documents")
async def read_all_documents(repo: RepositoryDep):
    """
    Retrieve all documents from the fashion collection.
    WARNING: This can be slow and return a large amount of data on large collections.
    """
    documents = []
    async for doc in repo.find_all():
        documents.append(doc)
    return documents

@router.put("/documents/{doc_id}", summary="Update a document by ID")
async def update_document(
    repo: RepositoryDep,
    doc_id: str,
    update_data: Annotated[Dict[str, Any], Body(..., description="Fields and values to update.")]
):
    """
    Update fields of an existing document in the fashion collection.
    """
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Update data cannot be empty.")
        
    success = await repo.update_by_id(doc_id, update_data)
    if not success:
        existing_doc = await repo.find_by_id(doc_id)
        if existing_doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID '{doc_id}' not found.")
        else:
            return {"message": "Document not modified (update data may be identical to existing data)."}
            
    return {"message": f"Document with ID '{doc_id}' updated successfully."}

@router.delete("/documents/{doc_id}", summary="Delete a document by ID")
async def delete_document(repo: RepositoryDep, doc_id: str):
    """
    Delete a document from the fashion collection by its ID.
    """
    success = await repo.delete_by_id(doc_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID '{doc_id}' not found.")
    return {"message": f"Document with ID '{doc_id}' deleted successfully."}
