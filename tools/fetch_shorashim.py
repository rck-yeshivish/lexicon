"""Fetch Radak's Sefer HaShorashim for the roots the entries name.
  python tools/fetch_shorashim.py [--refresh] [--retry-empty] [--reformat] [--homonyms]

Sefaria carries the Berlin 1847 edition, marked Public Domain and digitised
from the National Library of Israel. The lexicon's completion endpoint gives
the edition's whole list of headwords, a letter at a time, and the text
endpoint then takes a headword as a reference.

Three things the list settles that a bare lookup by letters cannot:

  The dictionary writes a root's last letter in its final form (ברך), and our
  entries fold it (ברכ), so the two are matched folded.

  Radak gives the same letters two entries where they are two roots, most often
  one for shin and one for sin (חרשׁ and חרשׂ). Both are kept, the first under
  the root and the rest under its "more", so the page never shows one homonym
  as though it were the only one.

  Radak files a word where his grammar puts it, which is not always where our
  entries do: צאן under צון, דין under דון, מטה under נטה, גרזן under גרז. Those
  filings are listed in FILED_UNDER, each one read in his text before it went
  in, and a line is used only if his entry there actually cites the entry's
  word. Such a root is stored with "under" (his headword) and "found" (the form
  he cites). A root with neither a headword nor a line stays empty; nothing is
  mapped on a guess, and guessing was tried: it took מחילה for מחלה and נימוס
  for נמס.

Roots of fewer than three letters are skipped: the two- and one-letter cores
our entries carry come from Rabbi Pappenheim's scheme, not from a dictionary
of verb roots, and a bare two-letter lookup matches the wrong entry.
"""
import html, json, pathlib, re, sys, time, unicodedata, urllib.parse, urllib.request

import refs

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "references" / "shorashim.json"
BASE = str.maketrans("ךםןףץ", "כמנפצ")
LETTERS = re.compile("[א-ת]")
ALEFBET = "אבגדהוזחטיכלמנסעפצקרשת"
UA = {"User-Agent": "whatsinaword-build"}
LEXICON = urllib.parse.quote("Sefer HaShorashim")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        time.sleep(0.34)                              # Sefaria is a shared service
        return json.load(r)


def save(store):
    """OneDrive holds the file for a moment while it syncs the last write, so a
    refused save waits and tries again rather than losing the run."""
    for wait in (0, 2, 5, 10, 20):
        time.sleep(wait)
        try:
            OUT.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
            return
        except PermissionError as err:
            last = err
    raise last


def fold(s):
    return "".join(LETTERS.findall(s)).translate(BASE)


def headwords():
    """Every headword in the edition: folded letters -> the forms as stored.
    A stored form carries whatever pointing tells two homonyms apart."""
    out = {}
    for c in ALEFBET:
        url = f"https://www.sefaria.org/api/words/completion/{urllib.parse.quote(c)}/{LEXICON}?limit=1000"
        for pair in get(url) or []:
            if len(pair) == 2 and pair[1] not in out.setdefault(fold(pair[0]), []):
                out[fold(pair[0])].append(pair[1])
    return out


TAG = re.compile(r"<(/?)([a-zA-Z]+)[^>]*>")
HEAD = re.compile(r"^\s*<strong>\s*<big>.*?</big>\s*</strong>\s*")
REF = re.compile(r'data-ref="([^"]+)"')


def ref_key(ref):
    """Sefaria's "I Chronicles 10:10" as references/pesukim.json keys it,
    "I Chronicles.10.10": the book keeps its spaces, and only the chapter and
    the pasuk are split off with dots."""
    ref = ref.replace(":", " ").strip()
    parts = ref.rsplit(" ", 2)
    return ".".join(parts) if len(parts) == 3 else ref


def markup(raw):
    """The edition's own markup, cut down to what helps a reader: the bold it
    sets on the root's form in each pasuk, and its citations, which become
    <span class="ref">. A citation keeps where it points, as data-r, in the
    Book.Chapter.Verse form references/pesukim.json is keyed by, so the site can
    show the pasuk itself. Everything else is escaped or dropped, so the result
    is safe to place in a page as it stands."""
    out, stack, pos = [], [], 0
    for m in TAG.finditer(raw):
        out.append(html.escape(html.unescape(raw[pos:m.start()]), quote=False))
        pos = m.end()
        closing, name = m.group(1), m.group(2).lower()
        name = {"b": "strong", "a": "span"}.get(name, name)
        if name not in ("strong", "span"):
            continue
        if not closing:
            ref = REF.search(m.group(0))
            ref = ref_key(html.unescape(ref.group(1))) if ref else ""
            out.append(f'<span class="ref" data-r="{html.escape(ref, quote=True)}">'
                       if name == "span" and ref else
                       '<span class="ref">' if name == "span" else "<strong>")
            stack.append(name)
        elif stack and stack[-1] == name:
            out.append(f"</{stack.pop()}>")
    out.append(html.escape(html.unescape(raw[pos:]), quote=False))
    out.extend(f"</{n}>" for n in reversed(stack))
    s = re.sub(r"\s+", " ", "".join(out)).strip()
    # The brackets sit outside the citation in the edition; bring them in.
    return re.sub(r'\(\s*<span class="ref"([^>]*)>(.*?)</span>\s*\)', r'<span class="ref"\1>(\2)</span>', s)


def entry(hw):
    url = "https://www.sefaria.org/api/v3/texts/" + urllib.parse.quote(f"Sefer HaShorashim, {hw}")
    d = get(url)
    if "error" in d or not d.get("versions"):
        return None
    v = d["versions"][0]
    raw = v.get("text")
    raw = " ".join(raw) if isinstance(raw, list) else (raw or "")
    # Each entry opens with its own headword, which the page already shows and
    # which otherwise runs straight into the first pasuk.
    raw = HEAD.sub("", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", html.unescape(text)))
    text = re.sub(r"\s+", " ", text).strip()
    return {"hw": hw, "text": text, "html": markup(raw)} if text else None


# Where Radak files a word whose root, as our entries write it, is not one of
# his headwords. Each line was checked against his text before it went in, and
# lookup() checks it again: a line is used only if his entry there cites the
# entry's word. The patterns are his grammar's: a hollow root under its vav
# (דין under דון), a final yod or alef under heh (עני under ענה), a noun under
# the root it is built on (מלאך under לאך, גרזן under גרז). A word he treats in
# two places (מטה, of which he writes ועוד נכתבו בשרש נטה) names both.
# A value is his headword, folded; two headwords where he treats the word twice;
# and headword=form where the form he cites is not the entry's own spelling, or
# is pointed to tell it from a homograph (שָׁנִי crimson, not שֵׁנִי second).
FILED_UNDER = {
    # hollow roots, which he heads with vav
    "דינ": "דונ", "לינ": "לונ=ילינ", "ניב": "נוב", "קיא": "קוא", "שיב": "שוב", "שימ": "שומ",
    "צאנ": "צונ", "צוצ": "ציצ",
    # a final yod or alef, which he heads with heh (and טלה, the other way)
    "ארי": "ארה", "גדי": "גדה", "מזי": "מזה", "עני": "ענה", "צרי": "צרה", "שני": "שנה=שָׁנִי",
    "טלה": "טלא", "אחו": "אחה",
    # a noun under the root it is built on
    "אשכל": "שכל", "אשכר": "שכר", "אתיק": "נתק", "גרזנ": "גרז", "מלאכ": "לאכ", "שלחנ": "שלח",
    "תירש": "ירש", "תרמ": "רומ", "קלנ": "קלה", "פתמ": "פתה", "תיב": "תבה", "גפה": "נגפ",
    "מטה": "נטה=המטה מטט=המטה", "מהדע": "מדע ידע", "הנה": "הנ", "למה": "מה", "כנמ": "כנ", "יממ": "ימ",
    "אממ": "אמ", "נכא": "נכת=נכאת", "ארל": "אראל=אראלמ",
    # sin for our samech, and his note in רמס: והנכתב בשי"ן ענינו קרוב לזה
    "כרס": "כרש=כרשו", "רמש": "רמס",
    # Added to his own entry rather than standing in for it: see lookup().
    "שיר": "+שור=שִׁיר",
}

TOKEN = re.compile("[א-ת֑-ׇֽֿׁׂׅׄ]+")
POINTED = re.compile("[ְ-ׇּׁׂ]")
ACCENTS = re.compile("[֑-ֽ֯]")       # cantillation and meteg, which a pasuk carries and a lemma does not
PREFIX = "ובהלכמ"


def lean(w):
    """A word without its vowel letters: Radak's תירש for our תירוש."""
    return w[:1] + "".join(c for c in w[1:] if c not in "וי")


def cited(e, targets):
    """The form in Radak's entry that is the entry's word, or None. The forms
    he points or the edition sets in bold come first, being the words he is
    discussing; his running prose comes last, since it is full of look-alikes
    (ענין for עני). A form may carry one prefix letter, or be spelled without
    the vowel letters ours has; never the reverse, or אלון would pass for אילן."""
    plain = re.sub(r"<[^>]+>", " ", e["html"])
    marked = [t for t in TOKEN.findall(plain) if POINTED.search(t)]
    for b in re.findall(r"<strong>(.*?)</strong>", e["html"]):
        marked += TOKEN.findall(b)
    # FILED_UNDER named a pointed form: that word and no homograph. NFD puts a
    # letter's dot and its vowel in one order however each side typed them.
    same = lambda x: unicodedata.normalize("NFD", ACCENTS.sub("", x))
    exact = {same(x) for x in targets if POINTED.search(x)}
    if exact:
        return next((t for t in marked if same(t) in exact), None)
    for forms, loose in ((marked, False), (marked, True), (TOKEN.findall(plain), True)):
        for t in forms:
            w = fold(t)
            for cut in [w] + ([w[1:]] if loose and w[:1] in PREFIX else []):
                if any(cut == x or (loose and len(cut) >= 3 and cut == lean(x)) for x in targets):
                    return t
    return None


def lookup(letters, targets, heads):
    """A root's entries: by its own headword, or by FILED_UNDER where Radak's
    entry bears the table out. A root he has twice (shin and sin) keeps both."""
    found = [e for e in (entry(hw) for hw in heads.get(letters, [])) if e]
    # A filing marked with + is added to whatever his own headword gave, rather
    # than standing in for it. Our שיר is the song, and his entry under those
    # letters is the ornament, ענקיא ושירי, with no singing in it; the singing is
    # under שור, a hollow root. Both belong on that root, and ordered() puts the
    # one that cites the entry's word first.
    add = [u for u in FILED_UNDER.get(letters, "").split() if u.startswith("+")]
    if not found or add:
        for under in (add or FILED_UNDER.get(letters, "").split()):
            # The form asked for must not be overwritten by the one found: the
            # loop runs once per headword these letters carry, and reusing the
            # name made the second headword be searched for the first one's hit.
            # That is how שיר took his שֹור, the princes, and missed שׁור, the
            # singing, which is the entry the filing is for.
            under, _, want = under.lstrip("+").partition("=")
            for e in (entry(hw) for hw in heads.get(under, [])):
                hit = e and cited(e, {want} if want else targets)
                if hit and not any(p["hw"] == e["hw"] for p in found):
                    found.append(dict(e, under=e["hw"], found=hit))
        if letters in FILED_UNDER and not found:
            print(f"  {letters}: FILED_UNDER names {FILED_UNDER[letters]}, but no entry there cites "
                  f"{' '.join(sorted(targets))}; left empty")
    return ordered(found, targets)


def ordered(parts, targets):
    """Of two entries for the same letters, the one that cites the entry's word
    goes first: for an entry on oaths, שׁבע before שׂבע. Both are still shown."""
    parts = sorted(parts, key=lambda e: not cited(e, targets))
    return dict(parts[0], **({"more": parts[1:]} if parts[1:] else {})) if parts else {}


def roots_wanted():
    """letters -> the words of our entries that carry that root."""
    out = {}
    for p in sorted((ROOT / "entries").glob("*.md")):
        src = p.read_text(encoding="utf-8")
        m = re.search(r"^roots: \[(.*)\]$", src, re.M)
        if not m:
            continue
        h = re.search(r"^hebrew: \[(.*)\]$", src, re.M)
        words = [w for x in (h.group(1).split(",") if h else []) for w in x.split()]
        for r in [x.strip() for x in m.group(1).split(",") if x.strip()]:
            letters = fold(r)
            if len(letters) >= 3:
                mine = [fold(w) for w in words if refs.matches_root(w, list(letters))]
                out.setdefault(letters, set()).update(mine or [letters])
    return out


def main():
    store = {"meta": {}, "roots": {}}
    if OUT.exists() and "--refresh" not in sys.argv:
        store = json.loads(OUT.read_text(encoding="utf-8"))
    store["meta"] = {"work": "Radak, Sefer HaShorashim", "edition": "Berlin 1847",
                     "license": "Public Domain", "via": "Sefaria (sefaria.org)",
                     "source": "National Library of Israel"}
    if not store.get("headwords") or "--refresh" in sys.argv:
        store["headwords"] = headwords()
        print(f"{sum(map(len, store['headwords'].values()))} headwords in the edition")
    heads, have = store["headwords"], store["roots"]
    want = roots_wanted()
    for k, v in have.items():                         # an entry's words may have changed since
        if v.get("more") and k in want:
            have[k] = ordered([{x: y for x, y in v.items() if x != "more"}] + v["more"], want[k])
    # A root stored empty either has no entry or failed on a flaky call, so
    # --retry-empty asks for those again rather than for the whole dictionary.
    # --reformat reads again the entries stored before the markup was kept, and
    # --homonyms the roots stored before a second entry of the same letters was.
    retry, reformat, homonyms = (f in sys.argv for f in ("--retry-empty", "--reformat", "--homonyms"))
    # --root reads named roots again and nothing else, for a filing added to
    # FILED_UNDER after the dictionary was already down: refetching all 930 to
    # correct one of them asks Sefaria for the whole work a second time.
    named = {fold(a) for a in sys.argv[1:] if not a.startswith("--") and LETTERS.search(a)}
    if named:
        todo = [k for k in sorted(want) if k in named]
    else:
        todo = [k for k in sorted(want)
                if k not in have or (retry and not have[k])
                or (reformat and have[k] and "html" not in have[k])
                or (homonyms and have[k] and len(heads.get(k, [])) > 1 and "more" not in have[k])]
    print(f"{len(want)} roots of three letters or more; {len(todo)} to fetch")
    found = 0
    for i, letters in enumerate(todo, 1):
        try:
            e = lookup(letters, want[letters], heads)
        except Exception as err:                      # a flaky call should not lose the run
            print(f"  {letters}: {err}")
            e = None
        have[letters] = e or have.get(letters) or {}
        found += bool(e)
        # Each filed part is reported on its own: with an added filing the
        # first part is his own headword and carries no "under" at all.
        for part in ([e] + e.get("more", []) if e else []):
            if part.get("under"):
                print(f"  {letters} ({' '.join(sorted(want[letters]))}): "
                      f"under {part['under']}, citing {part['found']}")
        if i % 25 == 0 or i == len(todo):
            save(store)
            print(f"  {i}/{len(todo)} ({found} found)", flush=True)
    save(store)
    n = sum(1 for v in have.values() if v)
    print(f"{OUT.relative_to(ROOT)}: {n} of {len(have)} roots have an entry "
          f"({sum(1 for v in have.values() if v.get('under'))} under another headword, "
          f"{sum(1 for v in have.values() if v.get('more'))} with a homonym), "
          f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
