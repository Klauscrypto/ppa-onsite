#!/usr/bin/env python3
"""Daily blog post generator for somv-project.de — generates DE/EN/TR in one call."""
import json
import os
import re
import sys
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    os.system(f"{sys.executable} -m pip install anthropic -q")
    import anthropic

POSTS_FILE = "html/posts.json"
MAX_POSTS = 60  # keep last 60 posts

SYSTEM_PROMPT = """You are a specialist author for renewable energy and photovoltaics, writing for SOMV Project Consulting GmbH — a German solar installation company.
You write for business clients: homeowners, SMEs, industrial customers, CFOs, energy managers.
Style: professional, factual, practical — real value, no marketing clichés.
You must write full articles in three languages: German (DE), English (EN), Turkish (TR).
Article structure: headings with ##, paragraphs separated by blank lines. No bullet lists as substitute for real content."""

USER_TEMPLATE = """Write a new trilingual blog post for somv-project.de about solar energy and photovoltaics.

Choose one of these topic areas (pick the most current/useful, avoid repeating recent posts):
- Solar Basics (planning a PV system, components, roof analysis, sizing)
- Battery Storage (self-consumption, peak-shaving, economics, lithium technology)
- Subsidies & Funding (KfW, BAFA, feed-in tariff, grid fees, electricity tax exemption)
- Market & Trends (PV market Germany/Europe, corporate solar, current statistics 2024–2026)
- ESG & Regulation (CSRD, Scope 2, CBAM, GHG Protocol, EU Taxonomy, RE100)
- Economics & ROI (payback periods, savings calculation, Netzentgelt, grid costs)
- Technology (inverters, monitoring, Agri-PV, open-space installations, carport solar)
- Residential Solar (Einfamilienhaus, Mehrfamilienhaus, balcony power stations)
- Commercial Solar (factories, logistics, retail, healthcare, agriculture)

Already published titles (DO NOT repeat these topics):
{recent_titles}

Respond ONLY with a valid JSON object — absolutely no text before or after:
{{
  "title": "German title (max 80 chars, compelling, precise)",
  "title_en": "English title (max 80 chars)",
  "title_tr": "Turkish title (max 80 chars)",
  "category": "German category (one of: Grundlagen / Batteriespeicher / Förderung / Markt / ESG & Regulierung / Wirtschaftlichkeit / Technologie / Privat / Gewerbe)",
  "category_en": "English category (one of: Basics / Battery Storage / Subsidies / Market / ESG & Regulation / Economics / Technology / Residential / Commercial)",
  "category_tr": "Turkish category (one of: Temeller / Batarya Depolama / Teşvikler / Pazar / ESG & Düzenleme / Ekonomi / Teknoloji / Konut / Ticari)",
  "summary": "German: 1-2 sentence summary of what the reader will learn",
  "summary_en": "English: 1-2 sentence summary",
  "summary_tr": "Turkish: 1-2 sentence summary",
  "content": "German: Full article 550-750 words. Use ## for section headings. Separate paragraphs with blank lines (\\n\\n). Bold key terms with **...**. Factual, sourced where possible.",
  "content_en": "English: Full article 550-750 words. Same structure as German content.",
  "content_tr": "Turkish: Full article 550-750 words. Same structure.",
  "readTime": "X min"
}}"""


def load_posts():
    if os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posts(posts):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def extract_json(text):
    """Extract JSON object from model response, tolerating markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group()
    return text


def generate_post(client, recent_titles):
    recent = "\n".join(f"- {t}" for t in recent_titles[:15]) if recent_titles else "None"
    prompt = USER_TEMPLATE.format(recent_titles=recent)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    cleaned = extract_json(raw)
    return json.loads(cleaned)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    posts = load_posts()
    recent_titles = [p["title"] for p in posts]

    print("Generating trilingual post (DE/EN/TR)...")
    post_data = generate_post(client, recent_titles)

    today = datetime.now().strftime("%Y-%m-%d")
    post_id = f"{today}-{len(posts) + 1:03d}"

    new_post = {"id": post_id, "date": today, **post_data}
    posts.insert(0, new_post)
    posts = posts[:MAX_POSTS]

    save_posts(posts)
    print(f"✓ Generated: {new_post['title']}")
    print(f"  EN: {new_post.get('title_en', '—')}")
    print(f"  TR: {new_post.get('title_tr', '—')}")
    print(f"  Category: {new_post['category']}")
    print(f"  Posts total: {len(posts)}")


if __name__ == "__main__":
    main()
