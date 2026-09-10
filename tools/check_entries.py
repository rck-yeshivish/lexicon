"""Lint lexicon entries against the schema and the house voice.
  python lexicon/tools/check_entries.py [entry.md ...]      (default: all)
Exit code 1 if any entry fails. Checks: front-matter keys, required headings in
order, source line format, no em dashes, no AI-register words, no narration
("the article explains"), "Notes for a project" present, and length: over 140
lines warns, over 200 fails.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEYS = ["cluster", "hebrew", "roots", "translit", "english", "domain", "sources", "authorities", "status", "updated"]
HEADINGS = ["## Bottom line", "## Distinctions", "## Rendering guidance", "## Notes for a project", "## Sources"]
DOMAINS = {"emotion", "cognition", "speech", "body", "action", "nature", "ritual", "society", "time", "quantity", "other"}
AI_PHRASES = ["the journey of", "on a journey", "journey toward", "journey towards"]
AI_TELLS = ["delve", "it's worth noting", "it is worth noting", "important to remember", "leverage", "navigate",
            "underscore", "a testament to", "in today's world", "mindset", "authentic self", "tapestry",
            "nuanced", "crucial", "vibrant", "multifaceted", "showcase"]
# Source-critical references ("the article prints 33:8") are fine; narrated attribution is not.
NARRATION = [r"\bthe (article|column|author) (says|explains|writes|argues|tells|teaches|suggests)\b",
             r"\bRabbi Klein (says|writes|explains|argues)\b", r"\baccording to the (article|author)\b"]


def check(p):
    t = p.read_text(encoding="utf-8")
    errs, warn = [], []
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not m:
        return ["no front matter"], []
    fm = m.group(1)
    for k in KEYS:
        if not re.search(rf"^{k}:", fm, re.M):
            errs.append(f"front matter missing `{k}`")
    dm = re.search(r"^domain:\s*(\S+)", fm, re.M)
    if dm and dm.group(1) not in DOMAINS:
        errs.append(f"domain `{dm.group(1)}` not in the allowed set")
    if not re.search(r"^\s+- wiaw:\d+ \".+\" \(\d{4}-\d{2}-\d{2}\) https://articles\.ohr\.edu/articles/[a-z0-9\-]+\s*$", fm, re.M):
        errs.append("no well-formed source line (  - wiaw:<id> \"<title>\" (<date>) https://articles.ohr.edu/articles/<slug>)")
    if re.search(r"^hebrew:\s*\[\s*\]", fm, re.M) or not re.search(r"[א-ת]", fm):
        errs.append("hebrew list empty or not Hebrew script")
    if not re.search(r"^status:\s*(draft|reviewed)\s*$", fm, re.M):
        errs.append("status must be draft or reviewed")
    if "<" in fm and ">" in fm:
        errs.append("template placeholder left in front matter")
    body = t[m.end():]
    pos = -1
    for h in HEADINGS:
        i = body.find(h + "\n")
        if i < 0:
            errs.append(f"missing heading `{h}`")
        elif i < pos:
            errs.append(f"heading `{h}` out of order")
        else:
            pos = i
    if "—" in t or "–" in body.replace("(", "").replace(")", ""):
        if "—" in t:
            errs.append("em dash present")
    if "—" not in t and "–" in body:
        errs.append("en dash in body (use a hyphen, 'to', or recast)")
    low = t.lower()
    for w in AI_TELLS + AI_PHRASES:
        if w in low:
            errs.append(f"AI-register word: `{w}`")
    prose = body.split("## Sources")[0]
    for pat in NARRATION:
        if re.search(pat, prose, re.I):
            errs.append(f"narration: /{pat}/")
    if re.search(r"<[^>]{3,}>", body):
        errs.append("template placeholder left in body")
    n = t.count("\n")
    if n < 30 or n > 200:
        errs.append(f"length {n} lines (hard limit 30..200)")
    elif n > 140:
        warn.append(f"length {n} lines (guidance is 140)")
    bl = re.search(r"## Bottom line\s*\n(.*?)\n## ", body, re.S)
    if bl and len(bl.group(1).split()) > 170:
        errs.append("Bottom line over 170 words")
    return errs, warn


def main():
    files = [pathlib.Path(a) for a in sys.argv[1:]] or sorted((ROOT / "entries").glob("*.md"))
    bad = 0
    for p in files:
        errs, warn = check(p)
        if errs:
            bad += 1
            print(f"FAIL {p.name}")
        elif warn:
            print(f"warn {p.name}")
        else:
            print(f"ok   {p.name}")
        for e in errs:
            print(f"     - {e}")
        for w in warn:
            print(f"     ~ {w}")
    print(f"\n{len(files) - bad}/{len(files)} entries pass")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
