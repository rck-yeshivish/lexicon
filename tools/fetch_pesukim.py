"""Fetch the Hebrew text of every pasuk and mishnah the entries cite, for the
site's pesukim panel. Writes references/pesukim.json, which is committed, so
the site build never needs the network.

  python tools/fetch_pesukim.py            # fetch what is missing
  python tools/fetch_pesukim.py --refresh  # fetch everything again

Texts come from Sefaria: Tanach in "Miqra according to the Masorah" (CC-BY-SA),
the Mishnah in its default Hebrew edition. Cantillation, meteg, paseq and the
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
OUT = ROOT / "references" / "pesukim.json"
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


def cited_keys():
    keys = set()
    for p in sorted((ROOT / "entries").glob("*.md")):
        body = p.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        body = body.split("\n## Sources")[0]
        for *_, pieces in refs.find(body.replace("\n", " ")):
            for _, _, ks in pieces:
                keys.update(ks)
    return keys


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


def main():
    data = {"meta": {}, "verses": {}}
    if OUT.exists() and "--refresh" not in sys.argv:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    want = cited_keys()
    missing = sorted(k for k in want if k not in data["verses"])
    chapters = sorted({k.rsplit(".", 1)[0] for k in missing})
    print(f"{len(want)} cited verses, {len(missing)} missing, {len(chapters)} chapters to fetch")
    for n, ch in enumerate(chapters, 1):
        d = fetch(ch)
        if not d or not d.get("versions"):
            continue
        v = d["versions"][0]
        book = ch.rsplit(".", 1)[0]
        data["meta"].setdefault(book, {"version": v.get("versionTitle"), "license": v.get("license")})
        text = v.get("text") or []
        if isinstance(text, str):
            text = [text]
        for i, t in enumerate(text, 1):
            k = f"{ch}.{i}"
            if k in want and isinstance(t, str):
                data["verses"][k] = clean(t)
        if n % 25 == 0:
            print(f"  {n}/{len(chapters)}")
            OUT.write_text(json.dumps(data, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
        time.sleep(0.15)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['verses'])} verses")


if __name__ == "__main__":
    main()
