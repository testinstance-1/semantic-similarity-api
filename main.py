from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity
import httpx
import numpy as np
import os
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    logger.error("HF_TOKEN environment variable not set!")
    raise RuntimeError("Hugging Face token not configured")

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

class TextPair(BaseModel):
    text1: str
    text2: str

class SimilarityResponse(BaseModel):
    similarity_score: float

@app.on_event("startup")
async def startup_event():
    """Warm up the Hugging Face model on startup"""
    try:
        await get_embedding("warmup")
        logger.info("Model warmup complete")
    except Exception as e:
        logger.warning(f"Model warmup failed: {str(e)}")

@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "Semantic Similarity API",
        "model": "all-MiniLM-L6-v2"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

async def get_embedding(text: str) -> list:
    """Get text embedding from Hugging Face API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                HF_API_URL,
                headers=headers,
                json={"inputs": [text]}  # Note: Input must be a list
            )
            
            if response.status_code == 404:
                logger.error(f"Model not found - check API URL: {HF_API_URL}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Model not found or loading"
                )
            elif response.status_code != 200:
                logger.error(f"HF API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"HF API error: {response.text}"
                )
                
            # API returns list of embeddings (we only sent one text)
            return response.json()[0]
            
    except httpx.RequestError as e:
        logger.error(f"Request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )

@app.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(text_pair: TextPair):
    """Compute cosine similarity between two text embeddings"""
    if not text_pair.text1.strip() or not text_pair.text2.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both text1 and text2 must be non-empty"
        )

    try:
        # Get embeddings in parallel
        emb1, emb2 = await asyncio.gather(
            get_embedding(text_pair.text1),
            get_embedding(text_pair.text2),
            return_exceptions=True
        )
        
        # Handle potential errors from either request
        if isinstance(emb1, Exception):
            raise emb1
        if isinstance(emb2, Exception):
            raise emb2
            
        # Verify we got valid embeddings
        if not isinstance(emb1, list) or not isinstance(emb2, list):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid embedding format received"
            )
            
        # Calculate cosine similarity
        sim_score = cosine_similarity([emb1], [emb2])[0][0]
        return {"similarity_score": float(sim_score)}
        
    except HTTPException:
        raise  # Re-raise existing HTTP exceptions
    except Exception as e:
        logger.error(f"Similarity computation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute similarity"
        )
