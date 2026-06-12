import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.recommendation_service import generate_and_save_recommendations_for_user


load_dotenv()

app = FastAPI(
    title=os.getenv("API_TITLE", "Personalized Book Recommendation API"),
    version=os.getenv("API_VERSION", "1.0.0"),
)


class GenerateRecommendationsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class GenerateRecommendationsResponse(BaseModel):
    success: bool
    user_id: str
    generated_count: int
    message: str
    recommendations: list[Dict[str, Any]]


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def verify_internal_secret(x_recommender_secret: Optional[str]) -> None:
    expected_secret = get_required_env("RECOMMENDER_INTERNAL_SECRET")

    if not x_recommender_secret:
        raise HTTPException(
            status_code=401,
            detail="Missing recommender secret.",
        )

    if x_recommender_secret != expected_secret:
        raise HTTPException(
            status_code=403,
            detail="Invalid recommender secret.",
        )


@app.get("/health")
def health_check():
    return {
        "success": True,
        "service": os.getenv("API_SERVICE_NAME", "book-recommendation-engine"),
        "status": "healthy",
    }


@app.post("/recommendations/generate", response_model=GenerateRecommendationsResponse)
def generate_recommendations(
    payload: GenerateRecommendationsRequest,
    x_recommender_secret: Optional[str] = Header(default=None),
):
    verify_internal_secret(x_recommender_secret)

    try:
        recommendations = generate_and_save_recommendations_for_user(
            user_id=payload.user_id,
            limit=payload.limit,
            recommendation_type="personalized",
        )

        return {
            "success": True,
            "user_id": payload.user_id,
            "generated_count": len(recommendations),
            "message": "Recommendations generated and saved successfully.",
            "recommendations": recommendations,
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate recommendations.",
        )
