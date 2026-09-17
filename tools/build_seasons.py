"""Build references/seasons.json: which entries go with each parsha and Yom Tov,
and what the home page shows in each week.
  python tools/build_seasons.py [--sample]

Two inputs. Rabbi Klein's book manuscript files every essay under a parsha or
a Yom Tov (sources/klein-book-manuscript/chapters.json with its essay map), so
the grouping is his, not ours; an entry joins a group through the essays it
cites. references/calendar.json (tools/fetch_calendar.py) says which parsha
and Yamim Tovim fall in each week. Only entry slugs and group names reach the
output; nothing from the manuscript's text does.

A week runs Sunday to Shabbos, and the page turns over on Sunday morning.
A Yom Tov leads the week when its eve falls by that Shabbos and it is still
running on the Monday; the week's parsha, if it has one, follows it, so Pesach starting on a Sunday belongs to the week
before it, and Simchas Torah on a Sunday does not take Bereishis's week.
Seasons (Elul, the Omer, the Three Weeks, the four parshiyos, Tu B'Shvat,
Shabbos Rosh Chodesh) never take the week; they add a few entries to it.
"""
import collections, datetime, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOK = ROOT / "sources" / "klein-book-manuscript"
OUT = ROOT / "references" / "seasons.json"
D = datetime.date


def norm(s):
    return re.sub(r"[^a-z]", "", s.lower())


# Parshiyos in order: our key and display form, the book's heading, Hebcal's name.
PARSHIYOS = [
    ("bereishis", "Bereishis", "Bereishis", "Bereshit"), ("noach", "Noach", "Noach", "Noach"),
    ("lech-lecha", "Lech Lecha", "Lech Lecha", "Lech-Lecha"), ("vayeira", "Vayeira", "Vayera", "Vayera"),
    ("chayei-sarah", "Chayei Sarah", "Chayei Sarah", "Chayei Sara"), ("toldos", "Toldos", "Toldos", "Toldot"),
    ("vayeitzei", "Vayeitzei", "Vayeitzei", "Vayetzei"), ("vayishlach", "Vayishlach", "Vayishlach", "Vayishlach"),
    ("vayeishev", "Vayeishev", "Vayeshev", "Vayeshev"), ("mikeitz", "Mikeitz", "Miketz", "Miketz"),
    ("vayigash", "Vayigash", "Vayigash", "Vayigash"), ("vayechi", "Vayechi", "Vayechi", "Vayechi"),
    ("shemos", "Shemos", "Shemos", "Shemot"), ("vaeira", "Va'eira", "Vaera", "Vaera"), ("bo", "Bo", "Bo", "Bo"),
    ("beshalach", "Beshalach", "Bishalach", "Beshalach"), ("yisro", "Yisro", "Yisro", "Yitro"),
    ("mishpatim", "Mishpatim", "Mishpatim", "Mishpatim"), ("terumah", "Terumah", "Terumah", "Terumah"),
    ("tetzaveh", "Tetzaveh", "Titzaveh", "Tetzaveh"), ("ki-sisa", "Ki Sisa", "Ki Sisa", "Ki Tisa"),
    ("vayakhel", "Vayakhel", "Vayakhel", "Vayakhel"), ("pekudei", "Pekudei", "Pekudai", "Pekudei"),
    ("vayikra", "Vayikra", "Vayikra", "Vayikra"), ("tzav", "Tzav", "Tzav", "Tzav"),
    ("shemini", "Shemini", "Shemini", "Shmini"), ("tazria", "Tazria", "Tazria", "Tazria"),
    ("metzora", "Metzora", "Metzora", "Metzora"), ("acharei-mos", "Acharei Mos", "Acharei Mos", "Achrei Mot"),
    ("kedoshim", "Kedoshim", "Kedoshim", "Kedoshim"), ("emor", "Emor", "Emor", "Emor"),
    ("behar", "Behar", "Behar", "Behar"), ("bechukosai", "Bechukosai", "Bechukosai", "Bechukotai"),
    ("bamidbar", "Bamidbar", "Bamidbar", "Bamidbar"), ("naso", "Naso", "Naso", "Nasso"),
    ("behaaloscha", "Behaaloscha", "Behaloscha", "Beha'alotcha"), ("shelach", "Shelach", "Shelach", "Sh'lach"),
    ("korach", "Korach", "Korach", "Korach"), ("chukas", "Chukas", "Chukas", "Chukat"),
    ("balak", "Balak", "Balak", "Balak"), ("pinchas", "Pinchas", "Pinchas", "Pinchas"),
    ("matos", "Matos", "Mattos", "Matot"), ("masei", "Masei", "Masei", "Masei"),
    ("devarim", "Devarim", "Devarim", "Devarim"), ("vaeschanan", "Va'eschanan", "Voeschanan", "Vaetchanan"),
    ("eikev", "Eikev", "Eikev", "Eikev"), ("reeh", "Re'eh", "Re'ay", "Re'eh"),
    ("shoftim", "Shoftim", "Shoftim", "Shoftim"), ("ki-seitzei", "Ki Seitzei", "Ki Saytzei", "Ki Teitzei"),
    ("ki-savo", "Ki Savo", "Ki Savo", "Ki Tavo"), ("nitzavim", "Nitzavim", "Nitzavim-Vayelech", "Nitzavim"),
    ("vayeilech", "Vayeilech", "Nitzavim-Vayelech", "Vayeilech"), ("haazinu", "Haazinu", "Haazinu", "Ha'azinu"),
    ("vezos-habrachah", "V'Zos HaBrachah", "V'Zos HaBrachah", None),
]

# Yamim Tovim and seasons: key, display, the book's heading.
OCCASIONS = [
    ("chanukah", "Chanukah", "Chanuka"), ("tu-bishvat", "Tu B'Shvat", "Tu B'Shvat"),
    ("four-parshiyos", "The four parshiyos", "4 Parshiyos"), ("purim", "Purim", "Purim"),
    ("pesach", "Pesach", "Pesach"), ("omer", "Sefiras HaOmer", "Sefiras HaOmer"),
    ("shavuos", "Shavuos", "Shavuos"), ("tisha-bav", "Tisha B'Av", "Tisha B'Av and Nachamu"),
    ("yamim-noraim", "Elul and the Yamim Noraim", "Elul/Rosh HaShanah/Yom Kippur"),
    ("sukkos", "Sukkos", "Sukkos/Simchas Torah"), ("rosh-chodesh", "Shabbos Rosh Chodesh", "Shabbos Rosh Chodesh"),
]
NAMES = {k: n for k, n, *_ in PARSHIYOS} | {k: n for k, n, _ in OCCASIONS}
# Rosh Hashanah and Yom Kippur share the book's Elul section but are named on their own.
NAMES |= {"rosh-hashanah": "Rosh Hashanah", "yom-kippur": "Yom Kippur", "nachamu": "Shabbos Nachamu"}


# Where the book's grouping is plainly too broad for one day: Rosh Hashanah and
# Yom Kippur share its Elul section, and its Sukkos section has two essays.
# "first" goes to the top in this order; "drop" leaves the group.
ADJUST = {
    "rosh-hashanah": {"first": ["horn-shofar-keren-yovel-chatzotzros", "king-melech-moshel", "judgment-din-rachamim"]},
    "yom-kippur": {"first": ["forgiveness-mechilah-selichah-kapparah", "advocate-meilitz-praklit-sanegor", "fasting-tzom-taanis"],
                   "drop": ["horn-shofar-keren-yovel-chatzotzros"]},
    "chanukah": {"first": ["oil-shemen-yitzhar", "vessel-pach-kankan-kad-chavis", "salvation-yeshuah-teshuah-hatzalah-purkan"]},
    "pesach": {"first": ["jumping-pesach-dilug-kefitzah"]},
    "sukkos": {"first": ["citron-hadar-etrog-tapuach", "joy-simchah-sasson-gilah", "drawing-water-dalah-shoev",
                         "rain-geshem-matar-yoreh-malkosh"]},
}


def book_groups():
    """Group key -> {essay id: 1 or 0.5}; 1 when the essay is the chapter's main one."""
    by_book = [(norm(b), k) for k, _, b, _ in PARSHIYOS] + [(norm(b), k) for k, _, b in OCCASIONS]
    chapters = json.loads((BOOK / "chapters.json").read_text(encoding="utf-8"))
    emap = {c["n"]: c["essays"] for c in json.loads((BOOK / "chapter-essay-map.json").read_text(encoding="utf-8"))}
    groups = collections.defaultdict(dict)
    for c in chapters:
        heading = c["parsha"] or c["section"]
        keys = [k for b, k in by_book if b == norm(heading)]
        if not keys:
            continue
        for k in keys:
            for i, essay in enumerate(emap.get(c["n"], [])):
                groups[k][essay] = max(groups[k].get(essay, 0), 1 if i == 0 else 0.5)
    groups["nachamu"] = dict(groups["tisha-bav"])
    for k in ("rosh-hashanah", "yom-kippur"):
        groups[k] = dict(groups["yamim-noraim"])
    return groups


def entry_essays():
    """Entry slug -> its essay ids in the order the entry lists them (reruns folded)."""
    pairs = json.loads((ROOT / "sources" / "whats-in-a-word" / "reruns.json").read_text(encoding="utf-8"))["pairs"]
    twin = {a: str(b) for a, b in pairs.items()} | {str(b): a for a, b in pairs.items()}
    out = {}
    for p in sorted((ROOT / "entries").glob("*.md")):
        fm = p.read_text(encoding="utf-8").split("\n---", 1)[0]
        ids = re.findall(r"^\s+- wiaw:(\d+) ", fm, re.M)
        out[p.stem] = [(i, twin.get(i)) for i in ids]
    return out


def ranked(groups, essays):
    """Group key -> entry slugs, best first. An entry scores by how much of it
    comes from the group's essays, with a lift when its first essay is one."""
    out = {}
    for k, g in groups.items():
        scores = []
        for slug, ids in essays.items():
            if not ids:
                continue
            hits = [max(g.get(a, 0), g.get(b, 0) if b else 0) for a, b in ids]
            if not any(hits):
                continue
            score = sum(hits) / len(ids) + (0.5 if hits[0] else 0)
            scores.append((-score, slug))
        out[k] = [s for _, s in sorted(scores)]
    for k, adj in ADJUST.items():
        first = [s for s in adj.get("first", []) if s in essays]
        out[k] = first + [s for s in out.get(k, []) if s not in first and s not in adj.get("drop", [])]
    return out


def weeks(calendar):
    items = calendar["items"]
    days = collections.defaultdict(list)
    for i in items:
        days[D.fromisoformat(i["date"])].append(i)
    title = lambda i: norm(i["title"])

    def span(prefix, skip=()):
        """(first day, last day) runs of a Yom Tov whose titles start with prefix."""
        ds = sorted({d for d, its in days.items() for i in its if title(i).startswith(prefix)
                     and not any(title(i).startswith(s) for s in skip) and i["category"] == "holiday"})
        runs, cur = [], []
        for d in ds:
            if cur and (d - cur[-1]).days > 2:
                runs.append((cur[0], cur[-1]))
                cur = []
            cur.append(d)
        if cur:
            runs.append((cur[0], cur[-1]))
        return runs

    wins = {"rosh-hashanah": span("roshhashana", ("roshhashanalabehemot",)), "yom-kippur": span("yomkippur"),
            "sukkos": span("sukkot"), "chanukah": span("chanukah"),
            "purim": span("purim", ("purimkatan",)), "pesach": span("pesach", ("pesachsheni",)), "shavuos": span("shavuot"),
            "tisha-bav": span("tishabav")}
    # Sukkos runs through Simchas Torah; Rosh Hashanah includes its second day.
    st = span("simchattorah")
    wins["sukkos"] = [(a, max([e for s, e in st if 0 <= (s - a).days < 12] or [b])) for a, b in wins["sukkos"]]
    wins["tisha-bav"] = [(a, a) for a, _ in wins["tisha-bav"]]

    def dated(prefix):
        return sorted(d for d, its in days.items() for i in its if title(i).startswith(prefix))

    def after(starts, ends, within):
        """Pair each start with the first end that follows it within `within` days."""
        return [(a, b) for a in starts for b in [next((e for e in ends if 0 < (e - a).days <= within), None)] if b]

    one = datetime.timedelta(days=1)
    seasons = {
        # Elul: from Rosh Chodesh Elul (its first day) to Yom Kippur.
        "yamim-noraim": after([d for d in dated("roshchodeshelul") if d - one not in dated("roshchodeshelul")],
                              [a for a, _ in wins["yom-kippur"]], 45),
        # The Omer: the day after Pesach to the day before Shavuos.
        "omer": [(a + one, b - one) for a, b in after([b for _, b in wins["pesach"]], [a for a, _ in wins["shavuos"]], 60)],
        # The Three Weeks: the Seventeenth of Tammuz to Tisha B'Av.
        "tisha-bav": [(a - datetime.timedelta(days=21), a) for a, _ in wins["tisha-bav"]],
    }
    first, last = min(days), max(days)
    sunday = first - datetime.timedelta(days=(first.weekday() + 1) % 7)
    out = []
    while sunday + datetime.timedelta(days=6) <= last:
        sat, mon = sunday + datetime.timedelta(days=6), sunday + datetime.timedelta(days=1)
        rng = [sunday + datetime.timedelta(days=n) for n in range(7)]
        lead = [k for k, runs in wins.items() for a, b in runs
                if a - datetime.timedelta(days=1) <= sat and b >= mon]
        lead.sort(key=lambda k: min(a for a, b in wins[k] if a - datetime.timedelta(days=1) <= sat and b >= mon))
        parsha = []
        for i in days.get(sat, []):
            if i["category"] == "parashat":
                names = i["title"].split(" ", 1)[1].split("-")
                # Hebcal hyphenates both double parshiyos and Lech-Lecha.
                if norm(i["title"]) == "parashatlechlecha":
                    names = ["Lech-Lecha"]
                parsha = [k for n in names for k, _, _, h in PARSHIYOS if h and norm(h) == norm(n)]
        mix = []
        in_range = lambda ds: any(sunday <= d <= sat for d in ds)
        overlaps = lambda windows: any(a <= sat and b >= sunday for a, b in windows)
        if overlaps(seasons["yamim-noraim"]):
            mix.append("yamim-noraim")
        if overlaps(seasons["omer"]):
            mix.append("omer")
        if overlaps(seasons["tisha-bav"]):
            mix.append("tisha-bav")
        elif in_range(dated("shabbatnachamu")):
            mix.append("nachamu")
        if in_range(dated("tubishvat")):
            mix.append("tu-bishvat")
        if any(in_range(dated(p)) for p in ("shabbatshekalim", "shabbatzachor", "shabbatparah", "shabbathachodesh")):
            mix.append("four-parshiyos")
        if any(i["category"] == "roshchodesh" for i in days.get(sat, [])):
            mix.append("rosh-chodesh")
        mix = [m for m in mix if m not in lead and not (m == "yamim-noraim" and {"rosh-hashanah", "yom-kippur"} & set(lead))
               and not (m == "omer" and {"pesach", "shavuos"} & set(lead))]
        out.append({"from": sunday.isoformat(), "lead": lead, "parsha": parsha, "mix": mix})
        sunday += datetime.timedelta(days=7)
    return out


# How a season reads after the week's name: "Parshas Re'eh · Elul".
SEASON_NAMES = {"yamim-noraim": "Elul", "omer": "Sefiras HaOmer", "tisha-bav": "The Three Weeks",
                "nachamu": "Shabbos Nachamu", "tu-bishvat": "Tu B'Shvat", "four-parshiyos": "The four parshiyos",
                "rosh-chodesh": "Shabbos Rosh Chodesh"}


def label(w):
    """"Parshas Chukas-Balak", "Yom Kippur and Sukkos", "Chanukah and Parshas Mikeitz",
    "Parshas Haazinu · Elul"."""
    parts = [NAMES[k] for k in w["lead"]]
    if w["parsha"]:
        parts.append("Parshas " + "-".join(NAMES[k] for k in w["parsha"]))
    return " · ".join([" and ".join(parts)] + [SEASON_NAMES[m] for m in w["mix"]])


def main():
    groups = book_groups()
    order = ranked(groups, entry_essays())
    cal = json.loads((ROOT / "references" / "calendar.json").read_text(encoding="utf-8"))
    ws = weeks(cal)
    for w in ws:
        w["label"] = label(w)
    OUT.write_text(json.dumps({"note": "Generated by tools/build_seasons.py; groups follow Rabbi Klein's book.",
                               "names": NAMES, "groups": order, "weeks": ws},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    thin = sorted((len(v), k) for k, v in order.items())
    print(f"{OUT.relative_to(ROOT)}: {len(order)} groups, {len(ws)} weeks; thinnest {thin[:5]}")
    missing = [k for k in NAMES if k not in order or not order[k]]
    if missing:
        print("groups with no entries:", missing)
    if "--sample" in sys.argv:
        for w in ws:
            print(w["from"], "|", w["label"], "|", "lead" if w["lead"] else "parsha", w["lead"] or w["parsha"], "| mix", w["mix"])


if __name__ == "__main__":
    main()
