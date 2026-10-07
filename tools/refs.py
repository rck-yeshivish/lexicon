"""Find Tanach and Mishnah citations in entry text, and match a cluster's words
inside a pasuk. Shared by fetch_pesukim.py (which fetches the texts) and
build_site.py (which links the citations and draws the pesukim panel)."""
import html
import json
import pathlib
import re

TANACH = {
    "Bereishis": "Genesis", "Shemos": "Exodus", "Vayikra": "Leviticus",
    "Bamidbar": "Numbers", "Devarim": "Deuteronomy", "Yehoshua": "Joshua",
    "Shoftim": "Judges", "Shmuel I": "I Samuel", "I Shmuel": "I Samuel",
    "Shmuel II": "II Samuel", "II Shmuel": "II Samuel",
    "Melachim I": "I Kings", "I Melachim": "I Kings",
    "Melachim II": "II Kings", "II Melachim": "II Kings",
    "Yeshayahu": "Isaiah", "Yirmiyahu": "Jeremiah", "Yechezkel": "Ezekiel",
    "Hoshea": "Hosea", "Yoel": "Joel", "Amos": "Amos", "Ovadiah": "Obadiah",
    "Yonah": "Jonah", "Michah": "Micah", "Nachum": "Nahum",
    "Chavakuk": "Habakkuk", "Tzefaniah": "Zephaniah", "Chaggai": "Haggai",
    "Zechariah": "Zechariah", "Zecharyah": "Zechariah", "Malachi": "Malachi",
    "Tehillim": "Psalms", "Mishlei": "Proverbs", "Iyov": "Job",
    "Shir HaShirim": "Song of Songs", "Rus": "Ruth", "Eichah": "Lamentations",
    "Koheles": "Ecclesiastes", "Esther": "Esther", "Daniel": "Daniel",
    "Ezra": "Ezra", "Nechemiah": "Nehemiah", "Nechemyah": "Nehemiah",
    "Divrei HaYamim I": "I Chronicles", "I Divrei HaYamim": "I Chronicles",
    "Divrei HaYamim II": "II Chronicles", "II Divrei HaYamim": "II Chronicles",
}

MISHNAH = {
    "Berachos": "Berakhot", "Peah": "Peah", "Demai": "Demai", "Kilayim": "Kilayim",
    "Sheviis": "Sheviit", "Terumos": "Terumot", "Maasros": "Maasrot",
    "Maaser Sheni": "Maaser Sheni", "Challah": "Challah", "Orlah": "Orlah",
    "Bikkurim": "Bikkurim", "Shabbos": "Shabbat", "Eruvin": "Eruvin",
    "Pesachim": "Pesachim", "Shekalim": "Shekalim", "Yoma": "Yoma",
    "Sukkah": "Sukkah", "Beitzah": "Beitzah", "Rosh Hashanah": "Rosh Hashanah",
    "Taanis": "Taanit", "Megillah": "Megillah", "Moed Katan": "Moed Katan",
    "Chagigah": "Chagigah", "Yevamos": "Yevamot", "Kesubos": "Ketubot",
    "Kesuvos": "Ketubot", "Nedarim": "Nedarim", "Nazir": "Nazir", "Sotah": "Sotah",
    "Gittin": "Gittin", "Kiddushin": "Kiddushin", "Bava Kamma": "Bava Kamma",
    "Bava Kama": "Bava Kamma", "Bava Metzia": "Bava Metzia",
    "Bava Basra": "Bava Batra", "Sanhedrin": "Sanhedrin", "Makkos": "Makkot",
    "Shevuos": "Shevuot", "Eduyos": "Eduyot", "Avodah Zarah": "Avodah Zarah",
    "Avos": "Pirkei Avot", "Horayos": "Horayot", "Zevachim": "Zevachim",
    "Menachos": "Menachot", "Chullin": "Chullin", "Bechoros": "Bekhorot",
    "Arachin": "Arakhin", "Temurah": "Temurah", "Kerisos": "Keritot",
    "Kerisus": "Keritot", "Meilah": "Meilah", "Tamid": "Tamid", "Middos": "Middot",
    "Kinnim": "Kinnim", "Keilim": "Kelim", "Ohalos": "Oholot", "Negaim": "Negaim",
    "Parah": "Parah", "Taharos": "Tahorot", "Mikvaos": "Mikvaot", "Niddah": "Niddah",
    "Machshirin": "Makhshirin", "Zavim": "Zavim", "Tevul Yom": "Tevul Yom",
    "Yadayim": "Yadayim", "Uktzin": "Oktzin",
}

# Tractates of the Bavli; the same spellings name the Yerushalmi's.
BAVLI = {k: v for k, v in MISHNAH.items() if v not in (
    "Peah", "Demai", "Kilayim", "Sheviit", "Terumot", "Maasrot", "Maaser Sheni", "Challah",
    "Orlah", "Bikkurim", "Shekalim", "Eduyot", "Pirkei Avot", "Middot", "Kinnim", "Kelim",
    "Oholot", "Negaim", "Parah", "Tahorot", "Mikvaot", "Makhshirin", "Zavim", "Tevul Yom",
    "Yadayim", "Oktzin")}
YERUSHALMI = {k: v for k, v in MISHNAH.items() if v not in (
    "Pirkei Avot", "Eduyot", "Zevachim", "Menachot", "Chullin", "Bekhorot", "Arakhin", "Temurah",
    "Keritot", "Meilah", "Tamid", "Middot", "Kinnim", "Kelim", "Oholot", "Negaim", "Parah",
    "Tahorot", "Mikvaot", "Makhshirin", "Zavim", "Tevul Yom", "Yadayim", "Oktzin")}


# Commentaries on the Bavli that Sefaria carries, by the name the entries use.
# When the entry names one just before a daf ("Tosafos to Bava Basra 74a"), the
# words it is about are in that commentary, not in the Gemara's own text.
COMMENTARIES = {"Tosafos": "Tosafot", "Tosafot": "Tosafot", "Rashi": "Rashi",
                "Rashbam": "Rashbam", "Ran": "Ran", "Ritva": "Ritva",
                "Rabbeinu Chananel": "Rabbeinu Chananel"}
COMMENTARY_NAME = {"Tosafot": "Tosafos", "Rashi": "Rashi", "Rashbam": "Rashbam", "Ran": "Ran",
                   "Ritva": "Ritva", "Rabbeinu Chananel": "Rabbeinu Chananel"}
# Tried on any daf whose Gemara text lacks the entry's word.
DEFAULT_COMMENTARIES = ("Rashi", "Tosafot")

# Commentaries on Tanach that Sefaria carries, by the names the entries use,
# each to the one name it goes by here ("Rashi to Bereishis 13:3" is keyed
# "Rashi on Genesis.13.3"). Eim LaMikra, Keses HaSofer and the like are not on
# Sefaria, and a citation of them keeps the pasuk.
TANACH_COMMENTARIES = {
    "Rashi": "Rashi", "Ibn Ezra": "Ibn Ezra", "Ramban": "Ramban", "Radak": "Radak",
    "Rashbam": "Rashbam", "Sforno": "Sforno", "Seforno": "Sforno", "Malbim": "Malbim",
    "Ralbag": "Ralbag", "Shadal": "Shadal", "Abarbanel": "Abarbanel", "Chizkuni": "Chizkuni",
    "Metzudas David": "Metzudas David", "Metzudas Tzion": "Metzudas Tzion",
    "Ohr HaChaim": "Ohr HaChaim", "Or HaChaim": "Ohr HaChaim", "Kli Yakar": "Kli Yakar",
    "Baal HaTurim": "Baal HaTurim", "Gur Aryeh": "Gur Aryeh", "Rabbeinu Bachya": "Rabbeinu Bachya",
    "Haamek Davar": "Haamek Davar", "HaKsav VeHaKabbalah": "HaKsav VeHaKabbalah",
    "Toras Moshe": "Toras Moshe", "Tzror HaMor": "Tzror HaMor", "Bechor Shor": "Bechor Shor",
    "Rabbi Yosef Bechor Shor": "Bechor Shor", "Rav Hirsch": "Rav Hirsch",
    "Onkelos": "Onkelos", "Targum Onkelos": "Onkelos", "Targum Yonasan": "Targum Yonasan",
    "Targum": "Targum", "Targum Sheini": "Targum Sheini",
}
TORAH = {"Genesis": "Bereshit", "Exodus": "Shemot", "Leviticus": "Vayikra", "Numbers": "Bamidbar",
         "Deuteronomy": "Devarim"}
NEVIIM = {"Joshua", "Judges", "I Samuel", "II Samuel", "I Kings", "II Kings", "Isaiah", "Jeremiah",
          "Ezekiel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
          "Zephaniah", "Haggai", "Zechariah", "Malachi"}
# How Sefaria titles each on a book, where it differs from "Rashi on Genesis".
_TITLE = {
    "Metzudas David": lambda b: f"Metzudat David on {b}",
    "Metzudas Tzion": lambda b: f"Metzudat Zion on {b}",
    "Ohr HaChaim": lambda b: f"Or HaChaim on {b}",
    "Baal HaTurim": lambda b: f"Ba'al HaTurim on {b}",
    "Chizkuni": lambda b: f"Chizkuni, {b}",
    "Bechor Shor": lambda b: f"Bekhor Shor, {b}",
    "HaKsav VeHaKabbalah": lambda b: f"HaKtav VeHaKabalah, {b}",
    "Toras Moshe": lambda b: f"Torat Moshe, {b}",
    "Abarbanel": lambda b: f"Abarbanel on Torah, {b}" if b in TORAH else f"Abarbanel on {b}",
    "Tzror HaMor": lambda b: f"Tzror HaMor on Torah, {b}",
    "Rabbeinu Bachya": lambda b: f"Rabbeinu Bahya, {TORAH.get(b, b)}",
    "Gur Aryeh": lambda b: f"Gur Aryeh on {TORAH.get(b, b).replace('Bereshit', 'Bereishit')}",
    # His commentary on the Torah only, and the part of it on the words.
    "Ralbag": lambda b: f"Ralbag Beur HaMilot on Torah, {b}" if b in TORAH else f"Ralbag on {b}",
    # On the Torah only; his Tehillim is not on Sefaria.
    "Rav Hirsch": lambda b: f"Rav Hirsch on Torah, {b}" if b in TORAH else None,
    "Onkelos": lambda b: f"Onkelos {b}",
    "Targum Yonasan": lambda b: f"Targum Jonathan on {b}",
    # "The Targum" is Onkelos on the Torah, Yonasan on Nevi'im, and on Kesuvim
    # the Targum printed with it.
    "Targum": lambda b: (f"Onkelos {b}" if b in TORAH else f"Targum Jonathan on {b}" if b in NEVIIM
                         else f"Aramaic Targum to {b}"),
    "Targum Sheini": lambda b: f"Targum Sheni on {b}",
}
COMMENTARY_NAME.update({c: c for c in TANACH_COMMENTARIES.values()})
# A Targum is the pasuk in Aramaic, one verse long, and its rendering is what
# it is cited for, though the Hebrew word itself is seldom in it.
TARGUMIM = {"Onkelos", "Targum Yonasan", "Targum", "Targum Sheini"}


def sefaria(key):
    """The Sefaria ref for a key. A commentary on a pasuk is keyed the same way
    whoever wrote it ("Chizkuni on Leviticus.3.3"); Sefaria titles each its own
    way ("Chizkuni, Leviticus.3.3"). Every other key is already its ref."""
    if " on " not in key:
        return key
    name, ref = key.split(" on ", 1)
    m = re.fullmatch(r"(.+?)((?:\.\d+){1,2})", ref)
    title = _TITLE[name](m.group(1)) if m and name in _TITLE else None
    return title + m.group(2) if title else key


def _alt(names):
    return "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))


def _subject_rx(names):
    # A commentator's name as the entries write it, plain, italic or bold.
    # Tosafos HaRosh, Tosafos Yeshanim and Tosafos Rid are other works than
    # Tosafos.
    one = r"\*{0,2}(?:%s)\b(?!\*{0,2}\s+(?:HaRosh|Yeshanim|Rid|Ri)\b)\*{0,2}" % _alt(names)
    many = r"%s(?:(?:,\s*|,?\s+and\s+)(?:the\s+)?%s)*" % (one, one)
    # "Rashi to", "Rashi (to", "Rashi (", "Rashi and Rabbeinu Chananel to", and
    # "(Rashi, " only in parentheses: "with Rashi, Yechezkel 16:29" is a list.
    return (many, re.compile(r"(?:(?<![\w*])(%s)\s*(?:\(\s*(?:to\s+)?|(?:to|on)\s+)|(?<=\()(%s),\s*)$"
                             % (many, many)),
            re.compile(r"\b(%s)\b" % _alt(names)))


_COMMS, SUBJECT_RX, COMM_NAME = _subject_rx(COMMENTARIES)
_, TANACH_SUBJECT_RX, TANACH_COMM_NAME = _subject_rx(TANACH_COMMENTARIES)
# "with Rashi", "with Rashi and Tosafos", "and Rashi there", "(Rashi)".
WITH_RX = re.compile(r"\s*,?\s*(?:(?:with|and)\s+(?:the\s+)?(%s)|\((%s)\))" % (_COMMS, _COMMS))
# One citation earlier in the same list, with what joins it to the next.
_REF = r"(?:(?:%s)\s+)?\d+(?::\d+)?[ab]?(?:\s*[-–]\s*\d+(?::\d+)?[ab]?)?" % _alt(set(TANACH) | set(MISHNAH))
LIST_STEP = re.compile(r"(?<![\w:])%s\s*(?:,\s*and(?:\s+to)?|,|\s+and(?:\s+to)?)\s+$" % _REF)

# The citations the pattern above cannot place, each read in its entry and
# judged (tools/cite_commentators.py lists the ones not yet judged). The
# entries say it too many ways for a pattern: "Rashi renders bitzah as maresc
# (to Yechezkel 47:11)" is Rashi's comment, while "Tosafos point out that face
# appears with hishtachavaah as well (Yeshayahu 49:23)" is the pasuk's. Each
# row is an entry, the words just before a list of citations, and whose
# comment the list is, or no one's.
CITED_BY = pathlib.Path(__file__).resolve().parent.parent / "references" / "cite-commentators.json"
_BY = {}
if CITED_BY.exists():
    for _r in json.loads(CITED_BY.read_text(encoding="utf-8"))["cites"]:
        _BY.setdefault(_r["entry"], []).append(_r)


def plain(s):
    """Text as a reader sees it, the same from an entry's markdown and from the
    page built from it: no tags, no emphasis, a link's words only."""
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return re.sub(r"\s+", " ", s.replace("*", ""))


def list_head(before):
    """The text before the first citation of the list this one ends, as a
    reader sees it: "Rashi to Bamidbar 22:5, *Berachos* 46b, " gives "Rashi to "."""
    pre = plain(before[-600:])
    while True:
        m = LIST_STEP.search(pre)
        if not m:
            return pre
        pre = pre[:m.start()]


def judged(entry, head):
    """The row of CITED_BY for the list whose list_head() this is, if judged.
    Where one row's words end another's, the longer is the one meant."""
    return max((r for r in _BY.get(entry, []) if r["before"] and head.endswith(r["before"])),
               key=lambda r: len(r["before"]), default=None)


def subject(before, tanach=False, entry=None):
    """The commentators a citation belongs to, from the text before it: "Rashi
    to Beitzah 4a", "Ibn Ezra to Shemos 23:27", and every citation further along
    such a list ("Rashi to Bamidbar 22:5, Berachos 46b, Beitzah 29b"). A list
    ends at a semicolon or a full stop, so in "Rashi to Yoma 75a; Gittin 70a"
    Gittin is the Gemara's. Where Rashi only follows the Gemara ("Rashi, from
    Bechoros 41a"; "Rashi (following Gittin 88a)") the daf is not his. A list
    judged in CITED_BY is as judged."""
    names, rx, name = ((TANACH_COMMENTARIES, TANACH_SUBJECT_RX, TANACH_COMM_NAME) if tanach
                       else (COMMENTARIES, SUBJECT_RX, COMM_NAME))
    head = list_head(before)
    row = judged(entry, head) if entry else None
    if row is not None:
        return list(dict.fromkeys(names[c] for c in row["by"] if c in names))
    m = rx.search(head)
    return list(dict.fromkeys(names[c] for c in name.findall(m.group(1) or m.group(2)))) if m else []

# A citation is a book followed by chapter:verse, a range (16-17), and any
# further "N:M" that follow it in the same run (", 45:14", "; 10:8", " and 19:20").
_NUM = r"(\d+):(\d+)(?:\s*[-–]\s*(\d+))?"
_CHAIN = r"(?:(?:,|;|,? and)\s+\d+:\d+(?:\s*[-–]\s*\d+)?)*"
TANACH_RX = re.compile(r"(?<![\w-])(%s)\s+%s%s" % (_alt(TANACH), _NUM, _CHAIN))
MISHNAH_RX = re.compile(r"(?<![\w-])(%s)\s+%s%s" % (_alt(MISHNAH), _NUM, _CHAIN))
YERUSHALMI_RX = re.compile(r"(?<![\w-])Yerushalmi\s+(%s)\s+(\d+):(\d+)(?:,\s+\d+:\d+)*" % _alt(YERUSHALMI))
# Bavli: tractate and daf, with more dapim of the same tractate after it (74a, 150b).
BAVLI_RX = re.compile(r"(?<![\w-])(%s)\s+(\d+)([ab])\b(?:,\s+\d+[ab]\b)*" % _alt(BAVLI))
# Citations shaped like the Mishnah or the Bavli that are something else.
NOT_MISHNAH = re.compile(r"(Yerushalmi|Tosefta|Hilchos|Rambam|Mishneh Torah|Sifra|Sifrei)\s+$")
NOT_BAVLI = re.compile(r"(Yerushalmi|Tosefta|Hilchos|Rambam|Mishneh Torah)\s+$")
PIECE = re.compile(_NUM)
DAF = re.compile(r"(\d+)([ab])\b")
HALACHAH = re.compile(r"(\d+):(\d+)")
MAX_RANGE = 4


def keys_for(book, ch, v1, v2):
    v2 = v2 or v1
    if v2 < v1 or v2 - v1 >= MAX_RANGE:
        return [f"{book}.{ch}.{v1}"]
    return [f"{book}.{ch}.{v}" for v in range(v1, v2 + 1)]


def find(text, lead="", entry=None):
    """[(start, end, kind, sefaria_book, name, [(piece_start, piece_end, [keys])])]
    for each citation run, in text order. kind is tanach, mishnah, bavli or
    yerushalmi. A run can hold several references to one book ("Yeshayahu
    43:3, 45:14", "Bava Basra 74a, 150b").

    A Bavli piece's keys are the daf and the commentaries on it worth trying,
    the daf first. Where the citation is a commentator's ("Rashi to Beitzah
    4a", "Ibn Ezra to Shemos 23:27"), his comment on the daf or the pasuk comes
    first instead, followed only by the daf or the pasuk. A key holding " on "
    is a commentary's.
    lead is the text just before this text where it was cut from a longer one
    (a run of a page between two tags), so that a commentator named there is
    seen. entry is the entry's file name, for the lists judged in CITED_BY."""
    out = []
    before = lambda m: text[max(0, m.start() - 20):m.start()]
    for m in TANACH_RX.finditer(text):
        book = TANACH[m.group(1)]
        # "Rashi to Bereishis 13:3": his comment on the pasuk first, then the pasuk.
        subj = subject(lead + text[:m.start()], tanach=True, entry=entry)
        pieces = []
        for p in PIECE.finditer(text, m.start(1) + len(m.group(1)), m.end()):
            keys = keys_for(book, int(p.group(1)), int(p.group(2)), int(p.group(3)) if p.group(3) else None)
            pieces.append((p.start(), p.end(), [f"{c} on {k}" for c in subj for k in keys] + keys))
        out.append((m.start(), m.end(), "tanach", book, m.group(1), pieces))
    for m in MISHNAH_RX.finditer(text):
        if NOT_MISHNAH.search(before(m)):
            continue
        name = MISHNAH[m.group(1)]
        book = name if name == "Pirkei Avot" else "Mishnah " + name
        pieces = [(p.start(), p.end(), keys_for(book, int(p.group(1)), int(p.group(2)),
                                                int(p.group(3)) if p.group(3) else None))
                  for p in PIECE.finditer(text, m.start(1) + len(m.group(1)), m.end())]
        out.append((m.start(), m.end(), "mishnah", book, m.group(1), pieces))
    for m in YERUSHALMI_RX.finditer(text):
        book = "Jerusalem Talmud " + YERUSHALMI[m.group(1)]
        pieces = [(p.start(), p.end(), [f"{book}.{p.group(1)}.{p.group(2)}"])
                  for p in HALACHAH.finditer(text, m.start(1) + len(m.group(1)), m.end())]
        out.append((m.start(), m.end(), "yerushalmi", book, "Yerushalmi " + m.group(1), pieces))
    comm_rx = re.compile(r"\b(%s)\b" % _alt(COMMENTARIES))
    for m in BAVLI_RX.finditer(text):
        if NOT_BAVLI.search(before(m)):
            continue
        book = BAVLI[m.group(1)]
        subj = subject(lead + text[:m.start()], entry=entry)
        # Otherwise a commentator the citation is "with", then one named in the
        # words just before it, then Rashi and Tosafos.
        w = WITH_RX.match(text, m.end())
        withc = [COMMENTARIES[c] for c in COMM_NAME.findall(w.group(1) or w.group(2))] if w else []
        named = comm_rx.findall(text[max(0, m.start() - 90):m.start()])
        comms = list(dict.fromkeys(withc + ([COMMENTARIES[named[-1]]] if named else []) + list(DEFAULT_COMMENTARIES)))
        pieces = []
        for p in DAF.finditer(text, m.start(1) + len(m.group(1)), m.end()):
            daf = f"{book}.{p.group(1)}{p.group(2)}"
            keys = ([f"{c} on {daf}" for c in subj] + [daf] if subj
                    else [daf] + [f"{c} on {daf}" for c in comms])
            pieces.append((p.start(), p.end(), keys))
        out.append((m.start(), m.end(), "bavli", book, m.group(1), pieces))
    out.sort()
    # Drop a run nested inside another (a tractate name inside a longer match).
    kept, last = [], -1
    for r in out:
        if r[0] >= last:
            kept.append(r)
            last = r[1]
    return kept


# ------------------------------------------------------------------ matching

NIKUD = re.compile("[֑-ׇ]")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")
WEAK = set("אהוי")
PREFIX = set("ובכלמשהאיתנ")
SUFFIX = set("והתימנכ")


def bare(w):
    return NIKUD.sub("", w).translate(FINALS).strip()


def root_letters(root):
    return [c for c in bare(root) if "א" <= c <= "ת"]


def matches_root(word, letters):
    """Does a pasuk word carry this root? Strong letters in order, with only
    weak letters between them, a short prefix and a suffix of inflection
    letters. A heuristic for highlighting, not a parser."""
    w = bare(word)
    # A root with fewer than two strong letters (ש-א-ה) would match nearly any
    # word holding that one letter, so it is not used for matching at all.
    strong = [c for c in letters if c not in WEAK]
    if len(strong) < 2:
        return False
    for start in range(0, min(4, len(w))):
        if w[start] != strong[0] or any(c not in PREFIX for c in w[:start]):
            continue
        i, ok = start, True
        for s in strong[1:]:
            j = i + 1
            while j < len(w) and w[j] != s:
                if w[j] not in WEAK or j - i > 2:
                    ok = False
                    break
                j += 1
            if not ok or j >= len(w):
                ok = False
                break
            i = j
        if ok:
            tail = w[i + 1:]
            if len(tail) <= 3 and all(c in SUFFIX for c in tail):
                return True
    return False
