import os
import asyncio
import json
import logging
from typing import List

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Setup logging
logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)

# Hugging Face API config
HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_API_KEY not found in environment variables")

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# Request model
class SimilarityRequest(BaseModel):
    sentence1: str
    sentence2: str

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Hugging Face Sentence Similarity API is running."}

# Similarity endpoint
@app.post("/similarity")
async def get_similarity(data: SimilarityRequest):
    payload = {
        "inputs": {
            "source_sentence": data.sentence1,
            "sentences": [data.sentence2]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(HF_API_URL, headers=headers, json=payload)
    except httpx.RequestError as e:
        logger.exception("Request to HF API failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to Hugging Face API"
        )

    if response.status_code != 200:
        logger.error(f"HF API error: {response.status_code} - {response.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"HF API error: {response.text}"
        )

    try:
        similarity_score = response.json()[0]
        return {"similarity": similarity_score}
    except Exception as e:
        logger.exception("Failed to parse HF response")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse Hugging Face response"
        )
