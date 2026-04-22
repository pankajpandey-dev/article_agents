from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from client.news_client import get_trending_news_by_category
from services.article_service import run_pipeline

router = APIRouter()


class GenerateArticleRequest(BaseModel):
    prompt: str | None = None
    count: int = Field(default=1, ge=1, le=20)
    language: Literal["english", "hindi"] = "english"


@router.post("/generate")
def generate_articles(payload: GenerateArticleRequest):
    return run_pipeline(
        prompt=payload.prompt,
        count=payload.count,
        language=payload.language,
    )


@router.get("/trending")
def get_trending_topics(
    category: str = Query(..., min_length=2),
    region: Literal["indian", "international"] = "international",
    language: Literal["english", "hindi"] = "english",
    limit: int = Query(default=5, ge=1, le=20),
):
    topics = get_trending_news_by_category(
        category=category,
        region=region,
        language=language,
        limit=limit,
    )
    return {
        "category": category,
        "region": region,
        "language": language,
        "count": len(topics),
        "topics": topics,
    }