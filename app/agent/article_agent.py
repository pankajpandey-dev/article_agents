from client.gemini_client import GeminiClient

llm = GeminiClient()

# def generate_article(topic: str, language: str = "english"):
#     prompt = f"""
#     Return ONLY JSON.

#     Topic: {topic}
#     Language: {language}

#     Generate:
#     - 1 titles
#     - 700 word article
#     - 5 keywords
#     - 2 slugs
#     - 4 FAQs
#     - meta title
#     - meta description
#     - category

#     The full content, titles, FAQs, meta title, and meta description must be in {language}.
#     """

#     return llm.generate(prompt)


def generate_article(topic: str, language: str = "english"):
    prompt = f"""
You are an advanced SEO content writer.

Return ONLY valid JSON. No explanation.

Topic: {topic}
Language: {language}

Follow STRICT SEO rules to achieve Rank Math score 90–100.

====================
OUTPUT FORMAT (JSON)
====================

{{
  "title": "...",
  "seo_title": "...",
  "meta_description": "...",
  "focus_keyword": "...",
  "keywords": ["...", "..."],
  "slug": "...",
  "article": "...",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ],
  "category": "...",
  "image_prompt": "..."
}}

====================
SEO REQUIREMENTS (Rank Math basic + title readability)
====================

1. Focus keyword (REQUIRED non-empty string):
- Choose ONE exact phrase (2–5 words) you will repeat verbatim everywhere below.
- "focus_keyword" MUST match that exact phrase (same spelling, spacing, casing you use in the article).

2. SEO title ("seo_title") — max 60 characters:
- MUST START with the EXACT "focus_keyword" phrase (same characters as in focus_keyword).
- Include at least ONE number (e.g. 5, 7, 10, 2026).
- Include a POWER word (e.g. Best, Ultimate, Proven, Complete, Essential, Top, Free, Quick).
- Include a SENTIMENT word (positive OR negative), e.g. Easy, Simple, Great, Amazing, Worst, Never, Avoid, Bad, Good.

3. Meta description — 140–160 characters:
- MUST START with the EXACT "focus_keyword" phrase (then continue with benefit + CTA like Discover, Learn, Get).

4. Slug:
- Lowercase, hyphens only; MUST contain every word from "focus_keyword" (slug can add extra words after).

5. Title ("title"):
- Reader-facing H1 idea; include the focus keyword naturally.

6. Article HTML ("article"):
- Length: 900–1100 words of readable text (not counting HTML tags). Do not go under 850 words.
- First <p> paragraph: the EXACT "focus_keyword" phrase must appear in the FIRST 15 words of visible text.
- Use <h1> once, multiple <h2> and <h3>.
- At least TWO subheadings (<h2> or <h3>) must contain the EXACT "focus_keyword" phrase inside the heading text.
- Keyword density: use the EXACT "focus_keyword" phrase about 8–12 times total in body copy (roughly 1% density). Do not stuff unnaturally; vary surrounding text.
- Use <p>, <ul>, <li>; short paragraphs.

7. Readability:
- Simple language, transition words, mostly short sentences.

8. Keywords array:
- 5 items; include the focus keyword and close variations.

9. Internal link:
- At least one <a href="/related-slug">…</a> with relevant anchor text.

10. External link:
- One authority <a href="https://...">…</a> (e.g. Wikipedia) with rel="nofollow" ONLY if the site is not authoritative; prefer normal follow link to Wikipedia or similar.

11. Images inside article:
- Do NOT add fake or placeholder <img> tags (no broken URLs). The CMS adds a featured image.
- If you include any real <img src="https://...">, alt MUST be exactly the same text as "focus_keyword".

12. Image prompt:
- Short realistic scene describing a photo related to the topic (for AI image generation).

13. DO NOT:
- Markdown, code fences, commentary outside JSON, or broken JSON.

====================
IMPORTANT
====================

Return ONLY JSON.
Ensure the article is fully SEO optimized and production-ready.
"""
    return llm.generate(prompt)