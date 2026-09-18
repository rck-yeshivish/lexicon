"""Check references/radak-gloss.json against Radak's own entries.

  python tools/check_glosses.py                     # the whole file
  python tools/check_glosses.py --file batch.json   # one batch, before merging
  python tools/check_glosses.py --thin              # his long entries, thinnest glosses first

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

Two more are about the English being English. A citation printed in Hebrew, as
the edition prints it, is refused: the reader this is written for cannot read
(ירמיה כב, יד), and a citation in Hebrew is invisible to the check above that
tests whether he cites it at all. And a block that is nearly all Hebrew is
refused, since a part whose point rests on a phrase left unrendered gives a
reader without Hebrew nothing.
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
                r"navigat\w+|(?<!day's )(?<!days' )journey|tapestry|realm|whence)\b", re.I)
# Authorities he may be said to bring, and how his Hebrew names them.
NAMED = {
    # Once the edition sets him רבי יוגה, a gimel for the nun.
    "Rabbi Yonah": ["רבי יונה", "רבי יוגה"],
    # The edition sets his name אבן עורא in places, with a vav for the zayin,
    # and four times drops the alef, רבי אברהם בן עזרא. That last needle has to
    # carry אברהם: רבי משה בן עזרא is a different man, and בן עזרא alone would
    # let Ibn Ezra be named in the one entry that is his brother's.
    "Ibn Ezra": ["אבן עזרא", "אבן עורא", "אברהם בן עזרא"],
    # He writes ויונתן תרגם 79 times, תרגם יונתן 77 and תרגום יונתן 36. Knowing
    # only the last two made drafters write "Yonasan renders" where they wanted
    # the fuller name, which is the check dictating the prose.
    # יונתן תרגם already carries יונתן תרגמו, which is why one entry passed by
    # luck; תרגמו יונתן, with the suffix before the name, does not follow from
    # any of the others, and neither does the one place he says Yonasan did not
    # render the word at all.
    "Targum Yonasan": ["תרגום יונתן", "תרגם יונתן", "יונתן תרגם", "יונתן תרגום",
                       "תרגמו יונתן", "יונתן לא תרגם", "יונתן פירש",
                       # and once with the verb first, ופירש יונתן
                       "פירש יונתן",
                       # Three times he gives not a rendering but a view: וכן דעת
                       # יונתן, and once that view is why Yonasan left a word
                       # untranslated.
                       "דעת יונתן"],
    "Targum": ["תרגום", "תרגם", "התרגום"],
    "Onkelos": ["אנקלוס"],
    # The edition prints his name twelve times as אלעזר, twice as אלעור with a
    # vav for the zayin, and once as אילעזר. The same slip it makes on Ibn Ezra.
    # The needles start at יעקב, since the edition writes the title out as רבי
    # in eleven places and abbreviates it to ר' in the twelfth.
    "Rabbi Yaakov ben Elazar": ["יעקב בן אלעזר", "יעקב בן אילעזר",
                                "יעקב בן אלעור"],
    "Rav Saadiah Gaon": ["רבי סעדיה", "סעדיה"],
    # Named once, at קלס, on saying ויתקלס in Kaddish. A drafter named him and
    # said plainly that nothing was checking it, which is how this got in.
    "Rav Amram(?: Gaon)?": ["רב עמרם"],
    # Bare, so the prefixed במסורת counts: he writes it three times, and with
    # the definite article on the needle a true sentence about what the Mesorah
    # does not carry was refused.
    "the Mesorah": ["מסורת", "מסורה"],
    # Rabbi Moshe Kimchi, whom he names as his brother: ורבי אחי רבי משה ז"ל
    # פירש. Policed like his father, and only where the brother is the one
    # saying something.
    "his brother (?:Rabbi Moshe )?(?:reads|takes|explains|holds|says|writes|glosses)|"
    "His brother Rabbi Moshe": ["אחי רבי משה"],
    # He is הרב אבן גיאת in one entry and הרב רבי יצחק גיאת in another, so the
    # needle is the surname and the key takes either English form.
    "(?:Rav|Rabbi) Yitzchak (?:ibn )?Giat|the Gaon Ibn Giat": ["גיאת"],
    # Nine times plene, once defective: וכתב רבנו שלמה ז"ל at שֹרד.
    "Rashi": ["רבינו שלמה", "רבנו שלמה", "רש\"י"],
    "the Gaon": ["הגאון"],
    # Only where his father is the one saying something: a son's father in plain
    # English, as in a son's inheritance from his father, claims nothing.
    "his father (?:reads|takes|explains|holds|says|writes|sets|glosses|brings|puts)":
        # Plene, defective, and once with a resh for the daled.
        ["אדוני אבי", "אדני אבי", "ארוני אבי"],
    # He names them רבותינו 318 times and רז"ל three, so both count.
    "Chachamim": ["רבותינו", "רז\"ל"],
    "Chazal": ["רבותינו", "רז\"ל", "משנה", "פרק"],
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
    # The edition sets Koheles once as קהלית, which Sefaria did not link.
    "קהלית": "Ecclesiastes",
    "דניאל": "Daniel", "עזרא": "Ezra", "נחמיה": "Nehemiah",
    "דברי הימים א": "I Chronicles", "דברי הימים ב": "II Chronicles",
}
BOOK_RX = "|".join(sorted((re.escape(b) for b in BOOKS), key=len, reverse=True))
# A citation as the edition prints it: "(ישעיה נז, א)", or "(שם לב, כו)" for an ibid.
# The book name must end where it ends: without this, the edition's misprint
# מלאכים for מלכים matches the prefix מלאכי and resolves to Malachi.
HEB_CITE = re.compile(r"\(\s*(?:(%s)(?![א-ת]))?[^()]{0,12}?([א-ת]{1,6})'?,\s*([א-ת]{1,6})'?\s*\)" % BOOK_RX)


# A citation printed the way the edition prints it, in Hebrew. Drafters have
# copied these straight out of his text; they belong in English on our side.
HEB_PRINTED = re.compile(r"\([^)]*[א-ת][^)]*,\s*[א-ת]{1,6}'?\s*\)")
ENG_CITE = re.compile(r"\([A-Z][A-Za-z ]+\s\d+:\d+\)")
ENG_WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")


# Five times he sets the book outside the citation and leaves only the volume
# letter inside it: בדברי הימים (א' יז, ו), בספר מלכים (א' י, יד). HEB_CITE wants
# the book within the brackets, so it read these as a bare chapter and pasuk with
# no book at all, and a true citation of his was refused.
VOL = {"א": "I", "ב": "II"}
OUTSIDE_BOOK = {"דברי הימים": "Chronicles", "שמואל": "Samuel", "מלכים": "Kings"}
OUTSIDE = re.compile(r"(דברי הימים|שמואל|מלכים)\s*\(\s*([אב])'?\s*"
                     r"([א-ת]{1,6})'?\s*,\s*([א-ת]{1,6})'?\s*\)")


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
    for m in OUTSIDE.finditer(text):
        c, v = gematria(m.group(3)), gematria(m.group(4))
        if c and v:
            pairs.add((c, v))
            keys.add(f"{VOL[m.group(2)]} {OUTSIDE_BOOK[m.group(1)]}.{c}.{v}")
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


def thin(g, roots, n=20):
    """His longest entries set against the English written for them. It cannot
    say a gloss is wrong, only that a great deal of his entry has gone
    unreported, which is a different fault from invention and the checks above
    cannot see it: שׁבע ran 3,654 characters on seven, the week, seven for a
    large number and swearing an oath, and carried a gloss of 23 characters that
    mentioned only the first."""
    size = {}
    for v in roots.values():
        for p in ([v] + (v.get("more") or [])) if v else []:
            size[p["hw"]] = len(p.get("text", ""))
    rows = []
    for hw, gl in g.items():
        his = size.get(hw, 0)
        if his < 1500:
            continue
        ours = len(gl.get("sense", "")) + sum(len(m["h"]) + len(m["t"])
                                              for m in (gl.get("more") or []))
        rows.append((ours / his, ours, his, hw, len(gl.get("more") or [])))
    rows.sort()
    print(f"{len(rows)} entries of his run past 1,500 characters. Thinnest first:\n")
    for ratio, ours, his, hw, parts in rows[:n]:
        print(f"  {ratio:.2f}  {hw:8} his {his:5} characters, ours {ours:4} in {parts} parts")


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
    if "--thin" in sys.argv:
        thin(g["glosses"], roots)
        return 0
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
        # The sense line stands in a table row beside 1,126 others. Past about
        # this length it stops being a line and becomes the paragraph the row
        # was meant to spare the reader.
        if len(gl["sense"]) > 170:
            say(f"the row's line runs {len(gl['sense'])} characters; keep it under 170")
        if BINYAN.search(gl["sense"]):
            say("the row's line names a binyan; say what the form does instead")
        for where, s in blocks:
            checked += 1
            if "—" in s or "–" in s:
                say(f"{where}: em or en dash")
            if AI.search(s):
                say(f"{where}: {AI.search(s).group(0)!r}")
            m = HEB_PRINTED.search(s)
            if m:
                say(f"{where}: {m.group(0)!r} cites in Hebrew; name the book in English")
            # A part that is nearly all Hebrew leaves the reader it was written
            # for with nothing. Citations are not prose, so they do not count
            # toward the English. The floor is set below the thinnest part that
            # earns its place, one whose point is grammatical and whose quoted
            # pesukim are the evidence for it rather than the thing being said.
            if not where.endswith(".h"):
                body = ENG_CITE.sub(" ", s)
                heb = sum(len(h.replace(" ", "")) for h in HEB.findall(body))
                eng = len(ENG_WORD.findall(body))
                if heb > 40 and eng / heb < 0.10:
                    say(f"{where}: {eng} words of English to {heb} letters of Hebrew; "
                        f"give the phrases their English")
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
                    # Some keys are small patterns. Print the plainest form of
                    # one rather than its regex, which told a drafter nothing,
                    # and name the Hebrew looked for, which is what settles it.
                    shown = re.sub(r"\(\?:|\)|\?|\\b", "", name).split("|")[0].strip()
                    say(f"{where}: names {shown or name}, whom his entry does not"
                        f" (looked for {', '.join(hebrew)})")
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
