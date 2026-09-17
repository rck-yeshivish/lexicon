"""Check references/radak-gloss.json against Radak's own entries.

  python tools/check_glosses.py [--verbose]

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
AI = re.compile(r"\b(delve|leverage|underscore\w*|a testament to|it'?s worth noting|"
                r"navigat\w+|journey|tapestry|realm)\b", re.I)
# Authorities he may be said to bring, and how his Hebrew names them.
NAMED = {
    "Rabbi Yonah": ["רבי יונה"],
    "Ibn Ezra": ["אבן עזרא", "אברהם אבן עזרא"],
    "Targum Yonasan": ["תרגום יונתן", "תרגם יונתן"],
    "Targum": ["תרגום", "תרגם", "התרגום"],
    "Onkelos": ["אנקלוס"],
    "Rabbi Yaakov ben Elazar": ["רבי יעקב בן אלעזר"],
    "Rav Yitzchak ibn Giat": ["יצחק אבן גיאת"],
    "his father": ["אדוני אבי"],
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
    verbose = "--verbose" in sys.argv
    g = json.loads(GLOSS.read_text(encoding="utf-8"))
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
                say(f"{where}: he does not cite {key}")
            for name, hebrew in NAMED.items():
                # The entry's text is compared flattened, so the needles are too,
                # or אבן עזרא would never be found in אבנ עזרא.
                if re.search(rf"\b{re.escape(name)}\b", s) and not any(flat(h) in text for h in hebrew):
                    say(f"{where}: names {name}, whom his entry does not")
    n = len(g["glosses"])
    done = sum(1 for v in roots.values() if v and any(
        p["hw"] in g["glosses"] for p in [v] + v.get("more", [])))
    have = sum(1 for v in roots.values() if v)
    for b in bad:
        print("  " + b)
    print(f"{n} glosses over {checked} blocks, {len(bad)} problems; "
          f"{done} of {have} roots have English ({done / have:.0%})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
