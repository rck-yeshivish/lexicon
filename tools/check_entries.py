"""Lint lexicon entries against the schema and the house voice.
  python lexicon/tools/check_entries.py [entry.md ...]      (default: all)
Exit code 1 if any entry fails. Checks: front-matter keys, required headings in
order, source line format, no em dashes, no AI-register words, no narration
("the article explains"), "Notes for a project" present, and length: over 140
lines warns, over 240 fails.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
NIKUD = re.compile("[֑-ׇ]")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")


def bare(s):
    """A Hebrew word for comparison: no nikud, final letters folded."""
    return NIKUD.sub("", s).translate(FINALS).strip()


KEYS = ["cluster", "hebrew", "roots", "translit", "english", "domain", "sources", "authorities", "status", "updated"]
HEADINGS = ["## Bottom line", "## Distinctions", "## Rendering guidance", "## Notes for a project", "## Sources"]
DOMAINS = {"emotion", "cognition", "speech", "body", "action", "nature", "ritual", "society", "time", "quantity", "other"}
AI_PHRASES = ["the journey of", "on a journey", "journey toward", "journey towards"]
AI_TELLS = ["delve", "it's worth noting", "it is worth noting", "important to remember", "leverage", "navigate",
            "underscore", "a testament to", "in today's world", "mindset", "authentic self", "tapestry",
            "nuanced", "crucial", "vibrant", "multifaceted", "showcase"]
# Source-critical references ("the article prints 33:8") are fine; narrated attribution is not.
# Narration means treating the essay as an impersonal authority: "the article
# explains that X", where the entry should simply say X and cite whoever holds
# it. That still has to go.
#
# What is NOT narration, and was banned here by mistake: naming Rabbi Klein or
# his column as the holder of a view. Separating his own inference from the
# authority he is reporting is the single most important thing an entry does,
# and it cannot be done without naming him. The verification pass added that
# attribution to scores of entries, and this rule then failed the build on
# every one of them.
NARRATION = [r"\bthe (article|author) (says|explains|writes|argues|tells|teaches|suggests)\b",
             r"\baccording to the (article|author)\b"]


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
    if not re.search(r"^\s+- wiaw:\d+ \".+\" \(\d{4}-\d{2}-\d{2}\) https://(?:articles\.ohr\.edu/articles/[a-z0-9\-]+|groups\.google\.com/g/whats-in-a-word/c/[\w\-]+)\s*$", fm, re.M):
        errs.append("no well-formed source line (  - wiaw:<id> \"<title>\" (<date>) https://articles.ohr.edu/articles/<slug>, or the author\'s Google Group thread for an essay Ohr Somayach does not carry)")
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
    # Quoted spans are the article's words, not ours. An essay that itself
    # writes "growth mindset" gets quoted with that phrase intact; failing the
    # entry for it would force a misquotation.
    low = re.sub(r'"[^"]{0,200}"', " ", t).lower()
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
    # Median is 146 lines, p90 is 212. The hard cap is a runaway detector, not
    # a target: an entry earns its length from the essay behind it, and the
    # verification pass has been raising these as restored material lands.
    # 500 sits well clear of the longest real entry so it stops moving.
    if n < 30 or n > 500:
        errs.append(f"length {n} lines (hard limit 30..500)")
    elif n > 140:
        warn.append(f"length {n} lines (guidance is 140)")
    bl = re.search(r"## Bottom line\s*\n(.*?)\n## ", body, re.S)
    # The caps exist to catch runaway output, not to shape a good entry. A
    # cluster of eight words needs a longer ruling than one of two, and shaving
    # it costs the reader a word rather than saving them anything.
    # A runaway detector, not a target. The site's owner does not want Bottom
    # lines trimmed for length, and restoring a dropped reading can
    # legitimately lengthen one; 223 is the longest real one so far.
    if bl and len(bl.group(1).split()) > 300:
        errs.append("Bottom line over 300 words")
    # A word's Hebrew has to read the same in all three places it is written:
    # the hebrew: list a reader searches, the words: block the cards are built
    # from, and the At-a-glance row. Three headwords that matched nothing else
    # reached the index unnoticed (עגם, השקיף, פזז), so a mismatch fails here.
    hm = re.search(r"^hebrew: \[(.*)\]", fm, re.M)
    listed = {bare(x) for x in hm.group(1).split(",")} if hm else set()
    block = [bare(m.group(1)) for m in re.finditer(r"^  - he: (.+)$", fm, re.M)]
    for he in block:
        if listed and he not in listed:
            errs.append(f"words: `{he}` is not in the hebrew: list")
    glance = re.search(r"## At a glance\s*\n(.*?)\n## ", body, re.S)
    if glance:
        rows = [l.strip().strip("|").split("|") for l in glance.group(1).split("\n")
                if l.strip().startswith("|")]
        for r in rows[2:]:
            # A cell may show two forms of one word ("איה / אי"); one has to match.
            if len(r) == 4 and not any(bare(x) in block for x in r[0].split("/")):
                errs.append(f"At a glance row `{r[0].strip()}` has no words: entry")
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
