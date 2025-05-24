from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
import logging
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Load the pre-trained SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L3-v2')
logger.info("Loaded SentenceTransformer model: all-MiniLM-L3-v2")

# Define request and response models
class TextPair(BaseModel):
    text1: str
    text2: str

class SimilarityResponse(BaseModel):
    similarity_score: float

@app.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity_endpoint(text_pair: TextPair):
    """
    Compute semantic similarity between two texts provided in the request body.
    
    Args:
        text_pair (TextPair): JSON body with 'text1' and 'text2' fields.
    
    Returns:
        SimilarityResponse: JSON response with 'similarity_score' field.
    """
    try:
        # Validate input
        if not text_pair.text1.strip() or not text_pair.text2.strip():
            raise HTTPException(status_code=400, detail="Both text1 and text2 must be non-empty strings")
        
        # Compute similarity
        embedding1 = model.encode(text_pair.text1, convert_to_tensor=True)
        embedding2 = model.encode(text_pair.text2, convert_to_tensor=True)
        similarity = util.cos_sim(embedding1, embedding2)[0][0].item()
        
        # Ensure similarity is between 0 and 1
        similarity = max(0.0, min(1.0, similarity))
        logger.info(f"Computed similarity: {similarity} for texts: {text_pair.text1[:50]}... and {text_pair.text2[:50]}...")
        
        return SimilarityResponse(similarity_score=similarity)
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)