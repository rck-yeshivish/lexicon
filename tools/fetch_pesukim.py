"""Fetch the texts of every source the entries cite that the site can show beside
them: pesukim and mishnayos (references/pesukim.json, verse by verse, with the
comments on a pasuk an entry cites as a commentator's, "Rashi to Bereishis
13:3", under "comments") and the Bavli and Yerushalmi (references/talmud.json,
each amud or halachah as its list of segments, from which the site picks the
ones holding the entry's words). Both files are committed, so the site build
never needs the network.

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
import urllib.error
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
    """Verse keys; the comments on a pasuk that an entry cites as a
    commentator's ("Rashi to Bereishis 13:3"); and each cited daf or halachah
    with the commentaries worth trying on it and the (bare) headwords of the
    entries that cite it."""
    verses, comments, passages = set(), set(), {}
    for p in sorted((ROOT / "entries").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"^hebrew:\s*\[(.*)\]", text, re.M)
        words = {refs.bare(h.strip()) for h in m.group(1).split(",")} if m else set()
        body = text.split("\n---\n", 1)[1]
        for _s, _e, kind, _b, _n, pieces in refs.find(body.replace("\n", " "), entry=p.stem):
            for _, _, ks in pieces:
                if kind in ("bavli", "yerushalmi"):
                    daf = next(k for k in ks if " on " not in k)
                    entry = passages.setdefault(daf, {"comms": [], "cited": [], "words": set()})
                    # "Rashi to Beitzah 4a" puts Rashi's comment first: it is
                    # what the entry cites, so it is fetched whatever the
                    # Gemara holds.
                    into = entry["cited"] if " on " in ks[0] else entry["comms"]
                    into += [c for c in ks if " on " in c and c not in into]
                    entry["words"] |= words
                else:
                    verses.update(k for k in ks if " on " not in k)
                    comments.update(k for k in ks if " on " in k)
    return verses, comments, passages


def has_word(segs, words):
    text = refs.bare(" ".join(segs))
    cores = {w[:-1] if len(w) > 3 and w[-1] in "אה" else w for w in words if w and " " not in w}
    return any(c in text for c in cores)


def fetch(ref, hebrew=True):
    url = (API + urllib.parse.quote(refs.sefaria(ref).replace(" ", "_"))
           + ("?version=hebrew" if hebrew else ""))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:  # no such book on Sefaria: asking again will not help
                return None
            if attempt == 3:
                print(f"  failed {ref}: {e}")
                return None
            time.sleep(2 * (attempt + 1))
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
    # OneDrive holds the file now and then while it syncs, and the write fails
    # with "Invalid argument"; a moment later it goes through.
    for attempt in range(5):
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(2)


def main():
    want_v, want_c, want_p = cited()

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

    # The comments on the pesukim that the entries cite as a commentator's,
    # a chapter of his at a time. A comment Sefaria has only in another
    # language (Rav Hirsch's, in his German and in English) is kept as "link":
    # it can be opened there, though its words cannot be matched here. A pasuk
    # he has nothing on, or a book Sefaria does not carry for him, is kept empty.
    com = data.setdefault("comments", {})
    missing = sorted(k for k in want_c if k not in com)
    chapters = sorted({k.rsplit(".", 1)[0] for k in missing})
    print(f"{len(want_c)} cited comments on pesukim, {len(missing)} missing, {len(chapters)} chapters to fetch")
    for n, ch in enumerate(chapters, 1):
        elsewhere = False
        d = fetch(ch)
        v = (d or {}).get("versions") or [{}]
        text = v[0].get("text") or []
        if not flat(text) and d is not None:
            d = fetch(ch, hebrew=False)
            text = ((d or {}).get("versions") or [{}])[0].get("text") or []
            elsewhere = True
        elif flat(text):
            # Kept apart from "meta", which names the editions of the pesukim.
            data.setdefault("comment_meta", {}).setdefault(
                refs.sefaria(ch).rsplit(".", 1)[0],
                {"version": v[0].get("versionTitle"), "license": v[0].get("license")})
        text = text if isinstance(text, list) else [text]
        for k in (k for k in missing if k.rsplit(".", 1)[0] == ch):
            i = int(k.rsplit(".", 1)[1])
            segs = [s for s in (clean(x) for x in flat(text[i - 1] if i <= len(text) else [])) if s]
            com[k] = ("link" if segs else []) if elsewhere else segs
        if n % 25 == 0:
            print(f"  comments {n}/{len(chapters)}")
            save(PESUKIM, data)
        time.sleep(0.15)
    save(PESUKIM, data)

    tal = load(TALMUD, {"meta": {}, "passages": {}})

    def get(key):
        if key in tal["passages"]:
            return tal["passages"][key]
        d = fetch(key)
        time.sleep(0.15)
        if not d or not d.get("versions"):
            tal["passages"][key] = []
            return []
        v = d["versions"][0]
        book = key.rsplit(".", 2)[0] if key.startswith("Jerusalem") else key.rsplit(".", 1)[0]
        if " on " in book:
            book = book.split(" on ")[0]
        tal["meta"].setdefault(book, {"version": v.get("versionTitle"), "license": v.get("license")})
        tal["passages"][key] = [s for s in (clean(s) for s in flat(v.get("text"))) if s]
        return tal["passages"][key]

    print(f"{len(want_p)} cited dapim and halachos")
    for n, (key, info) in enumerate(sorted(want_p.items()), 1):
        # The commentaries are fetched only where the Gemara's own text lacks
        # every word of the entries that cite it, or where an entry cites the
        # commentary itself.
        for c in info["cited"]:
            get(c)
        if not has_word(get(key), info["words"]):
            for c in info["comms"]:
                get(c)
        if n % 50 == 0:
            print(f"  passages {n}/{len(want_p)}")
            save(TALMUD, tal)
    save(TALMUD, tal)
    print(f"wrote {len(data['verses'])} verses, {len(tal['passages'])} passages")


if __name__ == "__main__":
    main()
