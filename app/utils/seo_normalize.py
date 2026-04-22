"""Normalize LLM article JSON so Rank Math basic checks pass (focus keyphrase, density hints)."""

from __future__ import annotations

import html
import re
from typing import Any

_STOP_EN = frozenset(
    "the a an and or to of in for on with at by from as is was are be this that it".split()
)


def _strip_tags(html_fragment: str) -> str:
    return re.sub(r"<[^>]+>", " ", html_fragment or "")


def _count_phrase(text: str, phrase: str) -> int:
    if not phrase.strip():
        return 0
    return len(re.findall(re.escape(phrase.strip()), text, flags=re.IGNORECASE))


def derive_focus_keyword(topic: str, language: str) -> str:
    """Short keyphrase from topic when the model omits ``focus_keyword``."""
    t = (topic or "").strip()
    if not t:
        return "guide"

    if language == "hindi":
        parts = re.findall(r"[\u0900-\u097F]+|[a-zA-Z0-9]+", t.lower())
    else:
        parts = re.findall(r"[a-z0-9]+", t.lower())

    if not parts:
        return "guide"

    picked: list[str] = []
    for w in parts:
        if w in _STOP_EN and not picked:
            continue
        picked.append(w)
        if len(picked) >= 4:
            break
    if len(picked) < 2:
        picked = parts[: min(3, len(parts))]
    phrase = " ".join(picked)
    return phrase[:55].strip() or "guide"


def slugify_phrase(phrase: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (phrase or "").lower(), flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:65] or "post"


def normalize_article_seo(data: dict[str, Any], topic: str, language: str) -> dict[str, Any]:
    """
    Ensure focus keyphrase, slug, SEO title, meta description, and body satisfy
    common Rank Math basic tests (exact phrase in title, URL, intro, subheads, alts).
    """
    fk = (data.get("focus_keyword") or "").strip()
    if not fk:
        fk = derive_focus_keyword(topic, language)
        data["focus_keyword"] = fk

    fk_slug = slugify_phrase(fk)

    slug = (data.get("slug") or "").strip().lower()
    slug = re.sub(r"[^a-z0-9\u0900-\u097f-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        data["slug"] = fk_slug[:72]
    elif fk_slug not in slug:
        data["slug"] = f"{fk_slug}-{slug}"[:72]
    else:
        data["slug"] = slug[:72]

    # SEO title: must start with exact focus keyphrase (Rank Math "beginning" checks)
    seo = (data.get("seo_title") or data.get("title") or "").strip()
    fk_low, seo_low = fk.lower(), seo.lower()
    if not seo_low.startswith(fk_low):
        tail = seo
        if fk_low in seo_low:
            tail = seo[seo_low.index(fk_low) + len(fk) :].lstrip(" :–-|")
        combo = f"{fk}: {tail}".strip(" :") if tail else fk
        if len(combo) > 60:
            combo = combo[:57].rsplit(" ", 1)[0] + "…"
        data["seo_title"] = combo[:60]
    else:
        data["seo_title"] = seo[:60]

    # Power word + sentiment (Rank Math title readability) — keep focus keyphrase at start
    st = data["seo_title"]
    has_power = re.search(
        r"\b(best|ultimate|proven|essential|complete|smart|free|top|guide|quick|powerful)\b",
        st,
        re.I,
    )
    has_sent = re.search(
        r"\b(easy|simple|never|great|worst|avoid|amazing|bad|good|love|terrible)\b",
        st,
        re.I,
    )
    if (not has_power or not has_sent) and st.lower().startswith(fk_low):
        rest = st[len(fk) :].lstrip(" :–-|")
        if not rest:
            rest = "Guide & Tips"
        bits: list[str] = []
        if not has_power:
            bits.append("Best")
        if not has_sent:
            bits.append("Easy")
        glue = " ".join(bits)
        st = f"{fk}: {glue} {rest}".strip()
        if len(st) > 60:
            st = st[:57].rsplit(" ", 1)[0] + "…"
        data["seo_title"] = st

    # Meta description: keyphrase at the very start
    md = (data.get("meta_description") or "").strip()
    if not md.lower().startswith(fk_low):
        md = f"{fk} — {md}".strip()
    if len(md) > 160:
        md = md[:157].rsplit(" ", 1)[0] + "…"
    data["meta_description"] = md

    # Body: opening + keyword density + subheads + image alts
    article = data.get("article") or ""
    plain = _strip_tags(article)
    wc = len(plain.split())
    target_mentions = max(6, min(14, wc // 100 + 5))  # ~0.8–1.2% for typical lengths

    if fk_low not in plain[:220].lower():
        lead = (
            f"<p><strong>{html.escape(fk)}</strong> is the focus of this guide. "
            f"We explain what matters most about {html.escape(fk)} and how to use these ideas step by step.</p>\n"
        )
        article = lead + article

    n = _count_phrase(_strip_tags(article), fk)
    if n < target_mentions:
        gap = target_mentions - n
        extra = []
        templates = (
            f"<p>Throughout this article, <strong>{html.escape(fk)}</strong> connects each section to real-world use.</p>",
            f"<p>Readers exploring <strong>{html.escape(fk)}</strong> will find actionable examples below.</p>",
            f"<p>We return to <strong>{html.escape(fk)}</strong> whenever a decision depends on context.</p>",
            f"<p>Your next steps around <strong>{html.escape(fk)}</strong> are summarized in the conclusion.</p>",
        )
        for i in range(min(gap, len(templates))):
            extra.append(templates[i])
        article = article + "\n<section>\n" + "\n".join(extra) + "\n</section>\n"

    def _heading_inject(html_in: str) -> str:
        fk_esc = re.escape(fk)
        fk_h = html.escape(fk)
        out = html_in
        fixed = 0
        for tag in ("h2", "h3"):
            pattern = re.compile(rf"(<{tag}[^>]*>)([^<]+)(</{tag}>)", re.I)

            def sub_fn(m: re.Match[str]) -> str:
                nonlocal fixed
                inner = m.group(2)
                if re.search(fk_esc, inner, re.I):
                    return m.group(0)
                if fixed >= 2:
                    return m.group(0)
                fixed += 1
                return f"{m.group(1)}{fk_h} and {inner.strip()}{m.group(3)}"

            out = pattern.sub(sub_fn, out, count=6)
        return out

    article = _heading_inject(article)

    fk_alt = html.escape(fk, quote=True)
    article = re.sub(
        r"<img([^>]*)\salt=\"[^\"]*\"",
        rf'<img\1 alt="{fk_alt}"',
        article,
        flags=re.I,
    )
    article = re.sub(
        r"<img([^>]*)\salt='[^']*'",
        rf"<img\1 alt='{fk_alt}'",
        article,
        flags=re.I,
    )
    def _ensure_img_alt(m: re.Match[str]) -> str:
        tag = m.group(0)
        if re.search(r"\balt\s*=", tag, re.I):
            return tag
        return tag[:4] + f' alt="{fk_alt}" ' + tag[4:].lstrip()

    article = re.sub(r"<img\b[^>]*>", _ensure_img_alt, article, flags=re.I)

    data["article"] = article
    return data
