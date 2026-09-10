"""Which harvested articles are not yet drawn on by any entry?
  python lexicon/tools/coverage.py            summary + the uncovered list
  python lexicon/tools/coverage.py --groups   uncovered, grouped into series
Series parts (Part 1/2, Part 2/3...) are grouped so one entry can cover them all.
"""
import re, sys, json, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "whats-in-a-word"
RAW = SRC / "raw"

STOP = set("""the a an and or of to in is it that this as for with on by from at be are was were not but
which who whom his her its their our your my we they he she i you one two three also than then so if
what when where how all any some such very more most other into out up down over under here there
parshat parsha parshas part word words hebrew english bible torah rabbi rav reb see cf ibid
vs like lit literally means meaning mean etc per say said also thus even only just about""".split())


def auto_terms(body, n=7):
    cnt = collections.Counter(w.lower().strip(" ,.;:()[]\"'")
                              for w in re.findall(r"\*([^*\n]{2,40})\*", body))
    return [w for w, c in cnt.most_common(20)
            if re.fullmatch(r"[a-z][a-z'\-]{2,}", w) and w not in STOP and c >= 3][:n]


def reruns_of(covered):
    """The column reran some pieces under a new id; a covered twin covers both."""
    p = SRC / "reruns.json"
    if not p.exists():
        return set()
    pairs = json.load(open(p, encoding="utf-8"))["pairs"]
    out = set()
    for a, b in pairs.items():
        a = int(a)
        if a in covered:
            out.add(b)
        if b in covered:
            out.add(a)
    return out


def series_key(title):
    """Key that is equal for the parts of one series and different across series.

    Strip the part marker FIRST, in every shape the column uses: "(Part 1/2)",
    "(Part 2 of 2)", ": Part 1", " - Part 2", "Pt. 3". Only then drop a leading
    parsha or occasion prefix. Doing it the other way round makes the key of
    "Jumping for Passover: Part 1" the string "part 1", which then collides with
    every other series' first part.
    """
    t = title
    t = re.sub(r"[\s:,\-–]*\(?\s*(Part|Pt\.?)\s*\d+\s*(of|/)?\s*\d*\s*\)?\s*$", "", t, flags=re.I)
    m = re.match(r"^([A-Za-z' /\.\-]{2,40})[:\-–]\s*(.+)$", t)
    core = m.group(2) if m else t
    core = re.sub(r"[^a-z0-9 ]+", "", core.lower()).strip()
    return core if len(core) > 3 else re.sub(r"[^a-z0-9 ]+", "", t.lower()).strip()


def main():
    cat = json.load(open(SRC / "catalogue.json", encoding="utf-8"))
    covered = set()
    for p in (ROOT / "entries").glob("*.md"):
        for m in re.finditer(r"wiaw:(\d+)", p.read_text(encoding="utf-8")):
            covered.add(int(m.group(1)))
    covered |= reruns_of(covered)
    rows = []
    for a in cat:
        p = RAW / f"{a['id']}-{a['slug']}.md"
        if not p.exists():
            continue
        body = p.read_text(encoding="utf-8").split("\n---\n", 1)[-1]
        a["terms"] = auto_terms(body)
        a["key"] = series_key(a["title"])
        a["words"] = len(body.split())
        rows.append(a)
    unc = [a for a in rows if a["id"] not in covered]
    print(f"{len(rows)} harvested, {len(rows) - len(unc)} covered by {len(list((ROOT / 'entries').glob('*.md')))} entries, {len(unc)} uncovered\n")
    if "--groups" not in sys.argv:
        for a in sorted(unc, key=lambda x: x["date"], reverse=True):
            print(f"{a['id']}\t{a['date']}\t{a['title']}\t{', '.join(a['terms'])}")
        return
    groups = collections.defaultdict(list)
    for a in unc:
        groups[a["key"]].append(a)
    multi = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"{len(groups)} groups ({len(multi)} multi-part series)\n")
    for k, v in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ids = "+".join(str(a["id"]) for a in sorted(v, key=lambda x: x["date"]))
        terms = sorted({t for a in v for t in a["terms"]})
        print(f"{ids}\t{v[0]['title']}\t{', '.join(terms[:10])}")


if __name__ == "__main__":
    main()
