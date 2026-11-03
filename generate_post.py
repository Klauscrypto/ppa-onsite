#!/usr/bin/env python3
"""Daily blog post generator for somv-project.de — generates DE/EN/TR in one call.

Gleiches Verfahren wie alle Jarvis-Blogs („aus einer Feder“):
  1. Beitrag schreiben (Claude, DE/EN/TR)
  2. Unabhängiger Faktencheck (Fachlektor PV/Energie, korrigiert alle drei Sprachen)
  3. Prüfung im Code (Länge, KI-Meta-Sätze, Vollständigkeit)
  4. Nur wenn alles bestanden ist, kommt der Beitrag in posts.json – sonst neuer Versuch, notfalls kein Beitrag.
"""
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

Today's date is {today}. The current year is {year}. Write from today's perspective: refer to {year} as the current year, never to past years as if they were current, and do not put a year in the title unless it is {year} or later.

Already published titles (DO NOT repeat these topics):
{recent_titles}

Submit the finished post by calling the tool "publish_post". Fill every field:
- title / title_en / title_tr: max 80 chars, compelling, precise
- category: one of Grundlagen / Batteriespeicher / Förderung / Markt / ESG & Regulierung / Wirtschaftlichkeit / Technologie / Privat / Gewerbe
- category_en: one of Basics / Battery Storage / Subsidies / Market / ESG & Regulation / Economics / Technology / Residential / Commercial
- category_tr: one of Temeller / Batarya Depolama / Teşvikler / Pazar / ESG & Düzenleme / Ekonomi / Teknoloji / Konut / Ticari
- summary / summary_en / summary_tr: 1-2 sentences on what the reader will learn
- content / content_en / content_tr: full article, 550-750 words each. Use ## for section headings, blank lines between paragraphs, **bold** for key terms.

Facts (strict – a specialist editor checks the post afterwards):
- Only well-established facts. Do not invent statistics, studies, sources, quotes, prices or subsidy rates.
- Subsidy programmes, tariffs and legal thresholds change often: describe them generally and recommend checking
  the current conditions, unless you are certain of the figure for {year}.
- Costs and savings only as clearly marked example ranges ("for example", "roughly", "depending on the site").
- Nothing about SOMV beyond: German solar installation and consulting company for private and business clients.
- readTime: e.g. 5 min
"""

FIELDS = [
    "title", "title_en", "title_tr",
    "category", "category_en", "category_tr",
    "summary", "summary_en", "summary_tr",
    "content", "content_en", "content_tr",
    "readTime",
]

POST_TOOL = {
    "name": "publish_post",
    "description": "Submit the finished trilingual blog post.",
    "input_schema": {
        "type": "object",
        "properties": {f: {"type": "string"} for f in FIELDS},
        "required": FIELDS,
    },
}

MAX_ATTEMPTS = 3
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
MIN_WOERTER = 400
META_MUSTER = re.compile(
    r"Entschuldigung|ich meine natürlich|Als (?:KI|Sprachmodell)|As an AI|I apologi[sz]e|Here is the (?:article|post)|"
    r"Hier ist (?:der|ein) (?:Artikel|Beitrag)|```|\bLorem\b|\[(?:TODO|Platzhalter|placeholder)[^\]]*\]", re.I)

PRUEF_SYSTEM = """You are a strict specialist editor for photovoltaics, battery storage, energy law and subsidies in
Germany/EU. You check a trilingual blog post (DE/EN/TR) for somv-project.de before publication.

Check for:
1. Technical errors or outdated statements (technology, EEG, feed-in tariffs, KfW/BAFA, taxes, CSRD/ESG rules).
2. Invented statistics, studies, sources, quotes, prices, subsidy rates or deadlines.
3. Exaggerations and promises ("guaranteed", "always", "saves X").
4. Self-corrections, AI meta sentences, broken or truncated sentences, the three languages saying different things.
5. Claims about SOMV beyond: German solar installation and consulting company.

Correct the post so all problems are fixed (remove doubtful statements or phrase them carefully), in all three
languages consistently. Keep the Markdown structure. Do not shorten unnecessarily.
Submit with the tool "pruefung". freigabe = true ONLY if the corrected post can be published without concern."""

PRUEF_FELDER = ["content", "content_en", "content_tr", "summary", "summary_en", "summary_tr"]
PRUEF_TOOL = {
    "name": "pruefung",
    "description": "Result of the fact check with the corrected texts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "freigabe": {"type": "boolean"},
            "probleme": {"type": "array", "items": {"type": "string"}},
            **{f: {"type": "string"} for f in PRUEF_FELDER},
        },
        "required": ["freigabe", "probleme", *PRUEF_FELDER],
    },
}


def faktencheck(client, data):
    """Zweiter, unabhängiger Durchgang. Gibt die korrigierten Daten zurück oder wirft einen Fehler."""
    text = "\n\n".join(f"### {f}\n{data[f]}" for f in ["title", "title_en", "title_tr", *PRUEF_FELDER])
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=PRUEF_SYSTEM,
        tools=[PRUEF_TOOL],
        tool_choice={"type": "tool", "name": "pruefung"},
        messages=[{"role": "user", "content": text}],
    )
    if response.stop_reason == "max_tokens":
        raise ValueError("fact check was cut off (max_tokens reached)")
    block = next((b for b in response.content if b.type == "tool_use"), None)
    if block is None:
        raise ValueError("fact check returned no result")
    r = block.input
    for p in r.get("probleme", []):
        print(f"  Faktencheck: {p}")
    if not r.get("freigabe"):
        raise ValueError("fact check not passed: " + "; ".join(r.get("probleme", []))[:300])
    out = dict(data)
    for f in PRUEF_FELDER:
        if str(r.get(f, "")).strip():
            out[f] = r[f]
    return out


def qualitaet(data):
    gruende = []
    for f in ["content", "content_en", "content_tr"]:
        t = data[f]
        if len(t.split()) < MIN_WOERTER:
            gruende.append(f"{f} too short ({len(t.split())} words)")
        if not re.search(r"[.!?…:)\"“”»]\s*$", t.strip()):
            gruende.append(f"{f} ends mid-sentence (truncated?)")
        m = META_MUSTER.search(t)
        if m:
            gruende.append(f"{f}: AI meta phrase '{m.group(0)}'")
    return gruende


def load_posts():
    if os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posts(posts):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def generate_post(client, recent_titles):
    recent = "\n".join(f"- {t}" for t in recent_titles[:15]) if recent_titles else "None"
    now = datetime.now()
    prompt = USER_TEMPLATE.format(
        recent_titles=recent,
        today=now.strftime("%Y-%m-%d"),
        year=now.year,
    )

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=[POST_TOOL],
                tool_choice={"type": "tool", "name": "publish_post"},
                messages=[{"role": "user", "content": prompt}],
            )
            if response.stop_reason == "max_tokens":
                raise ValueError("response was cut off (max_tokens reached)")
            block = next((b for b in response.content if b.type == "tool_use"), None)
            if block is None:
                raise ValueError("model did not call publish_post")
            data = block.input
            missing = [f for f in FIELDS if not str(data.get(f, "")).strip()]
            if missing:
                raise ValueError(f"missing fields: {', '.join(missing)}")
            data = faktencheck(client, {f: data[f] for f in FIELDS})
            gruende = qualitaet(data)
            if gruende:
                raise ValueError("quality check failed: " + "; ".join(gruende))
            return data
        except Exception as e:  # noqa: BLE001
            last_error = e
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed: {e}")
    raise RuntimeError(f"Could not generate post after {MAX_ATTEMPTS} attempts: {last_error}")


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
