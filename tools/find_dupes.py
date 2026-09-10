"""Find near-duplicate source articles and overlapping entries.
  python lexicon/tools/find_dupes.py
The column occasionally reruns a piece under a new title, and two agents working
different batches can then write two entries for one cluster. This reports:
  1. article pairs whose bodies overlap heavily (candidate reruns)
  2. entry pairs whose `hebrew` or `translit` lists overlap heavily (merge these)
"""
import re, json, pathlib, itertools, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "whats-in-a-word"
RAW = SRC / "raw"


def shingles(text, n=6):
    w = re.findall(r"[a-z]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(0, max(0, len(w) - n), 3)}


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def fm_list(text, key):
    m = re.search(rf"^{key}:\s*\[(.*?)\]", text, re.M | re.S)
    return {v.strip().lower() for v in m.group(1).split(",") if v.strip()} if m else set()


print("== near-duplicate articles (body overlap >= 0.35)")
arts = []
for p in sorted(RAW.glob("*.md")):
    t = p.read_text(encoding="utf-8")
    arts.append((p.stem, re.search(r'^title: "?(.*?)"?$', t, re.M).group(1), shingles(t.split("\n---\n", 1)[-1])))
buckets = collections.defaultdict(list)
for stem, title, sh in arts:
    for s in itertools.islice(sorted(sh), 0, 40):
        buckets[s].append((stem, title, sh))
seen = set()
for cands in buckets.values():
    for (s1, t1, sh1), (s2, t2, sh2) in itertools.combinations(cands, 2):
        key = tuple(sorted((s1, s2)))
        if key in seen:
            continue
        seen.add(key)
        j = jaccard(sh1, sh2)
        if j >= 0.35:
            print(f"  {j:.2f}  {s1}  ==  {s2}   [{t1} / {t2}]")

print("\n== overlapping entries (hebrew or translit overlap >= 0.4)")
ents = []
for p in sorted((ROOT / "entries").glob("*.md")):
    t = p.read_text(encoding="utf-8")
    ents.append((p.name, fm_list(t, "hebrew"), fm_list(t, "translit")))
for (n1, h1, r1), (n2, h2, r2) in itertools.combinations(ents, 2):
    jh, jr = jaccard(h1, h2), jaccard(r1, r2)
    if max(jh, jr) >= 0.4:
        print(f"  heb {jh:.2f} translit {jr:.2f}  {n1}  ==  {n2}")
