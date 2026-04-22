from fastapi import APIRouter
from api.endpoints import article

router = APIRouter()
router.include_router(article.router, prefix="/article")