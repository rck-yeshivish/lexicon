"""Split the uncovered articles into agent-sized batch files.
  python lexicon/tools/make_batches.py <out_dir> [--size 10] [--exclude <tsv> ...]

--exclude takes batch files that are still being worked by a running agent. Their
articles are not covered yet (no entry exists), so without this they would be
handed to a second agent and drafted twice under two filenames.
Writes <out_dir>/batch-NN.tsv, each line: ids<TAB>title<TAB>terms.
Groups multi-part series onto one line (one entry covers the series).
Ordering puts abstract and conceptual clusters first, concrete nouns last, so
the most useful entries get written first if the run is cut short.
"""
import re, sys, json, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "whats-in-a-word"
RAW = SRC / "raw"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from coverage import auto_terms, series_key, reruns_of  # noqa: E402

ABSTRACT = set("""soul spirit mind heart wisdom knowledge understand thought word speak say tell voice
sin guilt evil good righteous wicked holy pure impure judge law justice mercy kindness love hate fear
joy sorrow anger pride humble honor shame glory truth lie faith trust hope pray bless curse
time eternity beginning end life death world create form make destroy save redeem
power strength weak rich poor king rule servant slave free work rest peace war
teach learn remember forget see hear know understand nothing everything all
give take steal own inherit gift reward punish repent forgive atone""".split())
CONCRETE = set("""bird beast animal fish snake insect locust plant tree flower fruit vegetable grain bread
cake wine oil stone metal gold silver iron tool hammer knife rope basket vessel pot cloth garment
house tent door window wall city river mountain sea star moon sun rain snow wind color red white black
horse donkey camel sheep goat ox lion bear wolf fox dog cat mouse hair skin bone tooth nose ear eye
month name jericho ashkenaz persia egypt rome greek purim chanukah""".split())


def score(title, terms):
    t = (title + " " + " ".join(terms)).lower()
    a = sum(1 for w in ABSTRACT if w in t)
    c = sum(1 for w in CONCRETE if w in t)
    return c - a


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 10
    cat = json.load(open(SRC / "catalogue.json", encoding="utf-8"))
    covered = set()
    for p in (ROOT / "entries").glob("*.md"):
        for m in re.finditer(r"wiaw:(\d+)", p.read_text(encoding="utf-8")):
            covered.add(int(m.group(1)))
    covered |= reruns_of(covered)
    while "--exclude" in sys.argv:
        i = sys.argv.index("--exclude")
        for line in pathlib.Path(sys.argv[i + 1]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                covered |= {int(x) for x in line.split("	")[0].split("+")}
        del sys.argv[i:i + 2]
    groups = collections.defaultdict(list)
    for a in cat:
        p = RAW / f"{a['id']}-{a['slug']}.md"
        if not p.exists() or a["id"] in covered:
            continue
        body = p.read_text(encoding="utf-8").split("\n---\n", 1)[-1]
        a["terms"] = auto_terms(body)
        groups[series_key(a["title"])].append(a)
    rows = []
    for k, v in groups.items():
        v.sort(key=lambda x: x["date"])
        title = re.sub(r"\s*\(?Part.*$", "", v[0]["title"], flags=re.I).strip()
        terms = []
        for a in v:
            for t in a["terms"]:
                if t not in terms:
                    terms.append(t)
        rows.append((score(title, terms), title, [a["id"] for a in v], terms))
    rows.sort(key=lambda r: (r[0], r[1]))
    n = 0
    for i in range(0, len(rows), size):
        n += 1
        chunk = rows[i:i + size]
        lines = [f"{'+'.join(str(x) for x in ids)}\t{title}\t{', '.join(terms[:8])}"
                 for _, title, ids, terms in chunk]
        (out / f"batch-{n:02d}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"batch-{n:02d}.tsv  {len(chunk)} groups  e.g. {chunk[0][1]}")
    print(f"\n{len(rows)} groups -> {n} batches of {size}")


if __name__ == "__main__":
    main()
