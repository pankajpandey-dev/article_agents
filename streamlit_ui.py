import json
import os
from urllib import parse, request
from urllib.error import HTTPError, URLError

import streamlit as st
import streamlit.components.v1 as components


def post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, params: dict):
    query = parse.urlencode(params)
    full_url = f"{url}?{query}" if query else url
    with request.urlopen(full_url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def copy_button(label: str, value: str, key: str):
    safe_value = json.dumps(value)
    components.html(
        f"""
        <button id="{key}" style="padding:6px 10px;border-radius:8px;border:1px solid #ccc;cursor:pointer;">
            {label}
        </button>
        <script>
        const btn = document.getElementById("{key}");
        btn.onclick = async () => {{
            try {{
                await navigator.clipboard.writeText({safe_value});
                btn.innerText = "Copied!";
                setTimeout(() => btn.innerText = "{label}", 1200);
            }} catch (e) {{
                btn.innerText = "Copy failed";
                setTimeout(() => btn.innerText = "{label}", 1200);
            }}
        }};
        </script>
        """,
        height=44,
    )


def render_article_cards(articles: list[dict]):
    if not articles:
        st.info("No articles returned.")
        return

    for idx, article in enumerate(articles, start=1):
        with st.container(border=True):

            # 📰 Titles
            titles = article.get("titles", [])
            if titles:
                st.subheader("📰 Title Options")
                for t in titles:
                    st.write(f"- {t}")
            else:
                st.subheader(f"Article {idx}")

            # 🖼️ Generated hero image (path is on the API server; preview only if shared filesystem)
            ig = article.get("image_generation") or {}
            img_path = article.get("image_path")
            if ig.get("ok") and img_path and os.path.isfile(img_path):
                st.markdown("### 🖼️ Article image")
                st.image(img_path, use_container_width=True)
            elif ig and not ig.get("skipped"):
                st.caption(
                    f"Image generation: {'ok' if ig.get('ok') else 'failed'}"
                    + (f" — {ig.get('error')}" if ig.get('error') else "")
                    + (f" ({ig.get('bytes', 0) // 1024} KB)" if ig.get("bytes") else "")
                )

            # 📖 Main Article
            body = article.get("article", "")
            if body:
                st.markdown("### 📖 Article")
                st.write(body)
            else:
                st.warning("No article content found")

            # 🏷️ Keywords
            keywords = article.get("keywords", [])
            if keywords:
                st.markdown("### 🏷️ Keywords")
                st.write(", ".join(keywords))

            # ❓ FAQs
            faqs = article.get("faqs", [])
            if faqs:
                st.markdown("### ❓ FAQs")
                for faq in faqs:
                    with st.expander(faq.get("question", "Question")):
                        st.write(faq.get("answer", ""))

            # 🔗 Slugs
            slugs = article.get("slugs", [])
            if slugs:
                st.markdown("### 🔗 Slugs")
                st.code("\n".join(slugs))

            # 📊 Meta
            st.markdown("### 📊 Metadata")
            st.write("Meta Title:", article.get("meta_title", ""))
            st.write("Meta Description:", article.get("meta_description", ""))
            st.write("Category:", article.get("category", ""))

            wp = article.get("wordpress_publish")
            if wp is not None:
                st.markdown("### WordPress")
                if wp.get("ok"):
                    st.success(
                        f"Published ({wp.get('status', '')}) — "
                        f"[Open post]({wp.get('link')})"
                        if wp.get("link")
                        else f"Published (post id {wp.get('post_id')})"
                    )
                else:
                    st.error(
                        f"Publish failed: {wp.get('error', wp)}"
                        + (
                            f" (HTTP {wp.get('status_code')})"
                            if wp.get("status_code")
                            else ""
                        )
                    )
                    with st.expander("WordPress error details"):
                        st.json(wp)

            # 📋 Copy buttons
            c1, c2 = st.columns(2)
            with c1:
                copy_button(
                    "Copy First Title",
                    titles[0] if titles else "",
                    f"copy-title-{idx}",
                )
            with c2:
                copy_button(
                    "Copy Article",
                    body,
                    f"copy-body-{idx}",
                )


def render_trending_cards(topics: list[dict], heading: str):
    st.markdown(f"#### {heading}")
    if not topics:
        st.info("No topics found.")
        return

    for idx, topic in enumerate(topics, start=1):
        title = topic.get("title", "Untitled topic")
        link = topic.get("link", "")
        with st.container(border=True):
            st.write(f"**{title}**")
            c1, c2 = st.columns([1, 3])
            with c1:
                copy_button("Copy Title", title, f"copy-topic-title-{heading}-{idx}")
            with c2:
                if link:
                    st.link_button("View", link, use_container_width=False)
                else:
                    st.caption("No link available")

st.set_page_config(page_title="Article Agent UI", page_icon="📰", layout="wide")
st.title("Article Agent")

backend_url = st.sidebar.text_input("Backend Base URL", "http://127.0.0.1:8000")

tab_generate, tab_trending = st.tabs(["Generate Articles", "Trending Topics"])

with tab_generate:
    st.subheader("Generate Articles")
    prompt = st.text_area("Prompt (optional)", placeholder="e.g. AI in healthcare")
    count = st.number_input("Count", min_value=1, max_value=20, value=1, step=1)
    language = st.selectbox("Language", ["english", "hindi"], index=0)

    if st.button("Generate", type="primary"):
        payload = {
            "prompt": prompt or None,
            "count": int(count),
            "language": language,
        }
        try:
            result = post_json(f"{backend_url.rstrip('/')}/article/generate", payload)
            st.success("Articles generated successfully")
            # Handle both list and wrapped dict API responses.
            if isinstance(result, list):
                articles = result
            elif isinstance(result, dict):
                articles = (
                    result.get("articles")
                    or result.get("results")
                    or result.get("data")
                    or []
                )
            else:
                articles = []

            render_article_cards(articles)

            if not articles:
                with st.expander("Raw API response"):
                    st.json(result)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            st.error(f"HTTP {exc.code}: {body}")
        except URLError as exc:
            st.error(f"Connection error: {exc.reason}")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")

with tab_trending:
    st.subheader("Trending Topics")
    category = st.text_input("Category", placeholder="technology")
    region = st.selectbox("Region", ["indian", "international", "both"], index=2)
    trending_language = st.selectbox("Language", ["english", "hindi"], index=0, key="trending-language")
    limit = st.number_input("Topic limit", min_value=1, max_value=20, value=5, step=1)

    if st.button("Fetch Trending"):
        if not category.strip():
            st.warning("Please enter a category.")
        else:
            try:
                st.success("Trending topics fetched")
                base_url = f"{backend_url.rstrip('/')}/article/trending"
                if region == "both":
                    indian = get_json(
                        base_url,
                        {
                            "category": category.strip(),
                            "region": "indian",
                            "language": trending_language,
                            "limit": int(limit),
                        },
                    )
                    international = get_json(
                        base_url,
                        {
                            "category": category.strip(),
                            "region": "international",
                            "language": trending_language,
                            "limit": int(limit),
                        },
                    )
                    render_trending_cards(indian.get("topics", []), "Indian")
                    render_trending_cards(international.get("topics", []), "International")
                else:
                    result = get_json(
                        base_url,
                        {
                            "category": category.strip(),
                            "region": region,
                            "language": trending_language,
                            "limit": int(limit),
                        },
                    )
                    render_trending_cards(result.get("topics", []), region.capitalize())
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="ignore")
                st.error(f"HTTP {exc.code}: {body}")
            except URLError as exc:
                st.error(f"Connection error: {exc.reason}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
