"""Topic-related article images via Imagen, saved as small JPEGs for fast loading."""

from __future__ import annotations

import io
import re
import uuid

from google import genai
from google.genai import types
from PIL import Image

from core.config import settings


def _slug_stem(title: str) -> str:
    base = re.sub(r"[^\w\s-]", "", (title or "").strip())[:60]
    base = re.sub(r"[-\s]+", "-", base).strip("-")
    return base or "article"


def build_image_prompt(article: dict) -> str:
    explicit = (article.get("image_prompt") or "").strip()
    if explicit:
        return explicit
    title = article.get("title") or article.get("seo_title") or "blog topic"
    kw = (article.get("focus_keyword") or "").strip()
    suffix = f" Key theme: {kw}." if kw else ""
    return (
        f"Professional editorial blog header photograph related to: {title}. "
        f"Clean, modern, well-lit, no text or watermarks, suitable as a web hero image.{suffix}"
    )


def _compress_jpeg(image_bytes: bytes) -> bytes:
    im = Image.open(io.BytesIO(image_bytes))
    im = im.convert("RGB")
    w, h = im.size
    max_w = max(320, int(settings.GENERATED_IMAGE_MAX_WIDTH))
    if w > max_w:
        ratio = max_w / w
        im = im.resize((max_w, int(h * ratio)), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    q = max(40, min(95, int(settings.GENERATED_IMAGE_JPEG_QUALITY)))
    im.save(
        out,
        format="JPEG",
        quality=q,
        optimize=True,
        progressive=True,
    )
    return out.getvalue()


def generate_compressed_article_image(article: dict) -> dict:
    """
    Create one compressed JPEG for this article; set ``image_path`` on success.

    Returns a small status dict: ok, path (if ok), error (if not), bytes (compressed size).
    """
    out_dir = settings.project_root / "generated_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = _slug_stem(str(article.get("title") or article.get("seo_title") or "post"))
    filename = f"{stem}-{uuid.uuid4().hex[:10]}.jpg"
    dest = out_dir / filename

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = build_image_prompt(article)

    config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="16:9",
        output_mime_type="image/jpeg",
        output_compression_quality=max(
            40, min(85, int(settings.GENERATED_IMAGE_JPEG_QUALITY) + 5)
        ),
    )

    try:
        response = client.models.generate_images(
            model=settings.IMAGEN_MODEL,
            prompt=prompt,
            config=config,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": None, "bytes": 0}

    images = response.generated_images or []
    if not images or not images[0].image or not images[0].image.image_bytes:
        reason = images[0].rai_filtered_reason if images else None
        return {
            "ok": False,
            "error": reason or "No image returned (filtered or empty response)",
            "path": None,
            "bytes": 0,
        }

    raw = images[0].image.image_bytes
    try:
        compressed = _compress_jpeg(raw)
    except Exception as exc:
        return {"ok": False, "error": f"Compress failed: {exc}", "path": None, "bytes": 0}

    dest.write_bytes(compressed)
    article["image_path"] = str(dest.resolve())
    return {"ok": True, "error": None, "path": article["image_path"], "bytes": len(compressed)}


def attach_compressed_article_image(article: dict) -> dict:
    """
    If enabled, generate and attach ``image_path``. Always returns status for API/UI.
    """
    if not settings.ENABLE_ARTICLE_IMAGES:
        return {"ok": False, "skipped": True, "error": "disabled", "path": None, "bytes": 0}
    status = generate_compressed_article_image(article)
    article["image_generation"] = status
    return status
