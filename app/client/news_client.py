import feedparser
from urllib.parse import quote_plus


def _region_params(region: str, language: str = "english") -> str:
    region_name = region.lower()
    language_name = language.lower()

    country = "IN" if region_name == "indian" else "US"
    lang_code = "hi" if language_name == "hindi" else "en"

    if language_name == "hindi":
        hl = "hi-IN" if region_name == "indian" else "hi"
    else:
        hl = "en-IN" if region_name == "indian" else "en-US"

    return f"hl={hl}&gl={country}&ceid={country}:{lang_code}"


def get_trending_news(limit: int = 5):
    feed = feedparser.parse("https://news.google.com/rss")

    return [
        {"title": entry.title, "link": entry.link}
        for entry in feed.entries[:limit]
    ]


def get_trending_news_by_category(
    category: str,
    region: str = "international",
    language: str = "english",
    limit: int = 5,
):
    query = quote_plus(category.strip())
    params = _region_params(region, language)
    feed_url = f"https://news.google.com/rss/search?q={query}&{params}"
    feed = feedparser.parse(feed_url)

    return [
        {"title": entry.title, "link": entry.link}
        for entry in feed.entries[:limit]
    ]