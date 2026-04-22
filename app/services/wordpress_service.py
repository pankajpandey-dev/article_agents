"""Publish posts to WordPress with featured image and Rank Math–friendly meta."""

from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests
from requests.auth import HTTPBasicAuth

from core.config import settings


def _wordpress_origin() -> str:
    """Site root from WORDPRESS_URL (e.g. strip ``/wp-json/...``)."""
    u = urlparse((settings.WORDPRESS_URL or "").strip())
    path = u.path or ""
    marker = "/wp-json"
    if marker in path:
        path = path[: path.index(marker)].rstrip("/") or ""
    return urlunparse((u.scheme, u.netloc, path, "", "", "")).rstrip("/")


def _media_rest_base() -> str:
    """Base URL for ``/wp-json/wp/v2/media`` (explicit BASE_URL or derived)."""
    if settings.BASE_URL:
        return str(settings.BASE_URL).rstrip("/")
    return _wordpress_origin()


def _escape_html(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_rank_math_meta(
    data: dict[str, Any],
    image_id: int | None,
    image_url: str | None,
    post_url: str | None,
) -> dict[str, Any]:
    """Meta keys Rank Math reads; site must expose these via REST (Headless / register_meta)."""
    seo_title = (data.get("seo_title") or data.get("title") or "")[:70]
    meta_desc = (data.get("meta_description") or "")[:200]
    focus = (data.get("focus_keyword") or "").strip()

    meta: dict[str, Any] = {
        "rank_math_title": seo_title,
        "rank_math_description": meta_desc,
        "rank_math_focus_keyword": focus,
        "rank_math_facebook_title": seo_title,
        "rank_math_facebook_description": meta_desc,
        "rank_math_twitter_title": seo_title,
        "rank_math_twitter_description": meta_desc,
    }

    if post_url:
        meta["rank_math_canonical_url"] = post_url

    if image_id:
        meta["rank_math_facebook_image_id"] = image_id
        meta["rank_math_twitter_image_id"] = image_id

    return meta


def _faq_json_ld_block(data: dict[str, Any]) -> str:
    """FAQPage JSON-LD only (Rank Math often adds Article schema itself)."""
    faqs = data.get("faqs") or []
    entities: list[dict[str, Any]] = []
    for f in faqs:
        q = (f.get("question") or "").strip()
        a = (f.get("answer") or "").strip()
        if q and a:
            entities.append(
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a},
                }
            )
    if not entities:
        return ""
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }
    return (
        "\n<script type=\"application/ld+json\">"
        f"{json.dumps(payload, ensure_ascii=True)}"
        "</script>\n"
    )


def _hero_figure_html(image_url: str, alt: str, caption: str) -> str:
    """First image: no lazy-load (LCP); keyword-rich alt."""
    safe_url = _escape_html(image_url)
    safe_alt = _escape_html(alt)
    safe_cap = _escape_html(caption)
    return (
        f'<figure class="wp-block-image alignwide">'
        f'<img src="{safe_url}" alt="{safe_alt}" '
        f'decoding="async" fetchpriority="high" />'
        f"<figcaption>{safe_cap}</figcaption>"
        "</figure>\n"
    )


def _upload_media(image_path: str, data: dict[str, Any]) -> tuple[int | None, str | None, str | None]:
    """Returns (attachment_id, source_url, error_message)."""
    media_url = f"{_media_rest_base()}/wp-json/wp/v2/media"
    raw_name = image_path.rsplit("/", maxsplit=1)[-1]
    filename = re.sub(r"[^\w.\-]", "_", raw_name) or "article-image.jpg"
    if not filename.lower().endswith((".jpg", ".jpeg")):
        filename = f"{filename}.jpg"
    auth = HTTPBasicAuth(settings.WORDPRESS_USERNAME, settings.WORDPRESS_PASSWORD)

    try:
        with open(image_path, "rb") as f:
            file_bytes = f.read()
    except OSError as exc:
        return None, None, str(exc)

    # Multipart upload (works on more hosts than raw body)
    res = requests.post(
        media_url,
        files={"file": (filename, io.BytesIO(file_bytes), "image/jpeg")},
        auth=auth,
        timeout=120,
    )

    if res.status_code >= 400:
        res = requests.post(
            media_url,
            data=file_bytes,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "image/jpeg",
            },
            auth=auth,
            timeout=120,
        )

    try:
        img = res.json()
    except ValueError:
        img = {"raw": res.text[:500]}

    if res.status_code >= 400:
        err = img.get("message") or img.get("code") or str(img)[:200]
        return None, None, f"Media upload HTTP {res.status_code}: {err}"

    image_id = img.get("id")
    image_url = img.get("source_url")
    if not image_id:
        return None, None, "Media response missing id"

    alt_text = (data.get("focus_keyword") or data.get("seo_title") or data.get("title") or "").strip()
    title_text = (data.get("seo_title") or data.get("title") or "").strip()

    patch = requests.post(
        f"{media_url}/{image_id}",
        json={
            "alt_text": alt_text[:200],
            "title": title_text[:200],
            "caption": title_text[:200],
            "description": (data.get("meta_description") or "")[:300],
        },
        auth=auth,
        timeout=30,
    )
    if patch.status_code >= 400:
        # Image is uploaded; SEO fields on attachment are best-effort
        pass

    return int(image_id), image_url, None


def _post_to_wordpress(payload: dict[str, Any]) -> requests.Response:
    """Create post; if REST rejects ``meta``, create without meta then patch meta."""
    auth = HTTPBasicAuth(settings.WORDPRESS_USERNAME, settings.WORDPRESS_PASSWORD)
    url = settings.WORDPRESS_URL
    r = requests.post(url, json=payload, auth=auth, timeout=60)
    if r.status_code < 400:
        return r
    text_l = (r.text or "").lower()
    if "meta" not in text_l or "meta" not in payload:
        return r

    slim = {k: v for k, v in payload.items() if k != "meta"}
    r2 = requests.post(url, json=slim, auth=auth, timeout=60)
    if r2.status_code >= 400:
        return r

    try:
        pid = r2.json().get("id")
    except ValueError:
        pid = None

    if pid and payload.get("meta"):
        patch: dict[str, Any] = {"meta": payload["meta"]}
        if payload.get("featured_media"):
            patch["featured_media"] = payload["featured_media"]
        try:
            requests.post(
                f"{url.rstrip('/')}/{pid}",
                json=patch,
                auth=auth,
                timeout=60,
            )
        except requests.RequestException:
            pass
    return r2


def publish_article(data: dict[str, Any]) -> dict[str, Any]:
    image_id: int | None = None
    image_url: str | None = None
    media_error: str | None = None

    path = data.get("image_path")
    if path:
        image_id, image_url, media_error = _upload_media(str(path), data)

    content = data.get("article") or ""

    alt = (
        (data.get("focus_keyword") or "").strip()
        or (data.get("seo_title") or data.get("title") or "Article")
    )
    caption = (data.get("title") or data.get("seo_title") or alt)[:120]

    if image_url:
        content = _hero_figure_html(image_url, alt, caption) + content

    content += _faq_json_ld_block(data)

    title = data.get("title") or data.get("seo_title") or "Post"
    slug = data.get("slug") or ""
    excerpt = (data.get("meta_description") or "")[:300]

    origin = _wordpress_origin()
    canonical_guess = f"{origin}/{slug}/" if slug else None

    meta = _build_rank_math_meta(data, image_id, image_url, canonical_guess)

    payload: dict[str, Any] = {
        "title": title,
        "content": content,
        "status": settings.status,
        "slug": slug,
        "excerpt": excerpt,
        "meta": meta,
    }

    if data.get("category_ids"):
        payload["categories"] = data["category_ids"]
    if data.get("tag_ids"):
        payload["tags"] = data["tag_ids"]

    if image_id:
        payload["featured_media"] = image_id

    try:
        response = _post_to_wordpress(
            payload,
        )
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc), "media_error": media_error}

    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text[:800]}

    if response.status_code >= 400:
        return {
            "ok": False,
            "status_code": response.status_code,
            "error": body.get("message") or body.get("code") or str(body),
            "wordpress": body,
            "media_error": media_error,
        }

    link = body.get("link")
    post_id = body.get("id")

    # Re-send Rank Math meta + featured image + canonical (fixes "Focus keyword: Not set" on many sites)
    if post_id:
        post_base = settings.WORDPRESS_URL.rstrip("/")
        final_meta = dict(meta)
        if link:
            final_meta["rank_math_canonical_url"] = link
        sync_body: dict[str, Any] = {"meta": final_meta}
        if image_id:
            sync_body["featured_media"] = image_id
        try:
            requests.post(
                f"{post_base}/{post_id}",
                json=sync_body,
                auth=HTTPBasicAuth(
                    settings.WORDPRESS_USERNAME,
                    settings.WORDPRESS_PASSWORD,
                ),
                timeout=45,
            )
        except requests.RequestException:
            pass

    return {
        "ok": True,
        "post_id": post_id,
        "link": link,
        "status": body.get("status"),
        "featured_media_id": image_id,
        "featured_image_url": image_url,
        "media_error": media_error,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
