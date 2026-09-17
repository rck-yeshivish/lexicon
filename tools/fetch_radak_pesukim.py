"""Fetch the pesukim Radak cites in Sefer HaShorashim, so the roots page can show
a citation's text where the entries' own store does not already hold it.

  python tools/fetch_radak_pesukim.py [--refresh]

references/shorashim.json carries each citation's target as data-r, in the
Book.Chapter.Verse form references/pesukim.json is keyed by, and this fills
references/radak-pesukim.json with the ones that store is missing. The two are
kept apart because pesukim.json answers to the entries: tools/fetch_pesukim.py
rebuilds it from what the entries cite, and Radak's nine thousand would be
swept out of it on the next refresh.

His Talmud citations are left alone. They are a few hundred, the roots page
does not show them, and an amud is not a pasuk.
"""
import json, pathlib, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fetch_pesukim as fp  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "references" / "radak-pesukim.json"
VERSE = re.compile(r".+\.\d+\.\d+")


def cited():
    """Every pasuk Radak cites, by its Book.Chapter.Verse key."""
    s = json.loads((ROOT / "references" / "shorashim.json").read_text(encoding="utf-8"))
    out = set()
    for v in s["roots"].values():
        for p in ([v] + v.get("more", [])) if v else []:
            out.update(re.findall(r'data-r="([^"]+)"', p["html"]))
    return {r for r in out if VERSE.fullmatch(r)}


def main():
    store = {"meta": {}, "verses": {}}
    if OUT.exists() and "--refresh" not in sys.argv:
        store = json.loads(OUT.read_text(encoding="utf-8"))
    # Whatever the entries already cite is served from pesukim.json, so it is
    # not stored twice; the site reads both.
    theirs = set(json.loads((ROOT / "references" / "pesukim.json")
                            .read_text(encoding="utf-8"))["verses"])
    want = cited() - theirs
    missing = {k for k in want if k not in store["verses"]}
    chapters = sorted({k.rsplit(".", 1)[0] for k in missing})
    print(f"{len(want)} pesukim Radak cites that the entries do not; "
          f"{len(missing)} missing, in {len(chapters)} chapters")

    def one(ch):
        d = fp.fetch(ch)
        if not d or not d.get("versions"):
            return ch, None, []
        v = d["versions"][0]
        text = v.get("text") or []
        got = []
        for i, t in enumerate(text if isinstance(text, list) else [text], 1):
            if f"{ch}.{i}" in want and isinstance(t, str):
                got.append((f"{ch}.{i}", fp.clean(t)))
        return ch, v, got

    with ThreadPoolExecutor(4) as ex:
        for n, f in enumerate(as_completed([ex.submit(one, c) for c in chapters]), 1):
            ch, v, got = f.result()
            if v:
                store["meta"].setdefault(ch.rsplit(".", 1)[0],
                                         {"version": v.get("versionTitle"), "license": v.get("license")})
            store["verses"].update(got)
            if n % 100 == 0 or n == len(chapters):
                OUT.write_text(json.dumps(store, ensure_ascii=False, indent=0, sort_keys=True),
                               encoding="utf-8")
                print(f"  {n}/{len(chapters)} chapters, {len(store['verses'])} pesukim", flush=True)
    OUT.write_text(json.dumps(store, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    short = sorted(want - set(store["verses"]))
    print(f"{OUT.relative_to(ROOT)}: {len(store['verses'])} pesukim, "
          f"{OUT.stat().st_size / 1e6:.1f} MB"
          + (f"; {len(short)} not returned, e.g. {short[:4]}" if short else ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
