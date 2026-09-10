"""Find what the lexicon knows about a term.
  python lexicon/tools/lookup.py <term> [more terms]
Searches (1) the entries, (2) the raw source corpus, and prints matching files
with a line of context. Hebrew (nikud is stripped), transliteration, or English
all work; matching is case-insensitive substring.
"""
import re, sys, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
NIKUD = re.compile("[֑-ׇ]")


def strip(s):
    return NIKUD.sub("", unicodedata.normalize("NFC", s))


def scan(folder, terms, limit):
    hits = []
    for p in sorted(folder.rglob("*.md")):
        t = strip(p.read_text(encoding="utf-8", errors="replace"))
        tl = t.lower()
        for term in terms:
            i = tl.find(term.lower())
            if i >= 0:
                s = t.rfind("\n", 0, i) + 1
                e = t.find("\n", i)
                e = len(t) if e < 0 else e
                hits.append((p, term, t[s:e].strip()[:200]))
                break
        if len(hits) >= limit:
            break
    return hits


def main():
    terms = [strip(a) for a in sys.argv[1:]]
    if not terms:
        print(__doc__)
        return
    ent = scan(ROOT / "entries", terms, 50)
    print(f"== entries ({len(ent)})")
    for p, term, line in ent:
        print(f"{p.relative_to(ROOT)}  [{term}]  {line}")
    raw = scan(ROOT / "sources", terms, 60)
    print(f"\n== sources ({len(raw)})")
    for p, term, line in raw:
        print(f"{p.relative_to(ROOT)}  [{term}]  {line}")
    if not ent and not raw:
        print("nothing found; the guide has no source on this term")


if __name__ == "__main__":
    main()
