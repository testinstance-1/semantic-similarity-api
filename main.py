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

HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"  # Updated to L6 version
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

@app.get("/")
async def health_check():
    return {"status": "healthy"}

async def get_embedding(text: str) -> list:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                HF_API_URL,
                headers=headers,
                json={"inputs": text}
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
                
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )

@app.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(text_pair: TextPair):
    if not text_pair.text1.strip() or not text_pair.text2.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both text1 and text2 must be non-empty"
        )

    try:
        emb1, emb2 = await asyncio.gather(
            get_embedding(text_pair.text1),
            get_embedding(text_pair.text2)
        )
        
        if not emb1 or not emb2:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get embeddings"
            )
            
        sim_score = cosine_similarity([emb1], [emb2])[0][0]
        return {"similarity_score": float(sim_score)}
        
    except Exception as e:
        logger.error(f"Error in similarity computation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
