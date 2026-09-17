"""Fetch Radak's Sefer HaShorashim for the roots the entries name.
  python tools/fetch_shorashim.py [--refresh]

Sefaria carries the Berlin 1847 edition, marked Public Domain and digitised
from the National Library of Israel. A root is looked up in two steps: the
lexicon's completion endpoint gives the headword as the edition spells it
(pointed), and the text endpoint then takes that headword as a reference.

Roots of fewer than three letters are skipped: the two- and one-letter cores
our entries carry come from Rabbi Pappenheim's scheme, not from a dictionary
of verb roots, and a bare two-letter lookup matches the wrong entry.
"""
import json, pathlib, re, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "references" / "shorashim.json"
BASE = str.maketrans("ךםןףץ", "כמנפצ")
LETTERS = re.compile("[א-ת]")
UA = {"User-Agent": "whatsinaword-build"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


FINAL = {"כ": "ך", "מ": "ם", "נ": "ן", "פ": "ף", "צ": "ץ"}


def headword(letters):
    """The edition's spelling of a root, or None if it has no entry. The
    dictionary writes a root's last letter in its final form (ברך), so a
    lookup by the folded letters alone misses every root ending in one."""
    forms = [letters]
    if letters[-1] in FINAL:
        forms.append(letters[:-1] + FINAL[letters[-1]])
    for form in forms:
        url = ("https://www.sefaria.org/api/words/completion/"
               + urllib.parse.quote(form) + "/" + urllib.parse.quote("Sefer HaShorashim"))
        for pair in get(url) or []:
            # [typed form, stored form]; the stored form carries the pointing.
            if len(pair) == 2 and pair[0].translate(BASE) == letters:
                return pair[1]
    return None


def entry(hw):
    url = "https://www.sefaria.org/api/v3/texts/" + urllib.parse.quote(f"Sefer HaShorashim, {hw}")
    d = get(url)
    if "error" in d or not d.get("versions"):
        return None
    v = d["versions"][0]
    text = v.get("text")
    text = " ".join(text) if isinstance(text, list) else (text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {"hw": hw, "text": text} if text else None


def roots_wanted():
    out = {}
    for p in sorted((ROOT / "entries").glob("*.md")):
        m = re.search(r"^roots: \[(.*)\]$", p.read_text(encoding="utf-8"), re.M)
        if not m:
            continue
        for r in [x.strip() for x in m.group(1).split(",") if x.strip()]:
            letters = "".join(LETTERS.findall(r)).translate(BASE)
            if len(letters) >= 3:
                out.setdefault(letters, r)
    return out


def main():
    store = {"meta": {}, "roots": {}}
    if OUT.exists() and "--refresh" not in sys.argv:
        store = json.loads(OUT.read_text(encoding="utf-8"))
    store["meta"] = {"work": "Radak, Sefer HaShorashim", "edition": "Berlin 1847",
                     "license": "Public Domain", "via": "Sefaria (sefaria.org)",
                     "source": "National Library of Israel"}
    want = roots_wanted()
    # A root stored empty either has no entry or failed on a flaky call, so
    # --retry-empty asks for those again rather than for the whole dictionary.
    retry = "--retry-empty" in sys.argv
    todo = [k for k in sorted(want)
            if k not in store["roots"] or (retry and not store["roots"][k])]
    print(f"{len(want)} roots of three letters or more; {len(todo)} to fetch")
    found = 0
    for i, letters in enumerate(todo, 1):
        try:
            hw = headword(letters)
            e = entry(hw) if hw else None
        except Exception as err:                      # a flaky call should not lose the run
            print(f"  {letters}: {err}")
            e = None
        store["roots"][letters] = e or {}
        found += bool(e)
        if i % 25 == 0 or i == len(todo):
            OUT.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
            print(f"  {i}/{len(todo)} ({found} found)")
        time.sleep(0.34)                              # Sefaria is a shared service
    OUT.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
    have = sum(1 for v in store["roots"].values() if v)
    print(f"{OUT.relative_to(ROOT)}: {have} of {len(store['roots'])} roots have an entry, "
          f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
