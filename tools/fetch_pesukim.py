"""Fetch the texts of every source the entries cite that the site can show beside
them: pesukim and mishnayos (references/pesukim.json, verse by verse) and the
Bavli and Yerushalmi (references/talmud.json, each amud or halachah as its list
of segments, from which the site picks the ones holding the entry's words).
Both files are committed, so the site build never needs the network.

  python tools/fetch_pesukim.py            # fetch what is missing
  python tools/fetch_pesukim.py --refresh  # fetch everything again

Texts come from Sefaria in its default Hebrew editions (the edition and licence
of each book are recorded under "meta"). Cantillation, meteg, paseq and the
parashah markers are removed; the vowels are kept.
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import refs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PESUKIM = ROOT / "references" / "pesukim.json"
TALMUD = ROOT / "references" / "talmud.json"
API = "https://www.sefaria.org/api/v3/texts/"

TAAMIM = re.compile("[֑-ֽ֯׀ׅׄ]")


def clean(t):
    # A paseq comes as "&thinsp;<small>׀</small>&thinsp;" between two words:
    # the thin spaces are the word break, so they become spaces, not nothing.
    t = t.replace("&thinsp;", " ").replace("&nbsp;", " ")
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\{[^}]*\}", "", t)
    t = TAAMIM.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def cited():
    verses, passages = set(), set()
    for p in sorted((ROOT / "entries").glob("*.md")):
        body = p.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        for _s, _e, kind, _b, _n, pieces in refs.find(body.replace("\n", " ")):
            for _, _, ks in pieces:
                (passages if kind in ("bavli", "yerushalmi") else verses).update(ks)
    return verses, passages


def fetch(ref):
    url = API + urllib.parse.quote(ref.replace(" ", "_")) + "?version=hebrew"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # network hiccup or rate limit: back off and retry
            if attempt == 3:
                print(f"  failed {ref}: {e}")
                return None
            time.sleep(2 * (attempt + 1))


def flat(text):
    """A Sefaria text as a flat list of strings (it nests for some books)."""
    if isinstance(text, str):
        return [text]
    out = []
    for t in text or []:
        out.extend(flat(t))
    return out


def load(path, empty):
    if path.exists() and "--refresh" not in sys.argv:
        return json.loads(path.read_text(encoding="utf-8"))
    return empty


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def main():
    want_v, want_p = cited()

    data = load(PESUKIM, {"meta": {}, "verses": {}})
    missing = sorted(k for k in want_v if k not in data["verses"])
    chapters = sorted({k.rsplit(".", 1)[0] for k in missing})
    print(f"{len(want_v)} cited verses, {len(missing)} missing, {len(chapters)} chapters to fetch")
    for n, ch in enumerate(chapters, 1):
        d = fetch(ch)
        if not d or not d.get("versions"):
            continue
        v = d["versions"][0]
        data["meta"].setdefault(ch.rsplit(".", 1)[0], {"version": v.get("versionTitle"), "license": v.get("license")})
        text = v.get("text") or []
        for i, t in enumerate(text if isinstance(text, list) else [text], 1):
            if f"{ch}.{i}" in want_v and isinstance(t, str):
                data["verses"][f"{ch}.{i}"] = clean(t)
        if n % 25 == 0:
            print(f"  verses {n}/{len(chapters)}")
            save(PESUKIM, data)
        time.sleep(0.15)
    save(PESUKIM, data)

    tal = load(TALMUD, {"meta": {}, "passages": {}})
    missing = sorted(k for k in want_p if k not in tal["passages"])
    print(f"{len(want_p)} cited dapim and halachos, {len(missing)} to fetch")
    for n, key in enumerate(missing, 1):
        d = fetch(key)
        if d and d.get("versions"):
            v = d["versions"][0]
            tal["meta"].setdefault(key.rsplit(".", 2)[0] if key.startswith("Jerusalem") else key.rsplit(".", 1)[0],
                                   {"version": v.get("versionTitle"), "license": v.get("license")})
            segs = [clean(s) for s in flat(v.get("text"))]
            tal["passages"][key] = [s for s in segs if s]
        if n % 50 == 0:
            print(f"  passages {n}/{len(missing)}")
            save(TALMUD, tal)
        time.sleep(0.15)
    save(TALMUD, tal)
    print(f"wrote {len(data['verses'])} verses, {len(tal['passages'])} passages")


if __name__ == "__main__":
    main()
