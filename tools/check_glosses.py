"""Check references/radak-gloss.json against Radak's own entries.

  python tools/check_glosses.py                     # the whole file
  python tools/check_glosses.py --file batch.json   # one batch, before merging

The glosses are English written from his Hebrew, and the danger in writing 859
of them is a sentence that reads well and says something he never said. This
catches the kinds of invention a reader could not catch for himself:

  a Hebrew phrase quoted that is not in his entry,
  a pasuk cited that he does not cite,
  an authority named whom he does not name.

It cannot check whether the English renders the Hebrew rightly. That is what a
human review is for, and why a gloss stays "draft" until one has read it.

House style is checked too: no em dashes, no AI register, and no binyan names
in the line that stands in the root's row, which is written for a reader who
has no Hebrew grammar.
"""
import json, pathlib, re, sys, unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import refs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
GLOSS = ROOT / "references" / "radak-gloss.json"
SHORASHIM = ROOT / "references" / "shorashim.json"

HEB = re.compile(r"[א-ת][א-ת֑-ׇ־ ]*[א-ת]")
MARKS = re.compile(r"[֑-ׇ]")
BASE = str.maketrans("ךםןףץ", "כמנפצ")
BINYAN = re.compile(r"\b(hif'?il|pi'?el|nif'?al|pu'?al|hitpa'?el|hishtaf'?el|binyan)\b", re.I)
# The house rule bars journey as a figure, not a day's journey, which is what
# מהלך יום plainly is.
AI = re.compile(r"\b(delve|leverage|underscore\w*|a testament to|it'?s worth noting|"
                r"navigat\w+|(?<!day's )(?<!days' )journey|tapestry|realm)\b", re.I)
# Authorities he may be said to bring, and how his Hebrew names them.
NAMED = {
    "Rabbi Yonah": ["רבי יונה"],
    "Ibn Ezra": ["אבן עזרא", "אברהם אבן עזרא"],
    "Targum Yonasan": ["תרגום יונתן", "תרגם יונתן"],
    "Targum": ["תרגום", "תרגם", "התרגום"],
    "Onkelos": ["אנקלוס"],
    "Rabbi Yaakov ben Elazar": ["רבי יעקב בן אלעזר", "רבי יעקב בן אילעזר"],
    "Rav Saadiah Gaon": ["רבי סעדיה", "סעדיה"],
    "the Mesorah": ["המסורת", "המסורה"],
    "Rav Yitzchak ibn Giat": ["אבן גיאת"],
    "Rashi": ["רבינו שלמה", "רש\"י"],
    "the Gaon": ["הגאון"],
    # Only where his father is the one saying something: a son's father in plain
    # English, as in a son's inheritance from his father, claims nothing.
    "his father (?:reads|takes|explains|holds|says|writes|sets|glosses|brings|puts)":
        ["אדוני אבי"],
    "Chachamim": ["רבותינו"],
    "Chazal": ["רבותינו", "משנה", "פרק"],
}


def flat(s):
    """Hebrew with its pointing, maqaf and final forms levelled, for comparing."""
    # The maqaf falls inside the range of marks, so it becomes a space first,
    # or על־הארץ would flatten to one word and match nothing.
    s = unicodedata.normalize("NFD", s).replace("־", " ")
    s = MARKS.sub("", s).replace("[", " ").replace("]", " ")
    return re.sub(r"\s+", " ", s).strip().translate(BASE)


def entry_text(parts):
    return flat(" ".join(re.sub(r"<[^>]+>", " ", p.get("html", "")) for p in parts))


def entry_refs(parts):
    return {r for p in parts for r in re.findall(r'data-r="([^"]+)"', p.get("html", ""))}


GEM = {"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
       "י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80, "צ": 90,
       "ק": 100, "ר": 200, "ש": 300, "ת": 400}
# The edition's own Hebrew book names, including the spellings Sefaria does not
# link (שפטים for שופטים), so a citation can be read whether or not it is a link.
BOOKS = {
    "בראשית": "Genesis", "שמות": "Exodus", "ויקרא": "Leviticus", "במדבר": "Numbers",
    "דברים": "Deuteronomy", "יהושע": "Joshua", "שופטים": "Judges", "שפטים": "Judges",
    "שמואל א": "I Samuel", "שמואל ב": "II Samuel", "מלכים א": "I Kings", "מלכים ב": "II Kings",
    "ישעיה": "Isaiah", "ירמיה": "Jeremiah", "יחזקאל": "Ezekiel", "הושע": "Hosea",
    "יואל": "Joel", "עמוס": "Amos", "עובדיה": "Obadiah", "עבדיה": "Obadiah",
    "יונה": "Jonah", "מיכה": "Micah", "נחום": "Nahum", "חבקוק": "Habakkuk",
    "צפניה": "Zephaniah", "חגי": "Haggai", "זכריה": "Zechariah", "מלאכי": "Malachi",
    "תהלים": "Psalms", "משלי": "Proverbs", "איוב": "Job", "שיר השירים": "Song of Songs",
    "רות": "Ruth", "איכה": "Lamentations", "קהלת": "Ecclesiastes", "אסתר": "Esther",
    "דניאל": "Daniel", "עזרא": "Ezra", "נחמיה": "Nehemiah",
    "דברי הימים א": "I Chronicles", "דברי הימים ב": "II Chronicles",
}
BOOK_RX = "|".join(sorted((re.escape(b) for b in BOOKS), key=len, reverse=True))
# A citation as the edition prints it: "(ישעיה נז, א)", or "(שם לב, כו)" for an ibid.
HEB_CITE = re.compile(r"\(\s*(%s)?[^()]{0,12}?([א-ת]{1,6})'?,\s*([א-ת]{1,6})'?\s*\)" % BOOK_RX)


def gematria(s):
    n = sum(GEM.get(c, 0) for c in s if c in GEM)
    return n if n else None


def numbered(text):
    """Every citation the edition prints in Hebrew, whether or not Sefaria
    linked it: he writes שם for ibid constantly, and prints some book names in
    spellings the linker misses. Returns the full keys where the book is named
    and the bare chapter and pasuk where it is not."""
    keys, pairs = set(), set()
    for m in HEB_CITE.finditer(text):
        c, v = gematria(m.group(2)), gematria(m.group(3))
        if not (c and v):
            continue
        pairs.add((c, v))
        if m.group(1):
            keys.add(f"{BOOKS[m.group(1)]}.{c}.{v}")
    return keys, pairs


def cited_keys(text):
    """Every Tanach citation the English makes, as pesukim.json keys."""
    out = set()
    for m in refs.TANACH_RX.finditer(text):
        book = refs.TANACH[m.group(1)]
        for piece in refs.PIECE.findall(m.group(0)):
            c, v = piece[0], piece[1]            # the third group is a range's end
            out.add(f"{book}.{int(c)}.{int(v)}")
    return out


def main():
    # --file lints a batch on its own, before it is merged, so whoever drafts it
    # can put their own work right first. The file is either {"glosses": {...}}
    # or the bare mapping of headword to gloss.
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flag = "--file" in sys.argv
    g = json.loads((pathlib.Path(args[0]) if flag else GLOSS).read_text(encoding="utf-8"))
    if "glosses" not in g:
        g = {"glosses": g}
    roots = json.loads(SHORASHIM.read_text(encoding="utf-8"))["roots"]
    byhw = {}
    for v in roots.values():
        for p in ([v] + v.get("more", [])) if v else []:
            byhw.setdefault(p["hw"], p)

    bad, checked = [], 0
    for hw, gl in g["glosses"].items():
        say = lambda m: bad.append(f"{hw}: {m}")
        part = byhw.get(hw)
        if not part:
            say("no entry of his answers to this headword")
            continue
        text, cites = entry_text([part]), entry_refs([part])
        raw = re.sub(r"<[^>]+>", " ", part.get("html", ""))
        printed, pairs = numbered(raw)
        cites |= printed
        books = {r.rsplit(".", 2)[0] for r in cites}
        if not isinstance(gl.get("sense"), str) or not gl["sense"].strip():
            say("no sense line")
            continue
        blocks = [("sense", gl["sense"])]
        for i, m in enumerate(gl.get("more") or []):
            if set(m) != {"h", "t"}:
                say(f"more[{i}] should hold just h and t")
                continue
            if len(m["h"]) > 40:
                say(f"heading over 40 characters: {m['h']!r}")
            blocks += [(f"more[{i}].h", m["h"]), (f"more[{i}].t", m["t"])]
        if BINYAN.search(gl["sense"]):
            say("the row's line names a binyan; say what the form does instead")
        for where, s in blocks:
            checked += 1
            if "—" in s or "–" in s:
                say(f"{where}: em or en dash")
            if AI.search(s):
                say(f"{where}: {AI.search(s).group(0)!r}")
            for phrase in HEB.findall(s):
                f = flat(phrase)
                if len(f.replace(" ", "")) > 2 and f not in text:
                    say(f"{where}: {phrase!r} is not in his entry")
            for key in cited_keys(s) - cites:
                book, c, v = key.rsplit(".", 2)
                # He may cite it as שם, which carries no link: take it if the
                # book is one this entry cites and the numbers are printed here.
                if not (book in books and (int(c), int(v)) in pairs):
                    say(f"{where}: he does not cite {key}")
            for name, hebrew in NAMED.items():
                # The entry's text is compared flattened, so the needles are too,
                # or אבן עזרא would never be found in אבנ עזרא.
                # A key may be a small pattern rather than a bare name.
                if re.search(rf"\b{name}\b", s, re.I) and not any(flat(h) in text for h in hebrew):
                    say(f"{where}: names {name}, whom his entry does not")
    for b in bad:
        print("  " + b)
    if flag:
        print(f"{len(g['glosses'])} glosses over {checked} blocks, {len(bad)} problems")
        return 1 if bad else 0
    done = sum(1 for v in roots.values() if v and any(
        p["hw"] in g["glosses"] for p in [v] + v.get("more", [])))
    have = sum(1 for v in roots.values() if v)
    print(f"{len(g['glosses'])} glosses over {checked} blocks, {len(bad)} problems; "
          f"{done} of {have} roots have English ({done / have:.0%})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
