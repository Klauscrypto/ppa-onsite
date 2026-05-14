#!/usr/bin/env python3
"""Daily blog post generator for ppa-onsite.de — uses Claude API."""
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

SYSTEM_PROMPT = """Du bist ein Fachautor für erneuerbare Energien und Energiewirtschaft in Deutschland.
Du schreibst präzise, informative Blogbeiträge für Geschäftskunden (CFOs, Energiemanager, Einkäufer).
Stil: professionell, sachlich, praxisnah — kein Marketing-Sprech, echter Mehrwert.
Sprache: Deutsch. Keine englischen Fachbegriffe ohne Erklärung.
Struktur: Überschriften mit ##, Absätze mit Leerzeile. Keine Aufzählungen als Ersatz für echten Inhalt."""

USER_TEMPLATE = """Schreibe einen neuen Blogbeitrag für ppa-onsite.de.

Themenbereich (eines davon wählen — je nach dem was am aktuellsten und nützlichsten ist):
- PPA Grundlagen (Power Purchase Agreement, Vertragsstruktur, Wirtschaftlichkeit)
- Grünspeicher (Batteriespeicher mit 100% erneuerbarem Ladestrom, steuerliche Vorteile)
- Grauspeicher (Netzspeicher, Peak-Shaving, Unterschiede zum Grünspeicher)
- Marktentwicklung (aktuelle Zahlen, Trends, Corporate-PPA-Markt Deutschland/Europa)
- ESG & Regulierung (CSRD, Scope 2, CBAM, GHG Protocol, Taxonomie)
- Wirtschaftlichkeit (ROI, Amortisation, Netzentgelte, Stromsteuer)
- Technologie (PV-Komponenten, Monitoring, Messtechnik, Agri-PV)

Bereits veröffentlichte Themen (NICHT wiederholen):
{recent_titles}

Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt — kein Text davor oder danach:
{{
  "title": "Prägnanter, informativer Titel (max. 80 Zeichen)",
  "category": "Exakt eine der Kategorien von oben",
  "summary": "1–2 Sätze Zusammenfassung, worum es geht und was der Leser lernt",
  "content": "Vollständiger Artikel 550–750 Wörter. Absätze mit \\n\\n getrennt. Überschriften: ## Titel\\n\\nText. Fachlich korrekt, quellenbasiert wo möglich.",
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
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find outermost { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group()
    return text


def generate_post(client, recent_titles):
    recent = "\n".join(f"- {t}" for t in recent_titles[:15]) if recent_titles else "Keine"
    prompt = USER_TEMPLATE.format(recent_titles=recent)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
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
        print("Add it as a GitHub secret named ANTHROPIC_API_KEY.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    posts = load_posts()
    recent_titles = [p["title"] for p in posts]

    print("Generating post...")
    post_data = generate_post(client, recent_titles)

    today = datetime.now().strftime("%Y-%m-%d")
    post_id = f"{today}-{len(posts) + 1:03d}"

    new_post = {"id": post_id, "date": today, **post_data}
    posts.insert(0, new_post)
    posts = posts[:MAX_POSTS]

    save_posts(posts)
    print(f"✓ Generated: {new_post['title']}")
    print(f"  Category:  {new_post['category']}")
    print(f"  Posts total: {len(posts)}")


if __name__ == "__main__":
    main()
