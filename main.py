from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity
import httpx
import numpy as np
import os

app = FastAPI()

HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L3-v2"
HF_TOKEN = os.getenv("HF_TOKEN")  

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

class TextPair(BaseModel):
    text1: str
    text2: str

class SimilarityResponse(BaseModel):
    similarity_score: float

async def get_embedding(text: str) -> list:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": text}
        )
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"HF API error: {response.text}")
    return response.json()

@app.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(text_pair: TextPair):
    if not text_pair.text1.strip() or not text_pair.text2.strip():
        raise HTTPException(status_code=400, detail="Both text1 and text2 must be non-empty")

    # Get embeddings from Hugging Face API
    emb1, emb2 = await get_embedding(text_pair.text1), await get_embedding(text_pair.text2)

    # Compute cosine similarity
    sim_score = cosine_similarity([emb1], [emb2])[0][0]
    return {"similarity_score": float(sim_score)}
