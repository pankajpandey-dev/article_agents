import json
from client.news_client import get_trending_news
from agent.article_agent import generate_article
from utils.parser import safe_parse
from utils.seo_normalize import normalize_article_seo
from services.image_generator import attach_compressed_article_image
from services.wordpress_service import publish_article

def run_pipeline(prompt: str | None = None, count: int = 1, language: str = "english"):
    total = max(1, count)
    normalized_language = (language or "english").strip().lower()
    if normalized_language not in {"english", "hindi"}:
        normalized_language = "english"

    if prompt and prompt.strip():
        topics = [{"title": prompt.strip()} for _ in range(total)]
    else:
        topics = get_trending_news(limit=total)

    results = []

    for topic in topics:
        raw_output = generate_article(topic["title"], language=normalized_language)
        data = safe_parse(raw_output)

        if not data:
            continue

        normalize_article_seo(data, topic["title"], normalized_language)
        print("Generated Article:", data)
        attach_compressed_article_image(data)
        data["wordpress_publish"] = publish_article(data)
        results.append(data)

    return results