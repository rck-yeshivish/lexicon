"""Harvest Rabbi Reuven Chaim Klein's "What's in a Word?" column (Ohr Somayach)
into lexicon/sources/whats-in-a-word/.

  python lexicon/tools/harvest_wiaw.py            # catalogue + any missing bodies
  python lexicon/tools/harvest_wiaw.py --refresh  # re-download everything

Uses the public JSON API behind articles.ohr.edu (max 50 per page). Idempotent:
existing raw files are skipped unless --refresh. Output:
  sources/whats-in-a-word/catalogue.json   machine copy of the listing
  sources/whats-in-a-word/raw/<id>-<slug>.md   one article per file, YAML front
      matter (id = the API id, NOT the legacy ohr.edu/NNNN number; slug, title, date, hebrew_date, url) + body as markdown.
The catalogue.md (human/LLM index of the column) is built by build_catalogue.py.
"""
import json, re, sys, time, html, subprocess, pathlib
from repair_corpus import repair, is_mangled

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "whats-in-a-word"
RAW = SRC / "raw"
API = "https://articles.ohr.edu/api/v1/articles"
UA = "Mozilla/5.0 (lexicon harvester; personal research use)"

def get(url):
    for attempt in range(4):
        r = subprocess.run(["curl", "-sS", "-A", UA, "-H", "Accept: application/json", url],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"failed: {url}")

def html_to_md(s):
    if not s:
        return ""
    # Un-mangle BEFORE any normalisation. The API serves some articles' Hebrew
    # as UTF-8 read as cp1252, and in that form a letter's second byte can be a
    # non-breaking space; collapsing whitespace first would destroy it beyond
    # recovery (this cost the corpus its every mangled nun once already).
    if is_mangled(s):
        s = repair(s)
    s = re.sub(r"<\s*br\s*/?>", "\n", s)
    s = re.sub(r"</?(em|i)\b[^>]*>", "*", s)
    s = re.sub(r"</?(strong|b)\b[^>]*>", "**", s)
    s = re.sub(r"<sup[^>]*>(.*?)</sup>", r"[\1]", s, flags=re.S)
    s = re.sub(r"<a\b[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", s, flags=re.S)
    s = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: "\n" + "#" * int(m.group(1)) + " " + m.group(2).strip() + "\n", s, flags=re.S)
    s = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", s, flags=re.S)
    s = re.sub(r"</p\s*>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def main():
    refresh = "--refresh" in sys.argv
    SRC.mkdir(parents=True, exist_ok=True); RAW.mkdir(exist_ok=True)
    rows, page = [], 1
    while True:
        j = get(f"{API}?category_slug=whats-in-a-word&per_page=50&page={page}")
        rows += j["data"]
        if page >= j["meta"]["last_page"]:
            break
        page += 1
    cat = [{"id": r["id"], "slug": r["slug"], "title": r["title"],
            "date": r["published_at"][:10], "hebrew_date": r.get("hebrew_date"),
            "url": f"https://articles.ohr.edu/articles/{r['slug']}"} for r in rows]
    (SRC / "catalogue.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"catalogue: {len(cat)} articles")
    done = 0
    for c in cat:
        out = RAW / f"{c['id']}-{c['slug']}.md"
        if out.exists() and not refresh:
            continue
        d = get(f"{API}/{c['slug']}")["data"]
        body = html_to_md(d.get("body"))
        foot = html_to_md(d.get("footnotes"))
        head = html_to_md(d.get("header"))
        fm = "\n".join([
            "---",
            f"id: {c['id']}",
            f"slug: {c['slug']}",
            f"title: {json.dumps(c['title'], ensure_ascii=False)}",
            f"date: {c['date']}",
            f"hebrew_date: {json.dumps(c.get('hebrew_date') or '', ensure_ascii=False)}",
            f"url: {c['url']}",
            "source: \"What's in a Word?\" by Rabbi Reuven Chaim Klein, Ohr Somayach (ohr.edu). Copyright the author/Ohr Somayach; stored for private research use.",
            "---", ""])
        text = fm + f"# {c['title']}\n\n"
        if head: text += head + "\n\n"
        text += body + "\n"
        if foot: text += "\n## Footnotes\n\n" + foot + "\n"
        out.write_text(text, encoding="utf-8")
        done += 1
        time.sleep(0.4)
    print(f"downloaded {done} new bodies; raw total {len(list(RAW.glob('*.md')))}")

if __name__ == "__main__":
    main()
