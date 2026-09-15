"""Find Tanach and Mishnah citations in entry text, and match a cluster's words
inside a pasuk. Shared by fetch_pesukim.py (which fetches the texts) and
build_site.py (which links the citations and draws the pesukim panel)."""
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

def _alt(names):
    return "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))

# A citation is a book followed by chapter:verse, a range (16-17), and any
# further "N:M" that follow it in the same run (", 45:14", "; 10:8", " and 19:20").
_NUM = r"(\d+):(\d+)(?:\s*[-–]\s*(\d+))?"
_CHAIN = r"(?:(?:,|;|,? and)\s+\d+:\d+(?:\s*[-–]\s*\d+)?)*"
TANACH_RX = re.compile(r"(?<![\w-])(%s)\s+%s%s" % (_alt(TANACH), _NUM, _CHAIN))
MISHNAH_RX = re.compile(r"(?<![\w-])(%s)\s+%s%s" % (_alt(MISHNAH), _NUM, _CHAIN))
# Mishnah-shaped citations that are not the Mishnah.
NOT_MISHNAH = re.compile(r"(Yerushalmi|Tosefta|Hilchos|Rambam|Mishneh Torah|Sifra|Sifrei)\s+$")
PIECE = re.compile(_NUM)
MAX_RANGE = 4


def keys_for(book, ch, v1, v2):
    v2 = v2 or v1
    if v2 < v1 or v2 - v1 >= MAX_RANGE:
        return [f"{book}.{ch}.{v1}"]
    return [f"{book}.{ch}.{v}" for v in range(v1, v2 + 1)]


def find(text):
    """[(start, end, sefaria_book, [(label, [keys])])] for each citation run.

    Offsets are into `text`; each run can hold several references to the same
    book ("Yeshayahu 43:3, 45:14")."""
    out = []
    for rx, table, mishnah in ((TANACH_RX, TANACH, False), (MISHNAH_RX, MISHNAH, True)):
        for m in rx.finditer(text):
            if mishnah:
                if NOT_MISHNAH.search(text[max(0, m.start() - 20):m.start()]):
                    continue
                book = "Mishnah " + table[m.group(1)] if table[m.group(1)] != "Pirkei Avot" else "Pirkei Avot"
            else:
                book = table[m.group(1)]
            refs, pos = [], m.start(1) + len(m.group(1))
            for p in PIECE.finditer(text, pos, m.end()):
                ch, v1 = int(p.group(1)), int(p.group(2))
                v2 = int(p.group(3)) if p.group(3) else None
                refs.append((p.start(), p.end(), keys_for(book, ch, v1, v2)))
            out.append((m.start(), m.end(), book, m.group(1), refs))
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
    return NIKUD.sub("", w).translate(FINALS)


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
