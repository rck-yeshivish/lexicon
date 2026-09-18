"""Build the static site from the entries.

  python tools/build_site.py            -> site/
  python tools/build_site.py --out dist

Output is a plain static folder: drop it on Cloudflare Pages, no server and no
database. Everything the pages need is in one data.json, loaded once and cached.

The harvested corpus under sources/ is NEVER copied into the site. It is Rabbi
Klein's and Ohr Somayach's copyright; the site carries only our own entries,
each linking back to the original article.

There is a small markdown renderer here rather than a dependency, because the
entries use a known, narrow subset (headings, tables, lists, bold, italic,
links, code) and a build that needs no install is one less thing to break.
"""
import re, sys, json, html, shutil, pathlib, unicodedata, datetime, hashlib, urllib.parse
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import refs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "entries"
OUT = ROOT / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "site")

NIKUD = re.compile("[֑-ׇ]")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")
ALEFBET = list("אבגדהוזחטיכלמנסעפצקרשת")


def show_heb(s):
    """What a reader sees: nikud removed, spelling otherwise untouched."""
    return NIKUD.sub("", unicodedata.normalize("NFC", s)).strip()


def strip_heb(s):
    """The lookup key: no nikud and final letters folded, for matching only.

    Never render this. Folding turns אבדון into אבדונ, which is a misspelling;
    it exists so that a word typed with its final form still matches.
    """
    return show_heb(s).translate(FINALS)


def norm_latin(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9]+", "", s)


# ---------------------------------------------------------------- entry parsing

def front_matter(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    fm, key = {}, None
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if re.match(r"^\s+-\s", line) and key and key != "words":
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(line.strip()[2:].strip())
            continue
        mm = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if mm:
            key, val = mm.group(1), mm.group(2).split("  #")[0].strip()
            if val.startswith("[") and val.endswith("]"):
                fm[key] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
            elif val == "":
                fm[key] = []
            else:
                fm[key] = unquote(val)
    return fm


def unquote(v):
    """A YAML scalar written wholly in quotes loses them, as a YAML reader would
    drop them; quotes that are part of the text ("Canaanite" used for...) stay."""
    m = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', v)
    if m:
        return re.sub(r'\\(.)', r'\1', m.group(1))
    m = re.fullmatch(r"'((?:[^']|'')*)'", v)
    if m:
        return m.group(1).replace("''", "'")
    return v


def word_block(text):
    m = re.search(r"^words:\s*\n((?:\s+(?:-\s+)?\w+:.*\n?)+)", text, re.M)
    if not m:
        return []
    items, cur = [], None
    for line in m.group(1).splitlines():
        mm = re.match(r"^\s+-\s+(\w+):\s*(.*)$", line)
        if mm:
            if cur:
                items.append(cur)
            cur = {mm.group(1): unquote(mm.group(2).strip())}
            continue
        mm = re.match(r"^\s+(\w+):\s*(.*)$", line)
        if mm and cur is not None:
            cur[mm.group(1)] = unquote(mm.group(2).strip())
    if cur:
        items.append(cur)
    return [i for i in items if i.get("he")]


def sections(body):
    """Split the body into (heading, markdown) pairs, in order."""
    out, cur, buf = [], None, []
    for line in body.split("\n"):
        m = re.match(r"^## (.+)$", line)
        if m:
            if cur:
                out.append((cur, "\n".join(buf).strip()))
            cur, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if cur:
        out.append((cur, "\n".join(buf).strip()))
    return out


# ------------------------------------------------------------ markdown renderer

# Hebrew letters and points as a character class, built without escapes.
_HEB = chr(0x0590) + "-" + chr(0x05FF)
HEB_RUN = re.compile("[" + _HEB + "]+(?:[ -][" + _HEB + "]+)*")
HEB_CH = re.compile("[" + _HEB + "]")
LATIN_CH = re.compile("[A-Za-z]")


def bidir(s):
    """Direction for one block: rtl only when it is mostly Hebrew.

    This used to be dir="auto", which takes the FIRST strong character. The
    Rendering guidance bullets are English sentences that open on a Hebrew
    headword, so each one was laid out right to left: bullet on the right,
    trailing punctuation at the wrong end, mixed runs reordered. Count the
    scripts instead of trusting the first letter.
    """
    plain = re.sub("<[^>]+>", "", s)
    return "rtl" if len(HEB_CH.findall(plain)) > len(LATIN_CH.findall(plain)) else "ltr"


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    # Non-greedy, and NOT [^*]: a bold lead-in often carries an italic term
    # inside it, as in "**What *atzeh* is**". Excluding asterisks made that
    # fail to match, and the raw ** showed on 28 pages. Bold runs first so the
    # italic pass then handles what sits inside it.
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    # Isolate each Hebrew run so it keeps its own order inside English prose
    # without dragging neighbouring punctuation across.
    s = HEB_RUN.sub(lambda m: '<bdi lang="he">' + m.group(0) + "</bdi>", s)
    return s


def join_lines(parts):
    """Join wrapped source lines into one run of text. A line that ends inside a
    hyphenated word ("parents-in-" / "law") joins without a space."""
    out = ""
    for p in (x.strip() for x in parts):
        if out and not re.search("[A-Za-z]-$", out):
            out += " "
        out += p
    return out


def md(text):
    """Render the narrow markdown subset the entries actually use."""
    out, i = [], 0
    lines = text.split("\n")
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,3}) (.+)$", line)                  # headings
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2).strip())}</h{lvl}>")
            i += 1
            continue
        if line.lstrip().startswith("|"):                      # table
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if len(rows) >= 2 and all(set(c) <= set("-: ") for c in rows[1]):
                head, body_rows = rows[0], rows[2:]
            else:
                head, body_rows = None, rows
            t = ['<div class="tablewrap"><table>']
            if head:
                t.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>")
            t.append("<tbody>")
            for r in body_rows:
                t.append("<tr>" + "".join(f'<td dir="{bidir(c)}">{inline(c)}</td>' for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        if re.match(r"^\s*[-*]\s+", line):                      # bullets
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                item = [re.sub(r"^\s*[-*]\s+", "", lines[i])]
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() \
                        and not re.match(r"^\s*[-*]\s+", lines[i]):
                    item.append(lines[i].strip())
                    i += 1
                items.append(join_lines(item))
            out.append("<ul>" + "".join(f'<li dir="{bidir(x)}">{inline(x)}</li>' for x in items) + "</ul>")
            continue
        if re.match(r"^\s*\d+\.\s+", line):                     # numbered
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                item = [re.sub(r"^\s*\d+\.\s+", "", lines[i])]
                i += 1
                while i < len(lines) and lines[i].startswith("   ") and lines[i].strip() \
                        and not re.match(r"^\s*\d+\.\s+", lines[i]):
                    item.append(lines[i].strip())
                    i += 1
                items.append(join_lines(item))
            out.append("<ol>" + "".join(f'<li dir="{bidir(x)}">{inline(x)}</li>' for x in items) + "</ol>")
            continue
        para = [line]                                            # paragraph
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("|", "#")) \
                and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
            para.append(lines[i])
            i += 1
        txt = join_lines(para)
        out.append(f'<p dir="{bidir(txt)}">{inline(txt)}</p>')
    return "\n".join(out)


# ------------------------------------------------------------------- collection

def clean_gloss(g):
    """An English browse headword, not a sentence.

    Entry `en:` fields sometimes carry quotes or a parenthetical aside
    ("molten image (Modern Hebrew: mask)"). Those are useful inside the entry
    and noise in an A-to-Z list, so the aside is dropped and the quotes with it.
    """
    g = g.strip().strip("'\"‘’“” ").strip()
    g = re.sub(r"\s*\([^)]*\)", "", g).strip()
    g = re.sub(r"^(a|an|the|to)\s+", "", g, flags=re.I).strip()
    if not g or len(g) > 42 or not re.search(r"[A-Za-z]", g):
        return ""
    return g



def collect():
    entries, words, english = [], [], []
    for p in sorted(ENTRIES.glob("*.md")):
        t = p.read_text(encoding="utf-8")
        fm = front_matter(t)
        slug = p.stem
        body = t[t.index("\n---\n") + 5:]
        secs = sections(body)
        bottom = next((v for k, v in secs if k == "Bottom line"), "")
        per = {strip_heb(w["he"]): w for w in word_block(t)}
        e = {
            "slug": slug,
            "cluster": fm.get("cluster", slug),
            "domain": fm.get("domain", "other"),
            "hebrew": fm.get("hebrew", []),
            "translit": fm.get("translit", []),
            "english": fm.get("english", []),
            "authorities": fm.get("authorities", []),
            "roots": fm.get("roots", []),
            "status": fm.get("status", "draft"),
            "sources": fm.get("sources", []),
            "bottom_md": bottom,
            "sections": secs,
        }
        entries.append(e)

        seen = set()
        pos = 0
        for h in fm.get("hebrew", []):
            k, disp = strip_heb(h), show_heb(h)
            if not k or k in seen:
                continue
            seen.add(k)
            w = per.get(k, {})
            words.append({"h": disp, "k": k, "n": w.get("nk", ""), "t": w.get("tr", ""),
                          "e": w.get("en", ""), "d": w.get("distinct", ""),
                          "s": slug, "i": pos})
            pos += 1
        for k, w in per.items():
            if k in seen:
                continue
            seen.add(k)
            words.append({"h": show_heb(w["he"]), "k": k, "n": w.get("nk", ""),
                          "t": w.get("tr", ""), "e": w.get("en", ""),
                          "d": w.get("distinct", ""), "s": slug, "i": pos})
            pos += 1

        # Per-word glosses first, since those carry the Hebrew they render. An
        # entry-level gloss is added only if no word already claimed it, so the
        # A-to-Z list shows a Hebrew word wherever one is actually known.
        terms, claimed = {}, set()
        for w in per.values():
            for g in re.split(r",| or ", w.get("en", "")):
                g = clean_gloss(g)
                if g:
                    terms.setdefault(g.lower(), (g, w.get("he", "")))
                    claimed.add(g.lower())
        for g in e["english"]:
            g = clean_gloss(g)
            if g and g.lower() not in claimed:
                terms.setdefault(g.lower(), (g, ""))
        for term, heb in terms.values():
            english.append({"e": term, "h": strip_heb(heb), "c": e["cluster"], "s": slug})
    # The method essay only borrows its example words (מושל, בא...) from groups
    # that have entries of their own; searching one should land on that group,
    # so the essay keeps only the words no other entry has.
    elsewhere = {w["k"] for w in words if w["s"] != METHOD}
    words = [w for w in words if w["s"] != METHOD or w["k"] not in elsewhere]
    # The same on the English side, which it never reached: the essay was
    # listing word, thing, ruler and kingship in the A to Z beside the Word and
    # King entries that actually treat them. It keeps said, spoke and came,
    # which no entry claims.
    en_elsewhere = {x["e"].lower() for x in english if x["s"] != METHOD}
    english = [x for x in english
               if x["s"] != METHOD or x["e"].lower() not in en_elsewhere]
    return entries, words, english



def he_rows(words, emap):
    out = []
    for w in words:
        e = emap[w["s"]]
        shown = w.get("n") or w["h"]
        if w["e"]:
            right = f'<span class="e">{html.escape(w["e"])}</span>'
            if w["d"]:
                right += f'<span class="d">{html.escape(w["d"])}</span>'
        else:
            right = ('<span class="cl">in the ' + html.escape(e["c"]) + ' group: '
                     + html.escape(", ".join(e["g"][:4])) + '</span>')
        out.append(f'<a class="r" data-l="{html.escape(w["k"][0])}" '
                   f'href="entries/{w["s"]}.html#{w["k"]}">'
                   f'<span class="h">{html.escape(shown)}</span><span class="tx">{right}</span>'
                   f'<span class="go" aria-hidden="true">›</span></a>')
    return "".join(out)


def en_rows(terms):
    out = []
    for x in terms:
        c = x["e"][:1].upper()
        if not ("A" <= c <= "Z"):
            continue
        anchor = f'#{x["h"]}' if x["h"] else ""
        out.append(f'<a class="r" data-l="{c}" href="entries/{x["s"]}.html{anchor}">'
                   f'<span class="en">{html.escape(x["e"])}</span>'
                   f'<span class="h">{html.escape(x["h"])}</span>'
                   f'<span class="cl">in the {html.escape(x["c"])} group</span>'
                   f'<span class="go" aria-hidden="true">›</span></a>')
    return "".join(out)


# ------------------------------------------------------------------ page shells

ASSETS = {"css": "app.css", "js": "app.js"}   # filled in at build time with hashed names
# How many essays the guide rests on, and the year the column started: the
# footer's answer to a first-time reader asking how much is behind this.
ESSAYS = {"n": 0, "from": ""}


def essay_span(entries):
    """(essays cited across the guide, the earliest year)."""
    ids, years = set(), []
    for e in entries:
        for s in e["sources"]:
            m = re.match(r"wiaw:(\d+) \"[^\"]*\" \((\d{4})-", s)
            if m:
                ids.add(m.group(1))
                years.append(m.group(2))
    return len(ids), min(years) if years else ""


BASE = str.maketrans("ךםןףץ", "כמנפצ")


def root_key(root):
    """The root's letters, final forms folded: ב-ר-ך -> ברכ. Used for the
    anchor a link points at, so both spellings land in the same place."""
    return "".join(c for c in root if "\u05d0" <= c <= "\u05ea").translate(BASE)


def root_sort(root):
    order = {c: i for i, c in enumerate(ALEFBET)}
    letters = root_key(root)
    return ([order.get(c, 99) for c in letters], len(letters))


def radak(root):
    """Radak's entry for a root, or "" if his dictionary has none. He covers
    Biblical Hebrew, so an Aramaic or Mishnaic root simply has no entry."""
    return (SHORASHIM["roots"].get(root_key(root)) or {}).get("text", "")


def radak_headword(root):
    """His headword for a root, and whether it is the root itself or the place
    he files it under; "" where the letters are his own headword and nothing
    needs saying. The edition marks sin with a holam on the shin, so give it
    its own dot."""
    e = SHORASHIM["roots"].get(root_key(root)) or {}
    if not e or (not e.get("under") and not e.get("more")):
        return ""
    hw = html.escape(e["hw"].replace("שֹ", "שׂ"))
    lead = "he files it under" if e.get("under") else "his headword"
    return (f'<span class="rootnote">{lead} <bdi lang="he">{hw}</bdi></span>')


def radak_pair(root):
    """His entry beside its English rather than under it: the summary on the
    left, his Hebrew on the right. Where the same letters carry two of his
    roots, each gets its own pair. Narrow screens stack them, since two columns
    of this at phone width would leave four words to a line."""
    e = SHORASHIM["roots"].get(root_key(root)) or {}
    parts = [e] + e.get("more", []) if e else []
    out = []
    for p in parts:
        en = gloss_block(p, heading=False, summary=True)
        body = citable(p.get("html") or html.escape(p.get("text", "")))
        if p.get("found"):
            body = body.replace(p["found"], f'<mark>{p["found"]}</mark>', 1)
        head = (f'<p class="rad-hw" dir="ltr" lang="en">Radak’s root '
                f'<bdi lang="he">{html.escape(p["hw"].replace("שֹ", "שׂ"))}</bdi></p>'
                if len(parts) > 1 else "")
        # Built without nesting one f-string inside another: a backslash in an
        # f-string expression is a syntax error before Python 3.12, and the
        # deploy runs 3.11.
        left = f'<div class="rad-pair-en">{en}</div>' if en else ""
        # The letter its citations were filed under, so the page can fetch the
        # right chunk of pesukim when one is opened.
        out.append(f'<div class="rad-pair{"" if en else " alone"}" data-l="{root_key(root)[:1]}">{left}'
                   f'<div class="rad-text" dir="rtl" lang="he">{head}<p>{body}</p></div></div>')
    return "".join(out)


def radak_html(root, label=True):
    """The same entry with the edition's markup: the root's form bold in each
    pasuk, each citation in a .ref span. tools/fetch_shorashim.py has already
    cut it down to those two tags, so it goes into the page as it stands.
    With label False the caller names his headword itself, so the entry page
    does not print the root once as a heading and again as a line under it."""
    e = SHORASHIM["roots"].get(root_key(root)) or {}
    parts = [e] + e.get("more", []) if e else []
    if not parts:
        return ""
    # More than one entry answers to these letters, or Radak files the word
    # under another root. Either way each entry is named by his own headword.
    # The edition marks sin with a holam on the shin; give it its own dot.
    out = []
    for p in parts:
        hw = html.escape(p["hw"].replace("שֹ", "שׂ"))
        note = "Radak has this under the root" if p.get("under") else "Radak’s root"
        body = citable(p.get("html") or html.escape(p.get("text", "")))
        if p.get("found"):                            # the form he cites, so it can be found in a long entry
            body = body.replace(p["found"], f'<mark>{p["found"]}</mark>', 1)
        head = (f'<p class="rad-hw" dir="ltr" lang="en">{note} <bdi lang="he">{hw}</bdi></p>'
                if label or len(parts) > 1 else "")
        # The row this panel opens from already carries the sense line, so a
        # single entry does not print it twice. Where the letters carry two of
        # his roots the row can only show one, and the second needs its own.
        en = gloss_block(p, with_sense=len(parts) > 1)
        left = f'<div class="rad-pair-en">{en}</div>' if en else ""
        out.append(f'<div class="rad-pair{"" if en else " alone"}">{left}'
                   f'<div class="rad-text" dir="rtl" lang="he">{head}<p>{body}</p></div></div>')
    return "".join(out)


def pasuk(ref):
    """The text of a pasuk he cites, from either store, or "" if neither has it."""
    return PESUKIM["verses"].get(ref) or RADAK_PESUKIM["verses"].get(ref) or ""


CITE = re.compile(r'<span class="ref" data-r="([^"]+)">')


def citable(body):
    """His citations, as buttons where the pasuk can be shown and plain text
    where it cannot (his Talmud references, which the page does not carry)."""
    return CITE.sub(lambda m: (f'<span class="ref has-p" role="button" tabindex="0" data-r="{m.group(1)}">'
                               if pasuk(m.group(1)) else '<span class="ref">'), body)


def pesukim_credit():
    """The editions the pesukim come from, each named once with its licence."""
    seen = {}
    for meta in (PESUKIM["meta"], RADAK_PESUKIM["meta"]):
        for m in meta.values():
            if m.get("version"):
                seen.setdefault(m["version"], m.get("license"))
    return "; ".join(f"{html.escape(v)} ({html.escape(l)})" if l and l != "unknown" else html.escape(v)
                     for v, l in sorted(seen.items()))


def gloss(part, field):
    """The guide's English for one of his entries, or "" where none is written."""
    return (GLOSS["glosses"].get(part.get("hw", "")) or {}).get(field, "")


# A run of Hebrew inside an English sentence. The gloss is stored as plain
# text, so without this the Hebrew in it inherits the English UI font, which has
# no Hebrew of its own and falls back to whatever the system offers: the same
# words then read in one face on the left of the page and another on the right.
# A run must be allowed to end on its pointing, not on its last consonant.
# Ending it at the consonant left the vowel outside the span, where a combining
# mark with nothing to sit on renders as a bare dotted circle: חֻקֶּיךָ lost its
# final kamatz that way.
# Its own name, not HEB_RUN. Defined here it used to rebind the module level
# HEB_RUN above, so the entry body got this one too, and this one does not know
# the ASCII hyphen that joins a root's letters: it holds the maqaf instead. ל-צ
# was matched as two single letters, each isolated in its own bdi, and two
# isolates in an English paragraph lay out left to right. The root was stored
# correctly and rendered backwards, reading צל on the page.
GLOSS_HEB_RUN = re.compile("[א-ת][א-ת֑-ׇ־\"' ]*"
                           "[א-ת][֑-ׇ]*"
                           "|[א-ת][֑-ׇ]*")


def en_text(s):
    """Gloss text for an English column: escaped, with its Hebrew marked so it
    takes the Hebrew face and its own direction. Quotes are left alone, since
    this is text and not an attribute, and escaping them would cut a word like
    רז"ל in two."""
    return GLOSS_HEB_RUN.sub(lambda m: f'<bdi lang="he">{m.group(0)}</bdi>',
                             html.escape(s, quote=False))


def gloss_block(part, heading=True, summary=False, with_sense=True):
    """The English for one of his entries, labelled as ours and not his. Each
    part of "more" is one thing his entry holds, under its own heading, so a
    long entry reads as a few short answers rather than a paragraph. The entry
    page names the whole section, so it asks for no heading here.

    `summary` folds each part behind its heading. It is for the entry page,
    where his entry stands beside its English in two columns: the parts render
    every pasuk he quotes and then say what each one says, so open they run half
    again as long as the Hebrew they summarise, and a column billed as the
    summary finished a screen below its source. Folded, the column is the sense
    line and a short list of what the entry holds, and every word is still a
    click away. Headings alone were tried first and gave the reader too little:
    "The things to come" is not worth a line unless it opens."""
    sense = gloss(part, "sense")
    if not sense:
        return ""
    parts = gloss(part, "more") or []
    if not with_sense and not parts:
        return ""
    if summary:
        more = "".join(
            f'<details class="rad-en-d"><summary>{en_text(m["h"])}</summary>'
            f'<p class="rad-en-b">{en_text(m["t"])}</p></details>'
            for m in parts)
        more = f'<div class="rad-en-l">{more}</div>' if more else ""
    else:
        more = "".join(
            f'<div class="rad-en-p"><p class="rad-en-t">{en_text(m["h"])}</p>'
            f'<p class="rad-en-b">{en_text(m["t"])}</p></div>'
            for m in parts)
    # Not "our summary": where his entry is a line or two the gloss gives the
    # whole of it, and 68 of them do, so a standing promise of a summary
    # contradicted the part headed "The whole entry" right under it. "Our
    # account" is true of both and still says the words are ours, not his.
    head = '<p class="rad-en-h">In English, our account of his entry</p>' if heading else ""
    line = f'<p class="rad-en-s">{en_text(sense)}</p>' if with_sense else ""
    return f'<div class="rad-en" dir="ltr" lang="en">{head}{line}{more}</div>'


def radak_opening(text, n=120):
    """The first words of an entry, cut at a space so nothing breaks mid-word."""
    if len(text) <= n:
        return text
    cut = text[:n]
    return cut[:cut.rfind(" ")] + "\u2009\u2026" if " " in cut else cut + "\u2009\u2026"


def root_map(entries):
    """root as written -> [(cluster, slug)], and each root's letters folded."""
    out = {}
    for e in entries:
        for r in e["roots"]:
            if not root_key(r):
                continue
            out.setdefault(r, []).append((e["cluster"], e["slug"]))
    for v in out.values():
        v.sort(key=lambda x: x[0].lower())
    return out


def shell(title, body, *, depth=0, header_search=True, active="", extra_js=""):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="A Hebrew-to-English translation guide: one entry per synonym cluster, every distinction attributed to the authority who draws it.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{up}assets/{ASSETS["css"]}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>א</text></svg>">
</head>
<body data-up="{up}">
<header class="site{'' if header_search else ' bare'}">
  <a class="brand" href="{up}index.html" aria-label="What&rsquo;s in a Word? — back to the start">What&rsquo;s in a Word?</a>
  {'<div class="hsearch"><input id="q" type="search" placeholder="Search Hebrew or English" autocomplete="off" spellcheck="false" dir="auto"><div id="ac" class="ac" hidden></div></div>' if header_search else ''}
  <nav class="navs">
    <a class="meth {'on' if active == 'me' else ''}" href="{up}method.html">About</a>
    <span class="seg">
      <a href="{up}roots.html" lang="he" title="Browse by root" class="ix {'on' if active == 'roots' else ''}">שרשים</a>
      <a href="{up}hebrew.html" lang="he" title="Browse the Hebrew index" class="ix {'on' if active == 'he' else ''}">א–ת</a>
      <a href="{up}english.html" title="Browse the English index" class="{'on' if active == 'en' else ''}">A–Z</a>
    </span>
  </nav>
</header>
<main>
{body}
</main>
<footer>
  <p>Every distinction is attributed; where the authorities disagree, the entry names the views.</p>
  <p class="muted">Built on <em>What&rsquo;s in a Word?</em> by Rabbi Reuven Chaim Klein, published by Ohr Somayach since {ESSAYS["from"]}: {ESSAYS["n"]} essays, and each entry links to the essay it rests on. This is an independent rendering guide: the entries are written here, and the site is not published by or affiliated with Ohr Somayach. Parsha and Yom Tov dates from <a href="https://www.hebcal.com/">Hebcal</a> (CC BY 4.0).</p>
</footer>
<script src="{up}assets/{ASSETS["js"]}"></script>
{extra_js}
</body>
</html>
"""


# The essay on the method of synonyms, not a group of them.
METHOD = "synonyms-davar-vayomer-vayidaber"
# Entries whose words share a root but are not synonyms; the cards say so.
ROOT_FAMILY = {"splendor-tzvi-tzivyon-tzava"}

# slug -> [(cluster, other slug, shared word)], from xref.json; filled in main().
XREF = {}


def glance_cards(mdtext):
    """The At-a-glance table as one card per word, or "" if it is not the
    standard four-column table (Hebrew | translit | English | what sets it
    apart), in which case the caller renders the markdown as it stands."""
    lines = [l.strip() for l in mdtext.strip().split("\n") if l.strip()]
    if len(lines) < 3 or not all(l.startswith("|") for l in lines):
        return ""
    rows = [[c.strip() for c in l.strip("|").split("|")] for l in lines]
    if [c.lower() for c in rows[0]] != ["hebrew", "translit", "english", "what sets it apart"] \
            or any(len(r) != 4 for r in rows[2:]):
        return ""
    cards = []
    for i, (he, tr, en, d) in enumerate(rows[2:]):
        # Attributions in parentheses, "(Malbim)", sit a shade darker so the
        # authority behind each line can be picked out at a glance.
        dhtml = re.sub(r"\(([A-Z][^()]*)\)", r'(<span class="who">\1</span>)', inline(d))
        # The transliteration sits beside the Hebrew it spells out, and the
        # English gets a line of its own. Paired with the English, a long gloss
        # pushed the transliteration onto a second line on some cards only.
        cards.append(f'<div class="wcard w{i % 8}"><div class="wtop">'
                     f'<span class="wh" dir="rtl" lang="he">{inline(he)}</span>'
                     f'<span class="wt">{inline(tr)}</span></div>'
                     f'<div class="we">{inline(en)}</div>'
                     f'<div class="wd">{dhtml}</div></div>')
    # A multi-word name (הר האלהים, Har HaElokim) cannot share a row with its
    # transliteration in a narrow card. Rather than wrap on those cards alone,
    # every card on that page puts the transliteration under the Hebrew.
    stack = any(" " in he.strip() or len(he.strip()) + len(tr.strip()) > 16 for he, tr, _, _ in rows[2:])
    return f'<div class="wcards{" stack" if stack else ""}">' + "".join(cards) + "</div>"


# Hebrew texts of the pesukim and mishnayos the entries cite (references/
# pesukim.json, from tools/fetch_pesukim.py); filled in main(). STOP holds word
# forms so common across those texts (כלם, all) that a root match on them is
# more likely coincidence than the word itself.
PESUKIM = {"meta": {}, "verses": {}}
# Radak's Sefer HaShorashim by root letters (references/shorashim.json, from
# tools/fetch_shorashim.py). Public domain, so the site carries his own words.
SHORASHIM = {"meta": {}, "roots": {}}
# The guide's English for his entries (references/radak-gloss.json), keyed by
# his headword: "sense" for the root's row, "note" for the open panel. Draft,
# and the page says whose summary it is.
GLOSS = {"meta": {}, "glosses": {}}
# The pesukim he cites that the entries do not (references/radak-pesukim.json,
# from tools/fetch_radak_pesukim.py). The entries' own store answers first.
RADAK_PESUKIM = {"meta": {}, "verses": {}}
RADAK_CREDIT = ('Radak, <em>Sefer HaShorashim</em>, Berlin 1847. Public domain, '
                'digitised by <a href="https://www.sefaria.org/">Sefaria</a> '
                'from the National Library of Israel.')
TALMUD = {"meta": {}, "passages": {}}
TALMUD_COMMS = {}   # daf -> the commentaries on it held in TALMUD
STOP = set()
STOP_AT = 12


class Cites:
    """Links an entry's Tanach and Mishnah citations and gathers what the
    pesukim panel shows for each: the text, with the entry's own words marked."""

    def __init__(self, e, wmap=None):
        self.wmap = wmap or {}
        self.words = []
        for h in e["hebrew"]:
            b = refs.bare(h)
            if not b or " " in b:
                continue
            root = next((refs.root_letters(r) for r in e["roots"]
                         if refs.matches_root(b, refs.root_letters(r))), None)
            self.words.append((show_heb(h), b, root))
        self.cards = {}

    def mark(self, word):
        b = re.sub(r"[^א-ת]", "", refs.bare(word))
        if not b:
            return ""
        for disp, hb, root in self.words:
            # The headword itself, with up to two prefix letters (וְסַלּוֹנִים:
            # ו + סלון + ים) and up to three inflection letters after it. A
            # final א or ה is dropped first, since it goes with the ending
            # (גרמניא, בַּגֶּרְמָנִי; כלימה, כְּלִמָּתוֹ).
            for core in dict.fromkeys((hb, hb[:-1] if len(hb) > 3 and hb[-1] in "אה" else hb)):
                i = b.find(core)
                if i != -1 and i <= 2 and all(c in refs.PREFIX for c in b[:i]):
                    tail = b[i + len(core):]
                    if len(tail) <= 3 and all(c in refs.SUFFIX for c in tail):
                        return disp
        if b in STOP:
            return ""
        for disp, hb, root in self.words:
            if root and refs.matches_root(b, root):
                return disp
        return ""

    def tokens(self, text):
        # A maqaf-joined pair (וְגַם־נִכְלְמוּ) is two tokens, so only the word
        # itself is marked; a token ending in maqaf joins the next.
        return [[piece, self.mark(piece)] for w in text.split(" ")
                for piece in re.split(r"(?<=־)", w) if piece]

    def card(self, label, keys, kind):
        # Every citation the site recognises is a link. Where its text cannot
        # be shown (no segment of the amud holds the entry's word, a mishnah
        # numbered differently), the card offers the text on Sefaria instead.
        c = self.text_card(label, keys, kind)
        if c:
            return c
        return {"l": label, "w": [], "t": [],
                "u": "https://www.sefaria.org/" + urllib.parse.quote(keys[0].replace(" ", "_"))}

    def text_card(self, label, keys, kind):
        src = keys[0]
        if kind in ("bavli", "yerushalmi"):
            # A whole amud will not fit a card: show the segments of it that
            # hold the entry's words (at most two), with an ellipsis for the rest.
            # Where the Gemara's text lacks them, try the commentaries on the
            # daf (the one the entry names first, then Rashi and Tosafos).
            # Any other commentary already fetched on this daf is tried last
            # (the Sources list names no commentator, but the body may have).
            extra = [c for c in TALMUD_COMMS.get(keys[0], []) if c not in keys]
            for src in list(keys) + extra:
                segs = TALMUD["passages"].get(src) or []
                hits = [(i, self.tokens(s)) for i, s in enumerate(segs)]
                hits = [(i, t) for i, t in hits if any(m for _, m in t)][:2]
                if hits:
                    break
            else:
                return None
            if " on " in src:
                label = f'{refs.COMMENTARY_NAME.get(src.split(" on ")[0], src.split(" on ")[0])}, {label}'
            toks = []
            for n, (i, t) in enumerate(hits):
                if (n == 0 and i > 0) or (n > 0 and i > hits[n - 1][0] + 1):
                    toks.append(["…", ""])
                toks += t
            if hits[-1][0] < len(segs) - 1:
                toks.append(["…", ""])
        else:
            texts = [PESUKIM["verses"].get(k) for k in keys]
            if not all(texts):
                return None
            toks = [tok for t in texts for tok in self.tokens(t)]
        order = [d for d, _, _ in self.words]
        found = sorted({m for _, m in toks if m}, key=order.index)
        # Mishnah numbering and spelling vary between editions; a mishnah is
        # shown only where the entry's word is actually in it.
        if kind == "mishnah" and not found:
            return None
        return {"l": label, "w": toks, "t": found if len(found) >= 2 else [], "s": src}

    def link(self, fragment):
        out, skip = [], 0
        for p in re.split(r"(<[^>]+>)", fragment):
            if p.startswith("<"):
                if re.match(r"<(a|h2|h3)[\s>]", p):
                    skip += 1
                elif re.match(r"</(a|h2|h3)>", p):
                    skip = max(0, skip - 1)
                out.append(p)
                continue
            runs = refs.find(p) if not skip else []
            if not runs:
                out.append(p)
                continue
            s, pos = [], 0
            for start, _end, kind, book, name, pieces in runs:
                for n, (ps, pe, keys) in enumerate(pieces):
                    a = start if n == 0 else ps
                    k = "|".join(keys)
                    if k not in self.cards:
                        label = p[a:pe] if n == 0 else f"{name} {p[ps:pe]}"
                        self.cards[k] = self.card(label, keys, kind)
                    if not self.cards[k]:
                        continue
                    s.append(p[pos:a])
                    s.append(f'<a class="cite" href="#" data-k="{html.escape(k)}">{p[a:pe]}</a>')
                    pos = pe
            s.append(p[pos:])
            out.append("".join(s))
        return "".join(out)

    def rail(self):
        used = {k: c for k, c in self.cards.items() if c}
        if not used:
            return ""
        titles = {}
        for k, c in used.items():
            if c.get("u"):
                continue
            first = c.get("s") or k.split("|")[0]
            book = first.rsplit(".", 1)[0] if re.search(r"\.\d+[ab]$", first) else first.rsplit(".", 2)[0]
            book = book.split(" on ")[0]
            meta = PESUKIM["meta"].get(book) or TALMUD["meta"].get(book) or {}
            if meta.get("version"):
                lic = meta.get("license")
                if lic and lic != "unknown" or meta["version"] not in titles:
                    titles[meta["version"]] = lic if lic and lic != "unknown" else titles.get(meta["version"])
        versions = [f"{t} ({l})" if l else t for t, l in titles.items()]
        data = json.dumps(used, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        colors = json.dumps({d: self.wmap[hb] for d, hb, _ in self.words if hb in self.wmap},
                            ensure_ascii=False, separators=(",", ":"))
        return (f'<aside class="prail" aria-label="In the sources"><p class="prail-h">In the sources</p>'
                f'<div class="prail-f" hidden></div><div class="prail-list"></div>'
                f'<p class="prail-credit">Texts from Sefaria: {html.escape("; ".join(versions))}</p></aside>'
                f'<script type="application/json" id="pesukim-data">{data}</script>'
                f'<script type="application/json" id="word-colors">{colors}</script>')


def word_colors(e):
    """Hebrew form (bare) -> colour index, from the order of the word cards.
    A form listed for search that has no card of its own (a verb, a plural)
    takes the colour of the card whose root it shares."""
    glance = next((m for h, m in e["sections"] if h == "At a glance"), "")
    if not glance_cards(glance):
        return {}
    rows = [l.strip().strip("|").split("|") for l in glance.strip().split("\n") if l.strip().startswith("|")][2:]
    cards = [refs.bare(x) for r in rows for x in [r[0].split("/")[0]]]
    out = {c: i % 8 for i, c in enumerate(cards)}
    roots = [refs.root_letters(r) for r in e["roots"]]
    card_root = {c: next((rt for rt in roots if refs.matches_root(c, rt)), None) for c in cards}
    for h in e["hebrew"]:
        b = refs.bare(h)
        if b in out or " " in b:
            continue
        rt = next((rt for rt in roots if refs.matches_root(b, rt)), None)
        hit = next((c for c in cards if rt and card_root[c] == rt), None)
        if hit is not None:
            out[b] = out[hit]
    return out


# Questions written for particular groups; any group with cards can also be
# asked about in the plain form, "What's the difference between x and y?".
CURATED_QUESTIONS = {
    "speech-dibbur-amirah": "Why does the Torah say <i>vayomer</i> here and <i>vayidaber</i> there?",
    "sinai-chorev-gavnunim-bashan": "How many names does Mount Sinai have?",
    "month-bul-marcheshvan": "Why is the eighth month called Bul?",
    "names-moshe-yered-avigdor-yekusiel": "How many names did Moshe have?",
    "second-month-ziv-iyar": "Why was Iyar once called Ziv?",
    "rain-geshem-matar-yoreh-malkosh": "What are the <i>yoreh</i> and the <i>malkosh</i>?",
}


def glance_rows(mdtext):
    """The At-a-glance table as (he, tr, en, line) rows, or [] if it is not the standard table."""
    if not glance_cards(mdtext):
        return []
    lines = [l.strip() for l in mdtext.strip().split("\n") if l.strip()]
    return [tuple(c.strip() for c in l.strip("|").split("|")) for l in lines[2:]]


def difference_question(trs):
    names = [f"<i>{html.escape(x)}</i>" for x in trs]
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return f"What&rsquo;s the difference between {joined}?"


def home_pools(entries):
    """Groups for "Inside an entry" (2 to 4 cards with short lines) and the question pool."""
    taste, asks = [], []
    for e in entries:
        if e["slug"] == METHOD or e["slug"] in ROOT_FAMILY:
            continue
        glance = next((m for h, m in e["sections"] if h == "At a glance"), "")
        rows = glance_rows(glance)
        if len(rows) < 2:
            continue
        trs = [r[1] for r in rows[:3]]
        asks.append({"s": e["slug"], "q": CURATED_QUESTIONS.get(e["slug"]) or difference_question(trs[:2])})
        if 2 <= len(rows) <= 4 and all(len(r[3].split()) <= 16 for r in rows):
            taste.append({"s": e["slug"], "c": e["cluster"], "q": difference_question([r[1] for r in rows]),
                          "cards": glance_cards(glance)})
    # Curated questions first, so a first visit without script shows them.
    asks.sort(key=lambda a: a["s"] not in CURATED_QUESTIONS)
    return taste, asks


# How many of a group's entries a week can draw on. Elul has twenty, and a
# reader who comes back on Wednesday should not meet Monday's three again.
POOL_PER_GROUP = 8


def week_data(entries):
    """{"w": [[Sunday, label, [group keys]], ...], "g": {group: [slugs]},
    "e": {slug: [name, Hebrew]}} from references/seasons.json, from last week
    on. The page takes its links in turn from the Yom Tov, the parsha and the
    season, so each gets a place, and shuffles within each."""
    path = ROOT / "references" / "seasons.json"
    if not path.exists():
        return []
    s = json.loads(path.read_text(encoding="utf-8"))
    names = {e["slug"]: e["cluster"] for e in entries if e["slug"] != METHOD}
    # A Hebrew word shown beside the name ("שופר horn"): the card for the word
    # the slug leads with (praise-hallel -> להלל), else the first card.
    heb = {}
    for e in entries:
        rows = glance_rows(next((m for h, m in e["sections"] if h == "At a glance"), ""))
        if rows:
            lead = re.sub(r"[^a-z]", "", (e["slug"].split("-") + [""])[1])
            row = next((r for r in rows if lead and lead in re.sub(r"[^a-z]", "", r[1].lower())), rows[0])
            heb[e["slug"]] = row[0].split("/")[0].strip()
    since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    # The week names its groups; the groups hold their best entries, and the
    # page draws a fresh set from them on every visit. A week is kept small:
    # the groups and the names are written once, not once a week.
    weeks, keep, used = [], {}, set()
    for w in s["weeks"]:
        if w["from"] < since:
            continue
        keys = [g for g in w["lead"] + w["parsha"] + w["mix"] if s["groups"].get(g)]
        if not keys:
            continue
        weeks.append([w["from"], w["label"], keys])
        for g in keys:
            if g not in keep:
                keep[g] = [x for x in s["groups"][g] if x in names][:POOL_PER_GROUP]
                used.update(keep[g])
    return {"w": weeks, "g": keep, "e": {x: [names[x], heb.get(x, "")] for x in sorted(used)}}


def week_picks(data, week, count):
    """Entries for a week, one group after another. The build takes the first
    of each; the page shuffles first, which is where the rotation comes from."""
    lists = [list(data["g"].get(g, [])) for g in week[2]]
    picks = []
    while len(picks) < count and any(lists):
        for l in lists:
            while l and l[0] in picks:
                l.pop(0)
            if l and len(picks) < count:
                picks.append(l.pop(0))
    return picks


def week_html(data, week):
    if not week:
        return ""
    links = "".join(f'<a href="entries/{s}.html"><bdi lang="he">{html.escape(data["e"][s][1])}</bdi>'
                    f'{html.escape(data["e"][s][0])}<span class="chev" aria-hidden="true">&rsaquo;</span></a>'
                    for s in week_picks(data, week, 3))
    return f'<span class="week-h">This week &middot; <b>{html.escape(week[1])}</b></span><span class="week-l">{links}</span>'


def taste_html(x):
    """The whole taste is one link to its entry: the question, then the cards.
    A chevron on the question is the only thing that says so; a "Read the
    entry" line under the cards said it twice."""
    if not x:
        return ""
    return (f'<a class="taste-go" href="entries/{x["s"]}.html" aria-label="Read the {html.escape(x["c"])} entry">'
            f'<p class="taste-q">{x["q"]}<span class="chev" aria-hidden="true">&rsaquo;</span></p>{x["cards"]}</a>')


def questions_html(items):
    return "".join(f'<a href="entries/{a["s"]}.html"><span>{a["q"]}</span>'
                   f'<span class="chev" aria-hidden="true">&rsaquo;</span></a>' for a in items)


def radak_section(e):
    """His entries on the entry's roots, at the foot of the page with the other
    sources. It is background on where the words come from, not a way in to the
    cluster, and under the title it stood between the reader and the first thing
    the entry has to say."""
    roots = [r for r in sorted(e.get("roots", []), key=root_sort) if radak(r)]
    if not roots:
        return ""
    # One heading a root, carrying the root as our entries write it and, only
    # where it differs, his own headword. Before this the root was named twice
    # by two different routes, and which one a reader saw depended on whether
    # that root's English had been written yet.
    blocks = "".join(
        f'<h4><a href="../roots.html#r-{root_key(r)}" dir="rtl" lang="he">{html.escape(r)}</a>'
        f'{radak_headword(r)}</h4>{radak_pair(r)}'
        for r in roots)
    one = len(roots) == 1
    return (f'<details class="radak" id="s-radak"><summary>'
            f'<h2>Radak on {"this root" if one else "these roots"}</h2>'
            f'<span class="guide-hint">Sefer HaShorashim</span></summary>'
            f'{blocks}<p class="radak-credit">{RADAK_CREDIT}</p></details>')


def entry_page(e):
    # Lay the words out left to right in the same order as the At-a-glance table,
    # with each word marked RTL on its own. A single dir="rtl" block would be
    # correct Hebrew but would right-align the group away from the heading and
    # reverse it against the table beneath it.
    # No separator dots: where the line wraps on a phone a dot was left dangling
    # at the end of a row. The wide gap alone keeps "הר האלהים" reading as one name.
    heb = "".join(f'<span dir="rtl">{html.escape(h)}</span>' for h in e["hebrew"][:6])
    anchors = "".join(
        f'<span id="{html.escape(strip_heb(h))}"></span>' for h in e["hebrew"])
    # "other" is the catch-all domain and tells a reader nothing, so it gets no label.
    title = e["cluster"]
    eyebrow = '<p class="eyebrow">method</p>\n' if e["slug"] == METHOD else "" if e["domain"] == "other" else f'<p class="eyebrow">{html.escape(e["domain"])}</p>\n'
    radak_block = radak_section(e)
    parts = [f'''<article class="entry">
{anchors}
{eyebrow}<h1>{html.escape(title)}</h1>''']
    # Where the entry has word cards they come first: they are the easiest thing
    # on the page to read, and the Bottom line mostly restates them. It follows
    # as a plain "In short" for what the cards do not carry (how the words
    # relate, and any dispute). The cards also show every Hebrew word, so the
    # Hebrew line under the title is left off those pages rather than doubled.
    # The markdown keeps its order either way.
    has_cards = any(h == "At a glance" and glance_cards(m) for h, m in e["sections"])
    wmap = word_colors(e)
    if e["slug"] == METHOD:
        # The method essay's words are three example pairs from different
        # groups; laid out as a header they read as one group of synonyms.
        parts[0] += (
            '\n<div class="method-note"><p><strong>This page works differently.</strong> It is not a '
            'group of synonyms but Rabbi Klein’s introduction to the whole series: why Hebrew has '
            'near-synonyms at all, and the ways they turn out to differ. The three pairs below are '
            'only his examples, and each is covered on its own page: '
            '<a href="speech-dibbur-amirah.html">Speech</a> (<em>vayomer</em>, <em>vayidaber</em>), '
            '<a href="king-melech-moshel.html">King</a> (<em>melucha</em>, <em>moshel</em>), and '
            '<a href="coming-biah-halichah-atah.html">Coming</a> (<em>ba</em>, <em>atah</em>). '
            'It belongs with <a href="../method.html">About</a>, which carries the same '
            'question from his article in <em>Babel</em>.</p></div>')
    elif not has_cards:
        parts[0] += f'\n<p class="heb-title">{heb}</p>'
    # Each word's own distinction reads before the disputes about them.
    secs = list(e["sections"])
    names = [h for h, _ in secs]
    if "Distinctions" in names and "Where the authorities disagree" in names \
            and names.index("Distinctions") > names.index("Where the authorities disagree"):
        d = secs.pop(names.index("Distinctions"))
        secs.insert(names.index("Where the authorities disagree"), d)
    # "On this page": one link per section the entry actually has, and under
    # Distinctions one per word, so a long entry can be crossed in a click.
    # Shown only on wide screens; see .toc in the CSS.
    toc = []

    def sid(name):
        return "s-" + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "x")

    def distinction_ids(block):
        subs = []

        def tag(m):
            n = len(subs) + 1
            # Some entries open a heading lowercase ("tzvi (צבי)", "the two-letter
            # root"), others capitalised ("Sinai (סיני)"); shown, they start with
            # a capital like every other heading and link on the page.
            text = re.sub(r"^((?:<[^>]+>)*)([a-z])", lambda mm: mm.group(1) + mm.group(2).upper(), m.group(1))
            # The heading as written, in one style for every link. Pulling the
            # Hebrew out to the front only worked for "name (Hebrew)" headings,
            # and the rail came out mixed wherever a heading was shaped otherwise.
            label = f'<span class="tt">{text}</span>'
            subs.append((f"d-{n}", label, re.sub(r"<[^>]+>", "", text)))
            text = re.sub(r'<bdi lang="he">([^<]+)</bdi>',
                          lambda mm: (f'<bdi lang="he" class="w{wmap[refs.bare(mm.group(1))]}">{mm.group(1)}</bdi>'
                                      if refs.bare(mm.group(1)) in wmap else mm.group(0)), text)
            return f'<h3 id="d-{n}">{text}</h3>'
        return re.sub(r"<h3>(.*?)</h3>", tag, block), subs

    cites = Cites(e, wmap)
    deferred = None
    xref = XREF.get(e["slug"])
    for headname, mdtext in secs:
        if headname == "Notes for a project" and mdtext.strip() in ("None yet.", ""):
            continue
        if headname == "Bottom line" and has_cards:
            deferred = (f'<section class="inshort" id="s-in-short"><h2>In short</h2>{cites.link(md(mdtext))}</section>',
                        ("s-in-short", "In short", []))
            continue
        # Where else a reader can follow one of these words goes with the
        # entry's own material, not down among the apparatus: before the
        # translators' section rather than wedged between it and Radak. Entries
        # all carry Rendering guidance, but fall back to Sources for one that
        # somehow does not, so the list cannot be dropped.
        if headname in ("Rendering guidance", "Sources") and xref:
            items = "".join(
                f'<li><a href="{html.escape(s)}.html">'
                # "Synonyms" alone reads as a group of synonyms called synonyms,
                # which is the one thing that page is not.
                f'{html.escape("Synonyms: the method" if s == METHOD else c[:1].upper() + c[1:])}</a>'
                f'<span class="xw">{inline(w)}</span></li>'
                for c, s, w in xref)
            parts.append(f'<section class="xref" id="s-also"><h2>Also discussed in</h2><ul>{items}</ul></section>')
            toc.append(("s-also", "Also discussed in", []))
            xref = None
        # It belongs with the sources and before them: background on where the
        # words come from, once the entry has had its say.
        if headname == "Sources" and radak_block:
            parts.append(radak_block)
            toc.append(("s-radak", "Radak on the roots", []))
            radak_block = ""
        cls = {"Bottom line": "bottomline", "At a glance": "glance",
               "Where the authorities disagree": "disagree"}.get(headname, "")
        i = sid(headname)
        if headname == "Rendering guidance":
            # Collapsed by default: most readers come to understand the words,
            # not to translate them, and this section is advice for the second
            # group. <details> needs no script, and a crawler or an LLM reading
            # the HTML still gets the full text.
            parts.append(f'<details class="guide" id="{i}"><summary><h2>{html.escape(headname)}</h2>'
                         f'<span class="guide-hint">For translators</span></summary>{cites.link(md(mdtext))}</details>')
            toc.append((i, headname, []))
            continue
        if headname == "At a glance" and glance_cards(mdtext):
            note = ('<p class="root-note">Words from one root, not synonyms: each card is a meaning of its own.</p>'
                    if e["slug"] in ROOT_FAMILY else "")
            parts.append(f'<section class="glance" id="{i}"><h2>At a glance</h2>{note}{glance_cards(mdtext)}</section>')
            toc.append((i, headname, []))
            if deferred:
                parts.append(deferred[0])
                toc.append(deferred[1])
                deferred = None
            continue
        body, subs = md(mdtext), []
        if headname == "Distinctions":
            body, subs = distinction_ids(body)
        body = cites.link(body)
        parts.append(f'<section class="{cls}" id="{i}"><h2>{html.escape(headname)}</h2>{body}</section>')
        toc.append((i, headname, subs))
    if radak_block:                       # an entry with no Sources section
        parts.append(radak_block)
        toc.append(("s-radak", "Radak on the roots", []))
    parts.append("</article>")
    links = []
    for i, name, subs in toc:
        sub = "".join(f'<li><a href="#{d}" title="{html.escape(plain, quote=True)}">{label}</a></li>'
                      for d, label, plain in subs)
        links.append(f'<li><a href="#{i}">{html.escape(name)}</a>'
                     + (f'<ul>{sub}</ul>' if sub else "") + "</li>")
    nav = (f'<nav class="toc" aria-label="On this page"><p class="toc-h">On this page</p>'
           f'<ul>{"".join(links)}</ul></nav>')
    rail = cites.rail()
    page = (f'<div class="entry-layout{" has-rail" if rail else ""}">{nav}\n'
            + "\n".join(parts) + rail + "</div>")
    # His citations open their pesukim here too, not only on the roots page.
    return shell(f'{title} — What’s in a Word?', page, depth=1, active="",
                 extra_js='<script>wireEntryCites();</script>')


# ------------------------------------------------------------------------ build

def main():
    for kind, text in (("css", CSS), ("js", JS)):
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
        ASSETS[kind] = f"app.{h}.{kind}"

    entries, words, english = collect()
    ESSAYS["n"], ESSAYS["from"] = essay_span(entries)
    clusters = {e["slug"]: e["cluster"] for e in entries}
    xref_file = ROOT / "xref.json"
    if xref_file.exists():
        for p in json.loads(xref_file.read_text(encoding="utf-8"))["pairs"]:
            if p["a"] in clusters and p["b"] in clusters:
                XREF.setdefault(p["a"], []).append((clusters[p["b"]], p["b"], p["word"]))
                XREF.setdefault(p["b"], []).append((clusters[p["a"]], p["a"], p["word"]))
        for v in XREF.values():
            v.sort(key=lambda x: x[0].lower())
    for name, store in (("pesukim.json", PESUKIM), ("talmud.json", TALMUD),
                        ("shorashim.json", SHORASHIM), ("radak-gloss.json", GLOSS),
                        ("radak-pesukim.json", RADAK_PESUKIM)):
        f = ROOT / "references" / name
        if f.exists():
            store.update(json.loads(f.read_text(encoding="utf-8")))
    for key in TALMUD["passages"]:
        if " on " in key:
            TALMUD_COMMS.setdefault(key.split(" on ", 1)[1], []).append(key)
    # Counted per corpus: the Gemara texts are several times the size of the
    # pesukim, and pooling them raised the bar until כלם (all) passed again.
    verses = list(PESUKIM["verses"].values())
    segs = [s for ss in TALMUD["passages"].values() for s in ss]
    for corpus in (verses, segs):
        if not corpus:
            continue
        freq = Counter(re.sub(r"[^א-ת]", "", refs.bare(w))
                       for v in corpus for w in re.split(r"[\s־]+", v))
        bar = STOP_AT * max(1, len(corpus) // max(1, len(verses)))
        STOP.update(w for w, c in freq.items() if c >= bar)
    # Write in place and sweep stale files afterwards, rather than deleting the
    # tree first: on a OneDrive-synced folder the sync client holds directory
    # handles and rmtree fails with WinError 5 half way through.
    (OUT / "entries").mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    written = set()

    def emit(rel, text):
        f = OUT / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        written.add(f.resolve())

    def copy(rel, src):
        f = OUT / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(pathlib.Path(src).read_bytes())
        written.add(f.resolve())

    words.sort(key=lambda w: (w["k"], w["s"]))
    english.sort(key=lambda x: (x["e"].lower(), x["c"]))
    emap = {e["slug"]: {"c": e["cluster"],
                        "a": e["translit"],      # searchable: most transliterations live here
                        "g": e["english"]}
            for e in entries}
    data = {
        "built": datetime.date.today().isoformat(),
        "counts": {"entries": len(entries), "words": len(words), "english": len(english)},
        "entries": emap,
        "words": words,
        "english": english,
    }
    emit("data.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    for e in entries:
        emit(f'entries/{e["slug"]}.html', entry_page(e))

    # The method essay is a page, not a group of synonyms.
    n_words, n_entries = len(words), sum(1 for e in entries if e["slug"] != METHOD)
    taste_pool, question_pool = home_pools(entries)
    taste_json = json.dumps(taste_pool, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    questions_json = json.dumps(question_pool, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    weeks = week_data(entries)
    today = datetime.date.today()
    this_sunday = (today - datetime.timedelta(days=(today.weekday() + 1) % 7)).isoformat()
    this_week = next((w for w in weeks["w"] if w[0] == this_sunday), None)
    weeks_json = json.dumps(weeks, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    first_taste = next((x for x in taste_pool if x["s"].startswith("wisdom-")), taste_pool[0] if taste_pool else None)
    home = f'''<section class="hero">
  <div class="banner">
    <h1 class="wm">What&rsquo;s in a Word?</h1>
    <p class="wm-sub">Synonyms in the Hebrew Language</p>
    <p class="wm-sub wm-credit">From the essays of <span class="nw">Rabbi Reuven Chaim Klein</span></p>
    <hr class="wm-rule">
  </div>
  <p class="lede"><span class="tally" data-to="{n_words}">{n_words:,}</span> words in <span class="tally" data-to="{n_entries}">{n_entries}</span> groups of
  near-synonyms, each word with its own meaning clarified and the sources that discuss it.</p>
  <div class="bigsearch">
    <svg viewBox="0 0 24 24" class="mag" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
    <input id="q" type="search" placeholder="Type Hebrew or English&hellip;" autocomplete="off" spellcheck="false" dir="auto">
    <div id="ac" class="ac" hidden></div>
  </div>
  <div class="week" id="week"{'' if this_week else ' hidden'}>{week_html(weeks, this_week)}</div>
  <script type="application/json" id="week-data">{weeks_json}</script>
</section>
<section class="how" aria-label="How it works">
  <ol class="how-steps">
    <li><b>The idea</b>Two Hebrew words almost never mean exactly the same thing: near-synonyms each carry a shade of their own.</li>
    <li><b>The sources</b>Rashi, Radak, Malbim, Rav Hirsch and many others say where the line between them falls.</li>
    <li><b>The page</b>Each group sets out every word&rsquo;s meaning, who says what, and where they disagree.</li>
  </ol>
</section>
<section class="asks" aria-labelledby="asks-h">
  <p class="home-h" id="asks-h">Questions to explore</p>
  <div class="asks-list" id="asks">{questions_html(question_pool[:4])}</div>
  <script type="application/json" id="ask-pool">{questions_json}</script>
</section>
<section class="taste" aria-labelledby="taste-h">
  <p class="home-h" id="taste-h">Inside an entry</p>
  <div id="taste">{taste_html(first_taste)}</div>
  <script type="application/json" id="taste-pool">{taste_json}</script>
</section>
<section class="split">
  <a class="card" href="hebrew.html"><h3>Browse Hebrew<span class="chev" aria-hidden="true">&rsaquo;</span></h3>
    <p><bdi lang="he">א&#1523; ועד ת&#1523;</bdi> &middot; {n_words:,} words</p></a>
  <a class="card" href="english.html"><h3>Browse English<span class="chev" aria-hidden="true">&rsaquo;</span></h3>
    <p>A to Z &middot; {len(english):,} terms</p></a>
  <a class="card" href="roots.html"><h3>Browse Roots<span class="chev" aria-hidden="true">&rsaquo;</span></h3>
    <p><bdi lang="he">שרשים</bdi> &middot; {len(root_map(entries)):,} roots</p></a>
</section>'''
    emit("index.html", shell("What’s in a Word? — Synonyms in the Hebrew Language", home, header_search=False))

    letters = "".join(f'<button class="ltr" data-l="{l}">{l}</button>' for l in ALEFBET)
    he_body = f'''<section class="browse">
  <h1>Hebrew</h1>
  <p class="lede" dir="rtl" lang="he">א&#1523; ועד ת&#1523;</p>
  <div class="letters heb">{letters}</div>
  <p class="count" id="count">{len(words):,} words</p>
  <div id="list" class="rows">{he_rows(words, emap)}</div>
</section>'''
    emit("hebrew.html", shell("Hebrew — What’s in a Word?", he_body, active="he",
                              extra_js='<script>initBrowse("he");</script>'))

    en_letters = "".join(f'<button class="ltr" data-l="{c}">{c}</button>'
                         for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    en_body = f'''<section class="browse">
  <h1>English</h1>
  <p class="lede">A to Z, from the English rendering back to the Hebrew it translates.</p>
  <div class="letters">{en_letters}</div>
  <p class="count" id="count">{sum(1 for x in english if x["e"][:1].upper().isalpha()):,} terms</p>
  <div id="list" class="rows en3">{en_rows(english)}</div>
</section>'''
    emit("english.html", shell("English — What’s in a Word?", en_body, active="en",
                               extra_js='<script>initBrowse("en");</script>'))

    rmap = root_map(entries)
    # Where Radak files one of our roots under another that the list also
    # carries (גרזן under גרז), his entry belongs to the root that owns it, and
    # the second row points there rather than printing the same words again.
    owner = {}
    for r in rmap:
        e = SHORASHIM["roots"].get(root_key(r)) or {}
        if e and not e.get("under"):
            owner.setdefault(e["hw"], r)
    # An expand control on the right of the row, so it is plain that the row
    # opens on to something rather than being a line of text.
    # The other browse pages' rows are links, and carry the chevron that means
    # go. This row expands in place, so it takes the plus and minus that mean
    # open and close, and never the chevron.
    chev = ('<span class="rexp" aria-hidden="true"><svg viewBox="0 0 24 24" width="15" height="15" '
            'fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">'
            '<line x1="5" y1="12" x2="19" y2="12"></line>'
            '<line class="rexp-v" x1="12" y1="5" x2="12" y2="19"></line></svg></span>')
    rrows = []
    for r in sorted(rmap, key=root_sort):
        links = " &middot; ".join(f'<a href="entries/{s}.html">{html.escape(c)}</a>' for c, s in rmap[r])
        first = root_key(r)[:1]
        text = radak(r)
        # The English says what the root means, which is what a reader scanning
        # the list wants; his Hebrew opening stands in until one is written.
        # Where the letters carry two of his roots, the row says both: folded,
        # שׂבע and שׁבע are one word, and neither is the row's answer alone.
        e = SHORASHIM["roots"].get(root_key(r)) or {}
        under = owner.get(e.get("hw", "")) if e.get("under") else None
        sense = "" if under and under != r else "  ".join(
            x for x in (gloss(part, "sense") for part in ([e] + e.get("more", []) if e else [])) if x)
        # A root of one or two letters is not a fault in the data. The essays
        # discuss them: Rabbi Pappenheim traces gan to the single letter gimmel,
        # with precedent in Machberes Menachem and in Rashi. Radak's dictionary
        # is built on roots of three, so it has nothing for any of the 316 of
        # them, and an empty cell there read as something broken.
        n = len(root_key(r))
        rad = (f'<span class="rad points">Radak has this under '
               f'<a href="#r-{root_key(under)}" dir="rtl" lang="he">{html.escape(under)}</a></span>'
               if under and under != r else
               f'<span class="rad sense">{html.escape(sense)}</span>' if sense else
               f'<span class="rad" dir="rtl" lang="he">{html.escape(radak_opening(text))}</span>'
               if text and not under else
               f'<span class="rad none">{"One" if n == 1 else "Two"}-letter root, '
               f'no entry of his</span>' if n < 3 else '<span class="rad"></span>')
        rrows.append(f'<div class="r{" has-rad" if text else ""}" data-l="{first}" data-k="{root_key(r)}"'
                     f'{" tabindex=0 role=button aria-expanded=false" if text else ""}>'
                     f'<span class="h" id="r-{root_key(r)}" dir="rtl" lang="he">{html.escape(r)}</span>'
                     f'<span class="tx rlinks">{links}</span>{rad}'
                     f'{chev if text and not under else "<span></span>"}</div>')
    roots_body = f'''<section class="browse">
  <h1>Roots</h1>
  <p class="lede">Every root the entries name, and the groups whose words come from it. Beside each root is what Radak gives it in <em>Sefer HaShorashim</em>; open the row for the rest of his entry, in English and in his own Hebrew.</p>
  <div class="letters heb">{letters}</div>
  <p class="count" id="count">{len(rmap):,} roots</p>
  <div class="rhead" aria-hidden="true"><span>Root</span><span>Groups</span><span>Radak, <em>Sefer HaShorashim</em><span class="rhint">open a row for his entry, in English and his Hebrew</span></span></div>
  <div id="list" class="rows roots">{"".join(rrows)}</div>
  <p class="radak-credit">{RADAK_CREDIT} The pesukim he cites are from
    Sefaria: {pesukim_credit()}.</p>
</section>'''
    chunks = {}
    for r in rmap:
        text = radak(r)
        if text:
            chunks.setdefault(root_key(r)[:1], {})[root_key(r)] = radak_html(r)
    verses = {}
    for r in rmap:
        e = SHORASHIM["roots"].get(root_key(r)) or {}
        for part in ([e] + e.get("more", [])) if e else []:
            for ref in CITE.findall(part.get("html", "")):
                if pasuk(ref):
                    verses.setdefault(root_key(r)[:1], {})[ref] = pasuk(ref)
    for letter, part in chunks.items():
        emit(f"shorashim/{letter}.json", json.dumps(part, ensure_ascii=False, separators=(",", ":")))
    for letter, part in verses.items():
        emit(f"pesukim/{letter}.json", json.dumps(part, ensure_ascii=False, separators=(",", ":")))
    emit("roots.html", shell("Roots — What’s in a Word?", roots_body, active="roots",
                             extra_js='<script>initBrowse("roots");wireRoots();</script>'))

    method_src = ROOT / "references" / "how-synonyms-differ.md"
    pdf_src = ROOT / "sources" / "klein-babel-2020" / "synonyms-in-language.pdf"
    if method_src.exists():
        body = method_src.read_text(encoding="utf-8")
        pdf_pane = ""
        if pdf_src.exists():
            copy("article/synonyms-in-language.pdf", pdf_src)
            pdf_pane = ("""
<div class="pane" id="pane-article" hidden>
  <object class="pdf" data="article/synonyms-in-language.pdf" type="application/pdf">
    <p>Your browser will not display the PDF inline.
       <a href="article/synonyms-in-language.pdf">Open it directly</a>.</p>
  </object>
  <p class="pdfnote">&ldquo;Learning to differentiate between apparent synonyms,&rdquo;
     Rabbi Reuven Chaim Klein, <em>Babel: The Language Magazine</em> 31 (May 2020), 30&ndash;33.</p>
</div>""")
        tabs = ('<div class="tabs">'
                '<button class="tab on" data-pane="summary">Summary</button>'
                '<button class="tab" data-pane="article">The article</button></div>'
                if pdf_pane else "")
        # His own introduction to the column answers the same question this page
        # does, from a different source, and it is a full page of its own rather
        # than a group of synonyms. It belongs here rather than loose among the
        # entries, so About carries the way in to it.
        intro = (f'<div class="method-note"><p><strong>Rabbi Klein\'s own introduction.</strong> '
                 f'The summary above is drawn from his article in <em>Babel</em>. He opened the '
                 f'column itself with the same question, why Hebrew should need several words for '
                 f'one thing, and answered it with the templates the answers tend to follow. That '
                 f'is <a href="entries/{METHOD}.html">a page of its own</a>.</p></div>')
        emit("method.html", shell("Methodology — What’s in a Word?",
                                  f'<article class="entry prose">{tabs}'
                                  f'<div class="pane" id="pane-summary">{md(body)}{intro}</div>'
                                  f'{pdf_pane}</article>',
                                  active="me"))

    # --- machine-facing files ------------------------------------------------
    # The 342 entry pages were linked only from browse pages built by JS, so
    # nothing that does not run scripts could find them. A sitemap makes them
    # discoverable, and llms.txt points a model straight at the JSON rather
    # than making it scrape HTML.
    base = "https://whatsinaword.pages.dev"
    urls = (["", "hebrew.html", "english.html", "method.html"]
            + [f'entries/{e["slug"]}.html' for e in entries])
    today = datetime.date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"<url><loc>{base}/{u}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    emit("sitemap.xml", "\n".join(sm))

    emit("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

    emit("llms.txt", f"""# What's in a Word?

> A Hebrew-to-English translation guide. {len(entries)} entries, each taking one
> cluster of near-synonyms, giving every word its own English, and attributing
> each distinction to the authority who draws it. Where the authorities
> disagree, the entry names the views rather than picking one silently.

Built on Rabbi Reuven Chaim Klein's column "What's in a Word?" (Ohr Somayach).
Every entry cites the essay it rests on, and reports what that essay cites,
attributed as he attributes it. Nothing is brought in from outside the essays.

## Machine-readable data

- [data.json]({base}/data.json): every headword in one file.
  `entries` maps a slug to its cluster name, transliterations and English
  glosses. `words` is one record per Hebrew word: `h` the spelling, `k` the
  same folded for matching (no nikud, final letters normalised), `n` the
  pointed form where known, `t` transliteration, `e` its own English, `d` the
  line that separates it from its neighbours, `s` its entry slug.
  `english` maps English terms back to Hebrew.
- [sitemap.xml]({base}/sitemap.xml): all {len(urls)} pages.

## Pages

- [Hebrew index]({base}/hebrew.html): {len(words):,} headwords, alef to tav.
- [English index]({base}/english.html): the English renderings, A to Z.
- [Methodology]({base}/method.html): the ways apparent synonyms actually
  differ, and the article that sets them out.

## Caveats worth passing on

Entries are marked `status: draft`: sourced and checked for consistency, but
not yet read one by one against the essays they rest on. Where a word has no
per-word ruling, the site says which group it belongs to rather than implying
its neighbours' glosses are its own meaning.
""")

    emit(f'assets/{ASSETS["css"]}', CSS)
    emit(f'assets/{ASSETS["js"]}', JS)
    emit("_headers", HEADERS)

    stale = [f for f in OUT.rglob("*") if f.is_file() and f.resolve() not in written]
    for f in stale:
        f.unlink()
    if stale:
        print(f"removed {len(stale)} stale file(s)")

    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"{OUT.relative_to(ROOT)}/  {len(entries)} entry pages, {len(words)} Hebrew headwords, "
          f"{len(english)} English terms, {size/1024/1024:.1f} MB")


CSS = r""":root{
  /* A hint of warm paper behind white panels; the name's green is the one
     site colour (links, buttons, focus); gold marks only the together tag.
     The w0..w7 tones follow a word through its card, its marks in the
     sources panel and its heading, so a group can be read by colour. */
  --bg:#fbf9f4; --panel:#fff; --ink:#1d1d1f; --dim:#6b675f; --faint:#8f8a7e;
  --line:#ebe6da; --accent:#1d6b2a; --accent-soft:#e6efe2; --shadow:0 1px 3px rgba(60,50,30,.06),0 8px 28px rgba(60,50,30,.05);
  --ui:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Inter,system-ui,sans-serif;
  --radius:14px; --heb:"Frank Ruhl Libre","SF Hebrew","Noto Sans Hebrew","Arial Hebrew","Times New Roman",serif;
  --brand:#14601f; --brand-sub:#2f6b3a;
  --gold:#8a6d2a; --gold-soft:#f2e8cf;
  --w0:#3f6690; --w1:#98583a; --w2:#2f7a72; --w3:#7a4f86; --w4:#6d7431; --w5:#9a4a5e; --w6:#4b5aa0; --w7:#8a5a24;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#12110e; --panel:#1c1a16; --ink:#f3efe6; --dim:#b1aa9c; --faint:#8f887a;
  --line:#2f2b24; --accent:#6cc27d; --accent-soft:#1c2a1e; --shadow:0 1px 3px rgba(0,0,0,.5);
  --brand:#6cc27d; --brand-sub:#8fcf9b;
  --gold:#d9b86b; --gold-soft:#2c2616;
  --w0:#8fb1d8; --w1:#e0a07e; --w2:#72c2b8; --w3:#c29bd0; --w4:#b8c070; --w5:#df95a8; --w6:#9aa8e6; --w7:#d9a36a;
}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:400 17px/1.55 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Inter,system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
main{max-width:940px;margin:0 auto;padding:0 22px 96px}

/* header ------------------------------------------------------------------ */
header.site{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:26px;
  padding:15px 26px;background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);
  border-bottom:1px solid var(--line)}
/* The same serif wordmark as the home page. */
.brand{font-family:"Frank Ruhl Libre",Georgia,serif;font-weight:700;color:var(--brand);font-size:24px;flex:0 0 auto;
  white-space:nowrap}
.brand:hover{text-decoration:none;opacity:.75}
.hsearch{flex:1 1 auto;position:relative;max-width:520px;margin:0 auto}
.hsearch input{width:100%;height:40px;padding:0 14px;border:1px solid var(--line);
  border-radius:10px;background:var(--panel);color:var(--ink);font-size:15px;outline:none}
.hsearch input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
header.bare .brand{flex:1}
.navs{display:flex;align-items:center;gap:22px;flex:0 0 auto}
.seg{display:inline-flex;gap:2px;padding:2px;background:var(--line);border-radius:9px}
/* Quieter than the browse control: it is a different kind of page, not a third
   way of looking at the same list. */
.meth{color:var(--dim);font-size:17px;font-weight:500;white-space:nowrap}
.meth:hover{color:var(--ink);text-decoration:none}
.meth.on{color:var(--ink)}
/* Frank Ruhl Libre runs small beside the interface face, so the Hebrew tabs take
   a size of their own to sit level with A-Z rather than under it. */
.seg a.ix{font-family:var(--heb);font-size:1.2em;line-height:1.15;position:relative;top:1px}
.seg a{position:relative;padding:6px 18px;border-radius:7px;font-size:17px;color:var(--dim);font-weight:500}
.seg a:hover{text-decoration:none;color:var(--ink);background:rgba(255,255,255,.55)}
.seg a.on{background:var(--panel);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
/* A hairline between the two segments. On an entry page neither is selected,
   and without it "Hebrew" and "English" were two identical grey labels 2px
   apart that read as one phrase. It hides beside a selected segment, as a
   segmented control does, since the raised pill already separates them. */
.seg a+a::before{content:"";position:absolute;left:-1px;top:22%;bottom:22%;width:1px;
  background:var(--faint);opacity:.45}
.seg a.on::before,.seg a.on+a::before{opacity:0}
/* Phones. The header never wrapped, so every page was ~495px wide on a 375px
   screen and scrolled sideways: the English tab sat off the right edge and the
   header search was crushed to 29px. It now wraps to two rows, wordmark and
   tabs on the first and a full-width search on the second, measured at 430,
   390, 375 and 360px. Methodology stays visible at every one of them; only a
   320px screen takes a third row, and even there nothing scrolls sideways. */
@media (max-width:700px){
  header.site{flex-wrap:wrap;gap:8px 10px;padding:8px 12px}
  .brand{font-size:17px}
  .navs{gap:8px;margin-left:auto}
  .meth{font-size:13px;padding:6px 0}
  .seg a{padding:4px 9px;font-size:13px}
  .hsearch{order:3;flex:1 1 100%;max-width:none;margin:0}
  .hsearch input{height:34px}
}
@media (max-width:400px){
  header.site{gap:8px}
  .brand{font-size:16px}
  .navs{gap:6px}
  .meth{font-size:12.5px}
  .seg a{padding:4px 8px;font-size:12.5px}
}

/* home -------------------------------------------------------------------- */
.hero{padding:64px 0 30px;text-align:center}
.banner{margin:0 0 30px}
/* A serif wordmark over a letterspaced small-caps line and a short rule. The
   byline moved to the footer: "By Rabbi Klein" under the title read as though
   he wrote this site, and the footer says exactly what the site owes him. */
.hero .wm{font-family:"Frank Ruhl Libre",Georgia,serif;font-weight:700;color:var(--brand);font-size:56px;line-height:1.05;
  letter-spacing:-.01em;margin:0 0 12px}
.wm-sub{color:var(--dim);font-size:12.5px;font-weight:600;margin:0;letter-spacing:.18em;text-transform:uppercase}
.wm-rule{width:48px;height:1px;background:var(--line);margin:20px auto 26px;border:0}
/* The credit sits under the subtitle and the rule closes the block, so it is
   set a step quieter: two small-caps lines at one size read as two subtitles. */
.wm-credit{margin-top:11px;font-size:11.5px;font-weight:500;letter-spacing:.12em;color:var(--faint)}
/* On a phone the credit breaks before his name, never inside it. */
.nw{white-space:nowrap}
@media (max-width:640px){.hero .wm{font-size:38px}.wm-sub{font-size:11.5px;letter-spacing:.14em}
  .wm-credit{font-size:10.5px;letter-spacing:.1em}}
.hero h1{font-size:44px;line-height:1.08;letter-spacing:-.022em;font-weight:600;margin:0 0 14px}
.lede{color:var(--dim);font-size:17px;max-width:620px;margin:0 auto 30px}
.tally{font-variant-numeric:tabular-nums;display:inline-block;text-align:right;color:var(--ink);font-weight:500}
/* margin:0 here would drop the auto side-margins that centre the block, leaving the text centred inside a left-hugging box rather than on the page */
.browse .lede[lang="he"]{font-family:var(--heb);font-size:22px;margin:0 auto}
.bigsearch{position:relative;max-width:620px;margin:0 auto}
.bigsearch input{width:100%;height:60px;padding:0 22px 0 54px;font-size:17px;
  border:1px solid var(--line);border-radius:16px;background:var(--panel);color:var(--ink);
  box-shadow:var(--shadow);outline:none;transition:border-color .15s,box-shadow .15s}
.bigsearch input:focus{border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft),var(--shadow)}
.mag{position:absolute;left:20px;top:20px;width:20px;height:20px;fill:none;
  stroke:var(--faint);stroke-width:2;stroke-linecap:round;pointer-events:none}
.home-h{font-size:12.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);font-weight:600;
  margin:0 0 10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.week{margin:22px auto 0;max-width:620px}
.week-h{display:block;font-size:12.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);font-weight:600;margin-bottom:10px}
.week-h b{color:var(--accent);font-weight:600}
.week-l{display:flex;flex-wrap:wrap;justify-content:center;gap:8px}
.week-l a{display:inline-flex;align-items:baseline;gap:8px;border:1px solid var(--line);background:var(--panel);border-radius:999px;
  padding:5px 14px 6px;color:var(--ink);font-size:15px;transition:border-color .15s}
.week-l a:hover{text-decoration:none;border-color:var(--accent)}
.week-l .chev{color:var(--accent)}
.week-l bdi{font-size:18px;line-height:1;color:var(--accent)}
.how{margin-top:20px}
.how-steps{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(3,1fr);counter-reset:step}
.how-steps li{padding:2px 22px;font-size:15px;line-height:1.5;color:var(--dim);counter-increment:step}
.how-steps li:first-child{padding-left:0}
.how-steps li:last-child{padding-right:0}
.how-steps li+li{border-left:1px solid var(--line)}
.how-steps b{display:block;color:var(--accent);font-size:12.5px;text-transform:uppercase;letter-spacing:.07em;
  font-weight:600;margin-bottom:4px}
.how-steps b::before{content:counter(step) " \00b7  "}
/* On a phone the three steps stack, so the label runs into its line instead of
   sitting over it: three lines a step became two, and the questions come up a
   screen sooner. */
@media (max-width:760px){.how-steps{grid-template-columns:1fr}
  .how-steps li{padding:9px 0}.how-steps li:first-child{padding-top:0}.how-steps li:last-child{padding-bottom:0}
  .how-steps li+li{border-left:0;border-top:1px solid var(--line)}
  .how-steps b{display:inline;margin:0 7px 0 0}}
.taste{margin-top:40px}
.taste-q{font-size:20px;margin:0 0 14px;line-height:1.35}
.taste-go{display:block;color:var(--ink)}
.taste-go:hover{text-decoration:none}
.taste-go .chev{color:var(--accent);font-size:15px;margin-left:10px;display:inline-block;transition:transform .15s}
.taste-go:hover .chev{transform:translateX(3px)}
.taste-go:hover .taste-q{color:var(--accent)}
.taste-go:hover .wcard{border-color:var(--dim)}
.asks{margin-top:40px}
.asks-list{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.asks-list a{display:flex;gap:12px;justify-content:space-between;align-items:baseline;
  background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:13px 16px;color:var(--ink);font-size:15px;line-height:1.45;transition:border-color .15s}
.asks-list .chev{color:var(--accent);flex:0 0 auto}
.asks-list a:hover{text-decoration:none;border-color:var(--accent)}
.asks-list a i{color:var(--dim)}
@media (max-width:640px){.asks-list{grid-template-columns:1fr}.taste-q{font-size:18px}}
.split{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:40px}
@media (max-width:860px){.split{grid-template-columns:1fr}}
@media (max-width:640px){.hero h1{font-size:33px}.hero{padding:52px 0 20px}}
/* The two browse cards are the page's other clickable panels, so they are
   built like the question cards rather than as a pair of billboards. */
.card{display:block;padding:13px 16px;border:1px solid var(--line);border-radius:12px;
  background:var(--panel);color:var(--ink);transition:border-color .15s}
.card:hover{text-decoration:none;border-color:var(--accent)}
.card h3{margin:0 0 3px;font-size:15px;font-weight:600;display:flex;justify-content:space-between;align-items:baseline}
.card .chev{color:var(--accent);font-weight:400}
.card p{margin:0;color:var(--dim);font-size:14px}

/* autocomplete ------------------------------------------------------------ */
.ac{position:absolute;left:0;right:0;top:calc(100% + 8px);background:var(--panel);
  border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);
  overflow:hidden;text-align:left;max-height:60vh;overflow-y:auto;z-index:60}
.ac .row{display:grid;grid-template-columns:96px minmax(0,1fr) 20px;align-items:center;gap:14px;
  padding:12px 16px;cursor:pointer;border-bottom:1px solid var(--line);color:var(--ink)}
.ac .row:hover{text-decoration:none}
.ac .row:last-child{border-bottom:0}
.ac .row:hover,.ac .row.sel,.ac .row:active{background:var(--accent-soft)}
.ac .h{font-family:var(--heb);font-size:20px;direction:rtl;text-align:right}
.ac .tx{display:flex;flex-direction:column;gap:2px;min-width:0}
.ac .tr{font-style:italic;color:var(--dim)}
.ac .t{color:var(--dim);font-size:14px;font-style:italic;min-width:96px}
.ac .e{font-weight:500}
.ac .c{color:var(--faint);font-size:13px}
.ac .none{padding:16px;color:var(--dim);font-size:15px}
.ac-cap{padding:9px 16px 8px;font-size:12.5px;color:var(--faint);border-bottom:1px solid var(--line)}
.ac .row{grid-template-columns:96px minmax(0,1fr) auto}
.ac .top-line{display:flex;flex-wrap:wrap;align-items:baseline;gap:0 8px}
.ac .cmp{font-size:13px;color:var(--accent);border:1px solid var(--accent);border-radius:999px;
  padding:3px 11px;white-space:nowrap;justify-self:end}
.ac .row:hover .cmp,.ac .row.sel .cmp{background:var(--accent);color:var(--panel)}
.ac .row.top{grid-template-columns:96px minmax(0,1fr);align-items:start;padding:14px 16px 16px;
  background:color-mix(in srgb,var(--accent-soft) 45%,var(--panel))}
.ac .row.top .h{font-size:24px;padding-top:2px}
.ac .row.top .d{color:var(--dim);font-size:14.5px;line-height:1.45;margin-top:2px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.ac .cta{align-self:flex-start;margin-top:8px;font-size:13.5px;color:var(--panel);background:var(--accent);
  border-radius:999px;padding:4px 13px;white-space:nowrap}
/* The chevron is always visible and always in the accent colour. It used to
   light up only on hover, which a phone does not have, so on a phone nothing
   said the row opened anything. */
.ac .go,.rows .go{color:var(--accent);font-size:24px;line-height:1;justify-self:end;
  transition:transform .15s}
.ac .row:hover .go,.ac .row.sel .go,.rows .r:hover .go{transform:translateX(3px)}

/* browse ------------------------------------------------------------------ */
.browse{padding:46px 0 0}
.browse h1{font-size:36px;letter-spacing:-.02em;font-weight:600;margin:0 0 8px;text-align:center}
.browse > .lede{text-align:center}
.letters{display:flex;flex-wrap:wrap;justify-content:center;gap:7px;margin:26px 0 30px;
  padding-bottom:22px;border-bottom:1px solid var(--line)}
.letters.heb{direction:rtl}
.ltr{min-width:44px;height:44px;padding:0 8px;border:1px solid var(--line);background:var(--panel);
  color:var(--ink);border-radius:11px;font:inherit;font-size:17px;cursor:pointer;
  transition:background .12s,border-color .12s}
.letters.heb .ltr{font-family:var(--heb);font-size:22px}
.ltr:hover{border-color:var(--dim)}
.ltr.on{background:var(--accent);border-color:var(--accent);color:#fff}
.ltr[disabled]{opacity:.3;cursor:default}
.rows{display:flex;flex-direction:column}
.rows .r{display:grid;grid-template-columns:120px minmax(0,1fr) 20px;gap:18px;align-items:center;
  padding:10px 6px;border-bottom:1px solid var(--line)}
.rows.en3 .r{grid-template-columns:minmax(0,260px) minmax(0,150px) minmax(0,1fr) 20px}
.rows.roots .r{grid-template-columns:110px minmax(0,200px) minmax(0,1fr) auto;align-items:baseline;
  padding:9px 6px;gap:16px}
.rexp{display:inline-flex;align-items:center;justify-content:center;width:27px;height:27px;
  border:1px solid var(--line);border-radius:999px;color:var(--dim);background:var(--panel);
  align-self:center;transition:color .15s,border-color .15s,background .15s}
.rows.roots .r:hover .rexp{color:var(--accent);border-color:var(--accent)}
.rows.roots .r[aria-expanded="true"] .rexp{color:var(--accent);border-color:var(--accent);
  background:var(--accent-soft)}
.rexp-v{transform-origin:center;transition:opacity .15s,transform .15s}
.rows.roots .r[aria-expanded="true"] .rexp-v{opacity:0;transform:rotate(90deg)}
.rows.roots .r.has-rad{cursor:pointer}
.rows.roots .r.has-rad:hover{background:var(--panel)}
.rad{font-family:var(--heb);font-size:16px;line-height:1.5;color:var(--dim);overflow:hidden}
.rad.sense{font:400 15px/1.5 var(--ui);color:var(--ink);text-align:left}
.rad.points{font:400 14px/1.5 var(--ui);color:var(--faint);text-align:left}
.rad.points a{font-size:16px;color:var(--dim)}
.rad.none{font:400 13.5px/1.5 var(--ui);color:var(--faint);font-style:italic;text-align:left}
/* It sits inside his Hebrew, which is RTL, so a narrow block would be held to
   the right; these margins keep the English at the left edge of the card. It
   takes the same measure as his Hebrew below it, so the two end on the same
   line and the card does not look as though something were missing. */
.rad-en{font-family:var(--ui);direction:ltr;margin:0 auto 18px 0;padding:0 0 16px;text-align:left;
  max-width:46em;border-bottom:1px solid var(--line)}
.rad-en-h{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);
  font-weight:600;margin:0 0 5px}
.rad-en-s{font:400 17px/1.55 var(--ui);color:var(--ink);margin:0}
.rad-en-p{margin:13px 0 0}
.rad-en-t{font:600 12.5px/1.4 var(--ui);color:var(--ink);margin:0 0 1px}
/* The summary column: what his entry holds, a line a part, each opening on to
   the whole of it. Folded it keeps the column near the length of the Hebrew it
   sits beside; opened it loses the reader nothing. */
.rad-en-l{margin:9px 0 0}
.rad-en-d{border-top:1px solid var(--line)}
.rad-en-d:last-child{border-bottom:1px solid var(--line)}
.rad-en-d>summary{font:600 12.5px/1.45 var(--ui);color:var(--ink);padding:6px 0 6px 15px;
  position:relative;cursor:pointer;list-style:none}
.rad-en-d>summary::-webkit-details-marker{display:none}
.rad-en-d>summary::before{content:"\203a";position:absolute;left:2px;top:5px;color:var(--accent);
  font-size:14px;line-height:1.3;transition:transform .12s ease;transform-origin:50% 55%}
.rad-en-d[open]>summary::before{transform:rotate(90deg)}
.rad-en-d>summary:hover{color:var(--accent)}
.rad-en-d>.rad-en-b{padding:0 0 9px 15px}
.rad-en-b{font:400 15.5px/1.7 var(--ui);color:var(--dim);margin:0}
.rad-en-b bdi,.rad-en-b [lang="he"]{font-family:var(--heb)}
.rad-en bdi,.rad-en-s bdi{font-family:var(--heb)}
/* The same tracks as a row, including the one the open-and-close sign sits in,
   so each heading stands over its own column. */
.rhead{display:grid;grid-template-columns:110px minmax(0,200px) minmax(0,1fr) auto;gap:18px;padding:0 6px 6px;
  border-bottom:1px solid var(--line);color:var(--faint);font-size:12px;letter-spacing:.04em;text-transform:uppercase}
.rhead span:last-child{text-align:left}
/* What the column holds is not what a reader gets by clicking, and nothing on
   the page said the rows opened at all. It sits beside the heading rather than
   under it, so the header stays one line deep. */
.rhint{text-transform:none;letter-spacing:0;font-size:11.5px;
  font-style:italic;color:var(--faint);margin-left:12px;white-space:nowrap}
.rhead em{font-style:normal}
.rad-open{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 22px 20px;margin:4px 0 14px}
.rad-who{margin:0 0 10px;color:var(--dim);font-size:13px}
.rad-who bdi{font-family:var(--heb);font-size:16px;color:var(--accent)}
.rad-body,.rad-text{font-family:var(--heb);font-size:19px;line-height:1.9;color:var(--ink);text-align:right}
/* The measure belongs to his Hebrew, not to the English above it, which starts
   at the left edge of the card as the label does. */
.rad-body>p:not(.rad-hw),.rad-text>p:not(.rad-hw){max-width:46em;margin-left:auto}
.rad-body strong,.rad-text strong{font-weight:700;color:var(--accent)}
.rad-body .ref,.rad-text .ref{font-size:.72em;color:var(--faint);white-space:nowrap}
/* The affordance was scoped to .rad-body, which an entry page never had and the
   roots page stopped having when its panel became two columns: the citations
   still opened, but nothing showed they could be opened. */
.rad-body .ref.has-p,.rad-text .ref.has-p{cursor:pointer;border-bottom:1px dotted var(--accent)}
.rad-body .ref.has-p:hover,.rad-text .ref.has-p:hover{color:var(--accent)}
.rad-body .ref.on,.rad-text .ref.on{color:var(--accent);background:var(--accent-soft);border-radius:3px}
/* The pasuk opens as a block where it is cited, so his text keeps the whole
   width of the card and carries on under it. */
.rad-pasuk{display:block;margin:10px 0;padding:10px 14px;background:var(--bg);
  border:1px solid var(--line);border-radius:10px;text-align:right}
.rad-pasuk-r{display:block;font:400 12px/1.4 var(--ui);color:var(--faint);
  direction:rtl;margin:0 0 4px}
.rad-pasuk-t{display:block;font-family:var(--heb);font-size:18px;line-height:1.7;color:var(--ink)}
.rad-body p,.rad-text p{margin:0 0 14px}
.rad-body p:last-child,.rad-text p:last-child{margin-bottom:0}
p.rad-hw{font-family:var(--ui);direction:ltr;font-size:13px;line-height:1.5;color:var(--dim);text-align:left;margin:0 0 4px}
.rad-body mark,.rad-text mark{background:var(--accent-soft);color:inherit;border-radius:4px;padding:0 3px}
p.rad-hw bdi{font-family:var(--heb);font-size:17px;color:var(--accent)}
.radak-credit{color:var(--faint);font-size:13px;margin:22px 0 0;line-height:1.5}
.radak h4{display:flex;align-items:baseline;gap:10px;margin:22px 0 4px;font-size:15px}
.radak h4 a{font-family:var(--heb);font-size:18px;color:var(--accent)}
.radak h4 .rootnote{font:400 13px/1.4 var(--ui);color:var(--faint)}
.radak h4 .rootnote bdi{font-family:var(--heb);font-size:15px}
.rad-text{margin:0 0 0 auto}
/* On the entry page his Hebrew sits beside its English rather than under it,
   and both run smaller and tighter than on the roots page: the section is
   background, and two columns let a reader put the one against the other. */
.rad-pair{display:grid;gap:4px 26px;margin:0 0 6px}
.radak .rad-pair .rad-text{font-size:17px;line-height:1.75;max-width:none;margin:0}
.radak .rad-pair .rad-text p{max-width:none;margin:0 0 8px}
.rad-pair-en .rad-en{border:0;padding:0;margin:0;max-width:none}
.rad-pair-en .rad-en-s{font:400 14.5px/1.55 var(--ui);color:var(--ink)}
.rad-pair-en .rad-en-p{margin:9px 0 0}
.rad-pair-en .rad-en-t{font-size:11.5px}
.rad-pair-en .rad-en-b{font:400 13.5px/1.6 var(--ui)}
.radak .rad-pair .rad-pasuk{margin:8px 0}
.radak .rad-pair .rad-pasuk-t{font-size:16px;line-height:1.6}
/* The roots page pairs the same way, but it is the page a reader comes to for
   the whole entry, so its parts stand open and both sides run larger. */
.rad-open .rad-pair{margin:0 0 20px}
.rad-open .rad-pair:last-child{margin-bottom:0}
.rad-pair .rad-text>p:not(.rad-hw){max-width:none;margin-left:0}
.rad-open .rad-pair-en .rad-en{padding:0;border:0}
.rad-open .rad-pair-en .rad-en-s{font:400 16px/1.6 var(--ui)}
.rad-open .rad-pair-en .rad-en-b{font:400 14.5px/1.7 var(--ui)}
@media (min-width:900px){
  .rad-pair{grid-template-columns:minmax(0,1fr) minmax(0,1.05fr);align-items:start}
  .rad-pair.alone{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:760px){.rows.roots .r{grid-template-columns:90px minmax(0,1fr) auto;row-gap:4px;gap:10px}
  .rows.roots .rexp{grid-column:3;grid-row:1}
  .rhead{display:none}
  .rad-open{padding:14px 16px 16px}
  .rad-body,.rad-text{font-size:18px;line-height:1.8}
  /* A fold is opened by thumb here, so its row is a 44px target. */
  .rad-en-d>summary{padding:12px 0 12px 18px;font-size:13.5px}
  .rad-en-d>summary::before{top:11px}
  .rows.roots .rad{grid-column:1/-1}}
.rows.roots .h{font-size:20px;line-height:1.3}
.rlinks{color:var(--dim);font-size:14px;line-height:1.5}
.rlinks a{color:var(--ink)}
.rows.en3 .cl{text-align:right}
.rows .tx{min-width:0}
.rows .r{color:var(--ink)}
/* The browse filter hides rows with el.hidden, which leans on the browser's
   own [hidden]{display:none}. An author rule beats a user-agent rule, so the
   display:grid above kept every row on screen and the letter buttons appeared
   to do nothing while the count changed. Anything the script hides must be
   hidden here too. */
[hidden]{display:none!important}
.rows .rhead{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);
  font-weight:600;padding-bottom:8px;border-bottom:1px solid var(--line)}
.rows.en3 .h{text-align:left}
.rows .rhead:hover{background:none}
.rows .r:hover{background:var(--panel);text-decoration:none}
.rows .r:active{background:var(--accent-soft)}
.rows .h{font-family:var(--heb);font-size:21px;direction:rtl;text-align:left}
.rows .en{font-family:inherit;font-size:17px;font-weight:600;direction:ltr;text-align:left}
.rows .t{color:var(--dim);font-style:italic;font-size:14px}
.rows .e{font-weight:500;font-size:16px}
.rows .d{color:var(--dim);font-size:14px;line-height:1.45;display:block;margin-top:1px}
.rows .cl{color:var(--faint);font-size:13.5px}
/* Phones: one tidy line per row, word then text then chevron, instead of the
   word stacked over its text with nothing to tap toward. The search dropdown
   drops its fixed transliteration column, which left a wide empty gap and
   squeezed the English to one word per line. */
@media (max-width:700px){
  .rows .r{grid-template-columns:88px minmax(0,1fr) 18px;gap:12px;padding:10px 4px}
  .rows .h{text-align:right}
  .rows.en3 .r{grid-template-columns:minmax(0,1fr) auto 18px;grid-template-areas:"en h go" "cl cl go";row-gap:2px}
  .rows.en3 .en{grid-area:en}.rows.en3 .h{grid-area:h}.rows.en3 .cl{grid-area:cl;text-align:left}.rows.en3 .go{grid-area:go}
  .ac .row{grid-template-columns:64px minmax(0,1fr) auto;gap:10px;padding:12px 14px}
  .ac .row.top{grid-template-columns:64px minmax(0,1fr)}
  /* On a phone the word "Compare" squeezed the text column to a sliver; the
     row already says "vs.", so the button shrinks to its arrow. */
  .ac .cmp{font-size:0;padding:2px 10px}
  .ac .cmp span{font-size:18px}
  /* A word's distinction line ran six lines on a phone. Two, with an ellipsis,
     keeps the list scannable and the ellipsis itself says there is more. */
  .rows .d{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
}
/* Where the group line is a row's only text it is the row's content, not a
   footnote, and in the faint grey it read as disabled. */
.rows .tx > .cl:only-child,.ac .tx > .c:only-child{color:var(--dim);font-size:15px}
.rows .tx > .cl:only-child{font-size:14px}
.count{color:var(--faint);font-size:14px;margin:0 0 14px}

/* entry ------------------------------------------------------------------- */
.entry{padding:44px 0 0;max-width:760px}
.prose h1{font-size:34px;margin:0 0 18px;text-transform:none}
.tabs{display:inline-flex;gap:2px;padding:2px;background:var(--line);border-radius:9px;margin:0 0 26px}
.tab{border:0;background:none;color:var(--dim);font:inherit;font-size:14px;font-weight:500;
  padding:6px 15px;border-radius:7px;cursor:pointer}
.tab:hover{color:var(--ink)}
.tab.on{background:var(--panel);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.pdf{width:100%;height:min(82vh,1000px);border:1px solid var(--line);border-radius:var(--radius);
  background:var(--panel)}
.pdfnote{color:var(--faint);font-size:14px;margin:12px 0 0}
.prose h2{font-size:13px;border-bottom:1px solid var(--line);padding-bottom:8px;margin:34px 0 14px}
.prose h3{font-size:18px}
.eyebrow{color:var(--faint);font-size:13px;text-transform:uppercase;letter-spacing:.07em;margin:0 0 8px}
.entry h1{font-size:38px;letter-spacing:-.021em;font-weight:600;margin:0 0 6px;text-transform:capitalize}
.heb-title{font-family:var(--heb);font-size:30px;font-weight:400;line-height:1.3;
  color:color-mix(in srgb,var(--ink) 72%,var(--bg));margin:2px 0 30px;direction:ltr;text-align:left;display:flex;flex-wrap:wrap;align-items:baseline;gap:0 28px}
.entry h1+.glance{margin-top:34px}
.wcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.wcard{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:11px 14px 13px}
/* row-reverse keeps the Hebrew at the right; if a long name and its
   transliteration cannot share the row, the transliteration drops under it. */
.wtop{display:flex;flex-direction:row-reverse;justify-content:space-between;align-items:baseline;
  flex-wrap:wrap;gap:0 10px}
.wcards.stack .wtop{flex-direction:column;align-items:flex-end}
.wh{font-family:var(--heb);font-size:26px;font-weight:500;line-height:1.15}
.we{font-weight:600;font-size:15px;line-height:1.35;margin:4px 0 10px;padding-bottom:8px;
  border-bottom:1px solid var(--line)}
.wt{font-style:italic;color:var(--dim);font-size:14px}
.wd{font-size:14px;line-height:1.5;color:var(--dim)}
.wd .who{color:var(--ink)}
.wcard.w0{--wc:var(--w0)}.wcard.w1{--wc:var(--w1)}.wcard.w2{--wc:var(--w2)}.wcard.w3{--wc:var(--w3)}
.wcard.w4{--wc:var(--w4)}.wcard.w5{--wc:var(--w5)}.wcard.w6{--wc:var(--w6)}.wcard.w7{--wc:var(--w7)}
.wcard[class*=" w"]{border-top:3px solid var(--wc)}
.wcard[class*=" w"] .wh{color:var(--wc)}
.pv mark.w0,bdi.w0{color:var(--w0)}.pv mark.w1,bdi.w1{color:var(--w1)}.pv mark.w2,bdi.w2{color:var(--w2)}.pv mark.w3,bdi.w3{color:var(--w3)}
.pv mark.w4,bdi.w4{color:var(--w4)}.pv mark.w5,bdi.w5{color:var(--w5)}.pv mark.w6,bdi.w6{color:var(--w6)}.pv mark.w7,bdi.w7{color:var(--w7)}
/* On this page. Wide screens only: on anything narrower there is no margin to
   put it in, and a phone reader scrolls. The layout widens main just enough for
   the rail, so the article column itself stays 760px. */
.toc{display:none}
.entry [id]{scroll-margin-top:76px}
@media (min-width:1100px){
  main:has(.entry-layout){max-width:1030px}
  .entry-layout{display:grid;grid-template-columns:180px minmax(0,760px);gap:0 44px}
  .toc{display:block;position:sticky;top:76px;align-self:start;margin-top:52px;
    max-height:calc(100vh - 96px);overflow-y:auto;font-size:13.5px;line-height:1.35;
    scrollbar-width:thin}
  .toc-h{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);
    font-weight:600;margin:0 0 10px}
  .toc ul{list-style:none;margin:0;padding:0}
  .toc li{margin:0}
  .toc a{display:block;padding:4px 0 4px 12px;border-left:2px solid var(--line);color:var(--dim)}
  .toc a:hover{color:var(--ink);text-decoration:none}
  .toc a.on{color:var(--accent);border-left-color:var(--accent)}
  .toc ul ul a{padding:3px 0 3px 22px;display:flex;align-items:baseline;gap:7px;
    white-space:nowrap;overflow:hidden}
  .toc .tt{overflow:hidden;text-overflow:ellipsis}
  .toc bdi[lang="he"]{font-size:1.12em}
}
/* Pesukim panel. A citation the entry makes (Yeshayahu 45:16) is a quiet link;
   on a wide screen the panel on the right shows the pesukim cited in the part
   of the entry being read, and on anything narrower the pasuk opens under the
   line when the citation is tapped. */
.entry a.cite{color:inherit;text-decoration:none;border-bottom:1px dotted var(--accent);cursor:pointer}
.entry a.cite:hover,.entry a.cite.lit{color:var(--accent);background:var(--accent-soft);border-radius:3px;text-decoration:none}
.prail{display:none}
.pcard{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:9px 12px 10px;margin:0 0 10px}
.pcard.on{border-color:var(--accent)}
.pref{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:2px 8px;font-size:12.5px;color:var(--dim)}
.ptog{font-size:11.5px;color:var(--gold);background:var(--gold-soft);border-radius:999px;padding:1px 8px;white-space:nowrap}
.ptog bdi{font-family:var(--heb);font-size:13px}
.pv{font-family:var(--heb);font-size:18px;line-height:1.6;text-align:right;margin-top:3px;color:var(--ink)}
.pv mark{background:none;color:var(--accent);font-weight:600}
.pell{color:var(--faint)}
.plink{display:inline-block;font-size:13.5px;margin-top:4px}
.prail-h{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);font-weight:600;margin:0 0 10px}
.prail-f{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.prail-f button{font-family:var(--heb);font-size:15px;border:1px solid var(--line);background:var(--panel);
  border-radius:999px;padding:0 10px;cursor:pointer;color:var(--dim)}
.prail-f button.on{border-color:var(--accent);color:var(--accent)}
.prail-none{font-size:13px;color:var(--faint);margin:0}
.prail-credit{font-size:11.5px;line-height:1.4;color:var(--faint);margin:12px 0 0}
.ppop{margin:8px 0 6px}
.ppop .pcard{cursor:default;margin:0}
/* Under a bullet the card takes back the bullet's indent: on a phone that
   indent is a fifth of the width. */
li > .ppop{margin-inline-start:-1.4em}
.pclose{border:0;background:none;color:var(--faint);font-size:20px;line-height:1;padding:0 2px;cursor:pointer;margin-left:auto}
.pclose:hover{color:var(--ink)}
@media (min-width:1360px){
  main:has(.entry-layout.has-rail){max-width:1320px}
  .entry-layout.has-rail{grid-template-columns:180px minmax(0,760px) 250px;gap:0 40px}
  .prail{display:block;position:sticky;top:76px;align-self:start;margin-top:52px;
    max-height:calc(100vh - 96px);overflow-y:auto;scrollbar-width:thin}
}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
@media (max-width:520px){.wcards{grid-template-columns:1fr}.wh{font-size:24px}.heb-title{font-size:26px;gap:0 22px}}
.entry section{margin:0 0 34px}
.entry h2{font-size:13px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);
  font-weight:600;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.entry h3{font-size:19px;font-weight:600;margin:24px 0 6px}
.entry p{margin:0 0 14px}
.entry li{margin:0 0 8px}
.entry ul,.entry ol{padding-inline-start:1.4em}
.entry li::marker{color:var(--faint)}
.xref ul{list-style:none;padding:0}
.xref li{margin:0 0 8px}
.xref .xw{color:var(--dim);margin-left:10px;font-size:15px}
.bottomline{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 24px 8px;box-shadow:var(--shadow)}
.bottomline h2{border:0;padding:0}
.bottomline p{font-size:18px}
.inshort p{color:var(--ink)}
.root-note{color:var(--dim);font-size:15px;margin:-4px 0 12px}
.method-note{background:var(--accent-soft);border-left:3px solid var(--accent);border-radius:0 var(--radius) var(--radius) 0;
  padding:14px 18px;margin:14px 0 32px}
.method-note p{margin:0;font-size:16px;line-height:1.55}
/* Hebrew inside English text (a gloss in a sentence, the Also-discussed roots,
   a word card) takes the Hebrew face too, a touch larger, since a
   serif Hebrew set at the sans size reads small beside it. */
[lang="he"]{font-family:var(--heb)}
:not([lang="he"]) > bdi[lang="he"]{font-size:1.08em;line-height:1}
.disagree{border-left:3px solid var(--line);padding-left:20px}
.tablewrap{overflow-x:auto;margin:0 0 16px}
details.guide,details.radak{margin:28px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
details.guide>summary,details.radak>summary{display:flex;align-items:baseline;gap:12px;padding:14px 2px;cursor:pointer;
  list-style:none;-webkit-user-select:none;user-select:none}
details.guide>summary::-webkit-details-marker,details.radak>summary::-webkit-details-marker{display:none}
details.guide>summary h2,details.radak>summary h2{margin:0;display:inline}
details.guide>summary::before,details.radak>summary::before{content:"";flex:0 0 auto;width:7px;height:7px;align-self:center;
  border-right:2px solid var(--faint);border-bottom:2px solid var(--faint);
  transform:rotate(-45deg);transition:transform .15s}
details.guide[open]>summary::before,details.radak[open]>summary::before{transform:rotate(45deg)}
details.guide>summary:hover h2,details.radak>summary:hover h2{color:var(--accent)}
.guide-hint{color:var(--faint);font-size:13px;font-weight:500}
details.guide[open]>summary{padding-bottom:6px}
details.guide>:not(summary){padding-bottom:10px}
table{border-collapse:collapse;width:100%;font-size:15px}
th{text-align:left;font-weight:600;color:var(--faint);font-size:12px;text-transform:uppercase;
  letter-spacing:.05em;padding:0 14px 8px 0;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:11px 14px 11px 0;border-bottom:1px solid var(--line);vertical-align:top}
td:first-child{font-family:var(--heb);font-size:20px;white-space:nowrap}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;
  background:var(--line);padding:1px 5px;border-radius:5px}
footer{max-width:940px;margin:0 auto;padding:30px 22px 60px;border-top:1px solid var(--line);
  color:var(--dim);font-size:14px}
footer p{margin:0 0 6px}
.muted{color:var(--faint)}
"""

JS = r"""// Lexicon: client-side search and browse. One data.json, fetched once.
const UP = document.body.dataset.up || "";
const FINALS = {"ך":"כ","ם":"מ","ן":"נ","ף":"פ","ץ":"צ"};
let DATA = null, dataP = null;
let SIBS_ = null;
const SIBS = () => {
  if(!SIBS_){ SIBS_ = {}; for(const x of DATA.words) (SIBS_[x.s] = SIBS_[x.s] || []).push(x); }
  return SIBS_;
};

// Fold a Hebrew query the way the build folded the headwords: drop nikud and
// normalise final letters, so typing a word as it ends a sentence still matches.
function foldHeb(s){
  return s.normalize("NFC").replace(/[֑-ׇ]/g,"")
          .replace(/[ךםןףץ]/g, c => FINALS[c]).trim();
}
const foldLat = s => s.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g,"");
const isHeb = s => /[֐-׿]/.test(s);
const esc = s => (s||"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function load(){
  if(!dataP) dataP = fetch(UP + "data.json").then(r => r.json()).then(d => (DATA = d));
  return dataP;
}


// A transliteration on an entry names one of its words, but nothing records
// which. Compare consonants: "megillah" reduces to m-g-l, which threads through
// מגילה and not through ספר. Each latin consonant maps to the Hebrew letters it
// could be, and the match is a greedy in-order walk, so extra Hebrew letters
// (matres lectionis above all) do not break it.
const SKEL = {ch:"כח", kh:"כח", tz:"צ", ts:"צ", sh:"ש", th:"ת",
              b:"בו", v:"בו", w:"ו", g:"ג", d:"ד", h:"ה", z:"ז", t:"טת",
              y:"י", j:"י", k:"כק", c:"כק", q:"ק", l:"ל", m:"מ", n:"נ",
              s:"סשצ", p:"פ", f:"פ", r:"ר"};

function skeleton(latin){
  const t = (latin || "").toLowerCase().replace(/[^a-z]/g, "");
  const out = [];
  for(let i = 0; i < t.length; ){
    const two = t.slice(i, i + 2);
    if(SKEL[two]){ out.push(SKEL[two]); i += 2; continue; }
    if(SKEL[t[i]]) out.push(SKEL[t[i]]);
    i++;
  }
  // A doubled latin consonant is a dagesh, not two letters: "megillah" is
  // מ-ג-ל-ה with one lamed. Without collapsing, the walk fails on the second.
  return out.filter((c, n) => c !== out[n - 1]);
}

function namesWord(latin, heb){
  const sk = skeleton(latin);
  if(sk.length < 2) return false;
  let j = 0;
  for(const cls of sk){
    while(j < heb.length && !cls.includes(heb[j])) j++;
    if(j >= heb.length) return false;
    j++;
  }
  return true;
}

const ent = w => (DATA.entries && DATA.entries[w.s]) || {c: "", a: [], g: []};

function search(q, limit=12){
  if(!DATA || !q.trim()) return [];
  const out = [];
  // Half a rank for carrying its own English: between two equally good string
  // matches, the word whose entry actually rules on it is the better answer.
  const own = w => (w.e ? 0 : 0.5);
  if(isHeb(q)){
    const k = foldHeb(q);
    for(const w of DATA.words){
      const i = w.k.indexOf(k);
      if(w.k === k) out.push([0 + own(w), w]);
      else if(i === 0) out.push([1 + own(w), w]);
      else if(i > 0) out.push([3 + own(w), w]);
    }
  } else {
    const k = foldLat(q);
    if(!k) return [];
    // Most transliterations live on the entry, not the word: 1,522 of the 2,001
    // words carry none of their own. Without searching the entry's list,
    // "sefer" found nothing even though its entry is titled Book.
    const alias = {};
    for(const slug in DATA.entries){
      const a = DATA.entries[slug].a || [];
      for(const x of a){
        const f = foldLat(x);
        if(!f) continue;
        const r = (f === k) ? 0 : f.startsWith(k) ? 1 : f.includes(k) ? 3 : 9;
        if(r < (alias[slug]?.r ?? 9)) alias[slug] = {r, text: x};
        if(r === 0) break;
      }
    }
    for(const w of DATA.words){
      const e = ent(w);
      const t = foldLat(w.t), en = foldLat(w.e), g = foldLat((e.g || []).join(" "));
      const a = alias[w.s];
      // the word the matched transliteration actually names comes first
      const bonus = a && namesWord(a.text, w.k) ? -1.2 : 0;
      if(t === k || en === k) out.push([0 + own(w), w]);
      // A group named exactly what was typed ("bread") is the answer, even for
      // its words that carry no English of their own; before this, the bread
      // group ranked below a basket whose glosses happened to mention bread.
      else if(foldLat(e.c) === k) out.push([0.9 + own(w), w]);
      else if(t.startsWith(k)) out.push([1 + own(w), w]);
      else if(a !== undefined) out.push([1.6 + a.r + bonus + own(w), w]);
      else if(en.startsWith(k)) out.push([2 + own(w), w]);
      else if(t.includes(k) || en.includes(k)) out.push([3 + own(w), w]);
      else if((e.g || []).some(x => foldLat(x) === k)) out.push([2.5 + own(w), w]);
      else if(g.includes(k)) out.push([5 + own(w), w]);
      else if(foldLat(e.c).includes(k)) out.push([6 + own(w), w]);
    }
  }
  out.sort((a,b) => a[0]-b[0] || (a[1].i|0)-(b[1].i|0) || a[1].k.localeCompare(b[1].k));
  const seen = new Set(), perEntry = {}, res = [];
  for(const [,w] of out){
    const id = w.k + "|" + w.s;
    if(seen.has(id)) continue;
    seen.add(id);
    perEntry[w.s] = (perEntry[w.s] || 0) + 1;
    if(perEntry[w.s] > 3) continue;   // one cluster must not fill the list
    res.push(w);
    if(res.length >= limit) break;
  }
  return res;
}

function href(w){ return UP + "entries/" + w.s + ".html#" + encodeURIComponent(w.k); }

function wire(){
  const q = document.getElementById("q"), ac = document.getElementById("ac");
  if(!q || !ac) return;
  let sel = -1, rows = [];
  const close = () => { ac.hidden = true; sel = -1; };
  const render = list => {
    rows = list;
    if(!list.length){
      ac.innerHTML = '<div class="none">Nothing under that word yet.</div>';
      ac.hidden = false; return;
    }
    // One row shape everywhere: the word, a text block, a chevron. A word's own
    // meaning is bold only where it has one; otherwise the line names its group
    // and the group's words, so the group's glosses never read as this word's.
    // The results used to read as a dictionary: the word, its English, done.
    // People took the gloss for the whole answer and never opened a page. So
    // every result now says what the site is for, that the word has
    // near-synonyms and differs from them: the top match as a card with the
    // start of its distinction and a button, the rest as comparisons.
    // The group's words as its page shows them: the words with a card (a line
    // of their own), not every spelling and related form the entry lists for
    // search. An entry with no cards falls back to all its words.
    const group = w => {
      const all = SIBS()[w.s] || [], carded = all.filter(x => x.d);
      return carded.length ? carded : all;
    };
    const heb = x => `<span dir="rtl" lang="he">${esc(x.n || x.h)}</span>`;
    const oneGroup = list.every(w => w.s === list[0].s);
    // The introduction essay's examples are not a group of synonyms.
    const cap = oneGroup && list[0].s === "synonyms-davar-vayomer-vayidaber"
      ? "An example from Rabbi Klein's introduction to Hebrew synonyms"
      : oneGroup && list[0].s === "splendor-tzvi-tzivyon-tzava"
      ? `${group(list[0]).length} words from one root, not synonyms`
      : oneGroup
      ? `${group(list[0]).length} words in the ${esc(ent(list[0]).c)} group, each with its own shade`
      : "Each word has near-synonyms. Open one to see how they differ";
    ac.innerHTML = `<div class="ac-cap">${cap}</div>` + list.map((w,i) => {
      const E = ent(w), tr = w.t ? `<span class="tr">${esc(w.t)}</span>` : "";
      const others = group(w).filter(x => x.k !== w.k);
      // Every row, the best match included, shows the words it is set against
      // rather than the start of its distinction: a definition in the dropdown
      // read as a translation, and the page is where the distinction lives.
      const vs = others.length
        ? `vs. ${others.slice(0,3).map(heb).join(", ")}${others.length > 3 ? "…" : ""}`
        : `in the ${esc(E.c)} group`;
      if(i === 0){
        const n = group(w).length;
        return `<a class="row top${i===sel?" sel":""}" href="${href(w)}">
         <span class="h">${esc(w.n || w.h)}</span>
         <span class="tx">
           <span class="top-line">${w.e ? `<span class="e">${esc(w.e)}</span>` : `<span class="e">${esc(E.c)}</span>`}${tr}</span>
           <span class="c">${vs}</span>
           <span class="cta">See how the ${n > 1 ? n + " words" : "words"} differ <span aria-hidden="true">›</span></span>
         </span>
       </a>`;
      }
      return `<a class="row${i===sel?" sel":""}" href="${href(w)}">
         <span class="h">${esc(w.n || w.h)}</span>
         <span class="tx">
           <span class="top-line">${w.e ? `<span class="e">${esc(w.e)}</span>` : `<span class="e">${esc(E.c)}</span>`}${tr}</span>
           <span class="c">${vs}</span>
         </span>
         <span class="cmp">Compare <span aria-hidden="true">›</span></span>
       </a>`;
    }).join("");
    ac.hidden = false;
  };
  const run = () => {
    const v = q.value.trim();
    if(!v){ close(); return; }
    load().then(() => render(search(v)));
  };
  q.addEventListener("input", run);
  q.addEventListener("focus", () => { load(); if(q.value.trim()) run(); });
  q.addEventListener("keydown", e => {
    if(ac.hidden){
      // The list can be closed while the box still holds a query (a click
      // elsewhere closed it). Enter should still open the best match.
      const v = q.value.trim();
      if(e.key === "Enter" && v){
        e.preventDefault();
        load().then(() => { const r = search(v); if(r.length) location.href = href(r[0]); });
      }
      return;
    }
    if(e.key === "ArrowDown" || e.key === "ArrowUp"){
      e.preventDefault();
      sel = Math.max(0, Math.min(rows.length-1, sel + (e.key === "ArrowDown" ? 1 : -1)));
      const els = ac.querySelectorAll(".row");
      els.forEach((c,i) => c.classList.toggle("sel", i === sel));
      els[sel]?.scrollIntoView({block:"nearest"});
    } else if(e.key === "Enter"){
      const pick = rows[sel >= 0 ? sel : 0];
      if(pick){ e.preventDefault(); location.href = href(pick); }
    } else if(e.key === "Escape"){ close(); q.blur(); }
  });
  // A click outside the search closes the list.
  document.addEventListener("click", e => {
    if(!ac.contains(e.target) && e.target !== q) close();
  });
}

// A pasuk he cites opens where it is cited, on the roots page and on an entry
// page alike. The pesukim are chunked by the first letter of the root, so a
// card carries the letter its citations were filed under, and the base is "" on
// the roots page and "../" from an entry.
const PES = {};
async function wireCites(card, letter, base){
  const show = async span => {
    if(!PES[letter]){
      try{ PES[letter] = await fetch(`${base}pesukim/${encodeURIComponent(letter)}.json`).then(r => r.json()); }
      catch(err){ PES[letter] = {}; }
    }
    // Whatever is open closes first, before the new pasuk is looked up. Leaving
    // it open when the lookup fails is what reads as a citation being stuck:
    // the reader clicks another and the page appears to ignore them.
    const was = span.classList.contains("on");
    card.querySelectorAll(".ref.on").forEach(x => x.classList.remove("on"));
    card.querySelectorAll(".rad-pasuk").forEach(x => x.remove());
    const t = PES[letter][span.dataset.r];
    if(was || !t) return;
    span.classList.add("on");
    // A block inside his paragraph, so the pasuk opens where it is cited and
    // his text carries on under it at the full width of the card.
    const d = document.createElement("div");
    d.className = "rad-pasuk"; d.dir = "rtl"; d.lang = "he";
    d.innerHTML = `<span class="rad-pasuk-r">${span.textContent.replace(/^\(|\)$/g, "")}</span>`
      + `<span class="rad-pasuk-t">${t.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}</span>`;
    span.after(d);
  };
  card.addEventListener("click", e => {
    const span = e.target.closest(".ref.has-p");
    if(span) show(span);
  });
  card.addEventListener("keydown", e => {
    if(e.key !== "Enter" && e.key !== " ") return;
    const span = e.target.closest(".ref.has-p");
    if(span){ e.preventDefault(); show(span); }
  });
}

// An entry page shows his entries for several roots at once, each filed under
// its own letter, so every pair is wired to the chunk its citations are in.
function wireEntryCites(){
  const up = document.body.dataset.up || "";
  document.querySelectorAll(".rad-pair[data-l]").forEach(p => wireCites(p, p.dataset.l, up));
}

// The roots page: open a row to read Radak on that root. His dictionary is
// two megabytes, so a letter's worth is fetched the first time it is wanted.
function wireRoots(){
  const list = document.getElementById("list");
  if(!list || !list.classList.contains("roots")) return;
  const cache = {};
  const open = async row => {
    const had = row.nextElementSibling;
    if(had && had.classList.contains("rad-open")){
      had.remove(); row.setAttribute("aria-expanded", "false"); return;
    }
    const letter = row.dataset.l, key = row.dataset.k;
    if(!cache[letter]){
      try{ cache[letter] = await fetch(`shorashim/${encodeURIComponent(letter)}.json`).then(r => r.json()); }
      catch(err){ return; }
    }
    const text = cache[letter][key];
    if(!text) return;
    // The text was cut down to <strong> and .ref spans when it was fetched.
    const el = document.createElement("div");
    el.className = "rad-open";
    // The chunk already carries his Hebrew and its English as two columns, each
    // with its own direction, so it is not wrapped in one right-to-left block.
    el.innerHTML = `<p class="rad-who">Radak, <em>Sefer HaShorashim</em>, on the root `
      + `<bdi lang="he">${row.querySelector(".h").textContent}</bdi></p>${text}`;
    row.after(el);
    wireCites(el, letter, "");
    row.setAttribute("aria-expanded", "true");
  };
  list.addEventListener("click", e => {
    const row = e.target.closest(".r.has-rad");
    if(row && !e.target.closest("a")) open(row);
  });
  // A pasuk he cites, shown beside his text on a wide screen and under the
  // line on anything narrower. A letter's pesukim are fetched once, when the
  // first citation in that letter is pressed.
  list.addEventListener("keydown", e => {
    if(e.key !== "Enter" && e.key !== " ") return;
    const row = e.target.closest(".r.has-rad");
    if(row){ e.preventDefault(); open(row); }
  });
}
window.wireRoots = wireRoots;
function initBrowse(mode){
  // The rows are already in the HTML, so this only filters them. That is what
  // lets the page work with scripts off and gives a crawler real links.
  const list = document.getElementById("list");
  const rows = [...list.querySelectorAll(".r")];
  const btns = [...document.querySelectorAll(".ltr")];
  const count = document.getElementById("count");
  const have = new Set(rows.map(r => r.dataset.l));
  btns.forEach(b => { if(!have.has(b.dataset.l)) b.disabled = true; });

  const noun = mode === "en" ? "terms" : mode === "roots" ? "roots" : "words";
  const show = l => {
    btns.forEach(b => b.classList.toggle("on", b.dataset.l === l));
    // An open Radak panel is a sibling of its row and not a row itself, so
    // hiding the rows would leave it standing on its own under a letter it
    // does not belong to. Picking a letter closes it.
    list.querySelectorAll(".rad-open").forEach(p => p.remove());
    list.querySelectorAll('.r[aria-expanded="true"]')
        .forEach(r => r.setAttribute("aria-expanded", "false"));
    let n = 0;
    for(const r of rows){
      const hit = !l || r.dataset.l === l;
      r.hidden = !hit;
      if(hit) n++;
    }
    if(count) count.textContent = `${n.toLocaleString()} ${n === 1 ? noun.slice(0, -1) : noun}`;
    if(l) history.replaceState(null, "", "#" + encodeURIComponent(l));
  };
  btns.forEach(b => b.addEventListener("click", () => show(b.dataset.l)));
  const want = decodeURIComponent(location.hash.slice(1));
  if(want && btns.some(b => b.dataset.l === want && !b.disabled)) show(want);
}
window.initBrowse = initBrowse;
function wireTabs(){
  const tabs = [...document.querySelectorAll(".tab")];
  if(!tabs.length) return;
  tabs.forEach(t => t.addEventListener("click", () => {
    tabs.forEach(x => x.classList.toggle("on", x === t));
    document.querySelectorAll(".pane").forEach(p =>
      p.hidden = (p.id !== "pane-" + t.dataset.pane));
  }));
}

// The home page's word and group counts add themselves up from zero. The real
// numbers are in the HTML, so a crawler, a reader without scripts, or anyone
// who has asked the system to reduce motion simply sees them as they are.
function tally(){
  const els = document.querySelectorAll(".tally[data-to]");
  if(!els.length || document.hidden || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const fmt = n => n.toLocaleString("en-US");
  const dur = 1300, t0 = performance.now();
  const settle = () => els.forEach(el => { el.textContent = fmt(+el.dataset.to); });
  els.forEach(el => { el.style.minWidth = el.offsetWidth + "px"; el.textContent = "0"; });
  const step = now => {
    const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    els.forEach(el => { el.textContent = fmt(Math.round(+el.dataset.to * e)); });
    if(p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  // A browser pauses animation frames in a background tab; the real numbers
  // must never be left showing zero.
  setTimeout(settle, dur + 150);
}

// Highlight the section being read in "On this page", and open Rendering
// guidance when its link is followed, since it is collapsed by default.
function wireToc(){
  const toc = document.querySelector(".toc");
  if(!toc) return;
  const links = [...toc.querySelectorAll("a")];
  const targets = links.map(a => document.getElementById(a.getAttribute("href").slice(1)));
  links.forEach((a, i) => a.addEventListener("click", () => {
    if(targets[i] && targets[i].tagName === "DETAILS") targets[i].open = true;
  }));
  let ticking = false;
  const spy = () => {
    ticking = false;
    let cur = -1;
    targets.forEach((t, i) => { if(t && t.getBoundingClientRect().top < 110) cur = i; });
    // A sub-link wins over its section, and the section stays lit beside it.
    links.forEach((a, i) => a.classList.toggle("on", i === cur ||
      (cur > i && a.nextElementSibling && a.parentElement.contains(links[cur]))));
  };
  addEventListener("scroll", () => { if(!ticking){ ticking = true; requestAnimationFrame(spy); } }, {passive:true});
  spy();
}

// The sources panel: the pesukim, mishnayos and Gemara cited in the part of the
// entry on screen, those holding two of the cluster's words first. Narrow
// screens have no panel; a citation opens its text under the line instead.
function wirePesukim(){
  const data = document.getElementById("pesukim-data"), rail = document.querySelector(".prail");
  if(!data || !rail) return;
  const P = JSON.parse(data.textContent);
  const colorEl = document.getElementById("word-colors");
  const C = colorEl ? JSON.parse(colorEl.textContent) : {};
  const list = rail.querySelector(".prail-list"), filt = rail.querySelector(".prail-f");
  const cites = [...document.querySelectorAll(".entry a.cite")].filter(c => P[c.dataset.k]);
  const wide = matchMedia("(min-width:1360px)");
  const targets = [...document.querySelectorAll(".toc a")]
    .map(a => document.getElementById(a.getAttribute("href").slice(1))).filter(Boolean);
  cites.forEach(c => {
    c._r = -1;
    targets.forEach((t, i) => { if(t.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING) c._r = i; });
  });
  const esc = s => s.replace(/[&<>"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]));
  const lit = (k, on) => cites.forEach(c => { if(c.dataset.k === k) c.classList.toggle("lit", on); });
  // The whole text, always: a pasuk or mishnah in full, and for the Gemara the
  // segments that hold the entry's words, with "…" where the rest is left out.
  const verse = d => d.w.map((x, i, s) => (x[0] === "…" ? '<span class="pell">…</span>'
      : x[1] ? `<mark${x[1] in C ? ` class="w${C[x[1]]}"` : ""}>${esc(x[0])}</mark>` : esc(x[0]))
    + (i < s.length - 1 && !x[0].endsWith("־") ? " " : "")).join("");
  const card = k => {
    const d = P[k], div = document.createElement("div");
    div.className = "pcard";
    div.dataset.k = k;
    const tog = d.t.length ? `<span class="ptog"><bdi lang="he">${esc(d.t.join(" + "))}</bdi> together</span>` : "";
    div.innerHTML = d.u
      ? `<div class="pref"><span>${esc(d.l)}</span></div><a class="plink" href="${esc(d.u)}" target="_blank" rel="noopener">Open on Sefaria ↗</a>`
      : `<div class="pref"><span>${esc(d.l)}</span>${tog}</div><div class="pv" dir="rtl" lang="he">${verse(d)}</div>`;
    div.addEventListener("mouseenter", () => lit(k, true));
    div.addEventListener("mouseleave", () => lit(k, false));
    return div;
  };
  let shown = null, filter = "";
  const render = (r, active) => {
    const keys = [...new Set(cites.filter(c => c._r === r).map(c => c.dataset.k))];
    // Two of the words together first, texts next, Sefaria links last.
    const rank = k => (P[k].t.length ? 2 : 0) + (P[k].u ? 0 : 1);
    keys.sort((x, y) => rank(y) - rank(x));
    // At most six filter words, the ones marked in the most pesukim here.
    const count = {};
    keys.forEach(k => new Set(P[k].w.filter(x => x[1]).map(x => x[1])).forEach(h => { count[h] = (count[h] || 0) + 1; }));
    const heads = Object.keys(count).sort((x, y) => count[y] - count[x]).slice(0, 6);
    if(!heads.includes(filter)) filter = "";
    filt.innerHTML = "";
    filt.hidden = !(keys.length > 5 && heads.length > 1);
    if(!filt.hidden) heads.forEach(h => {
      const b = document.createElement("button");
      b.type = "button"; b.lang = "he"; b.textContent = h;
      b.classList.toggle("on", h === filter);
      b.addEventListener("click", () => { filter = filter === h ? "" : h; render(r, active); });
      filt.appendChild(b);
    });
    list.innerHTML = "";
    const vis = keys.filter(k => !filter || P[k].w.some(x => x[1] === filter));
    if(!vis.length) list.innerHTML = '<p class="prail-none">No pesukim are cited in this part of the entry.</p>';
    vis.forEach(k => { const c = card(k); if(k === active) c.classList.add("on"); list.appendChild(c); });
    shown = r;
  };
  const current = () => {
    let cur = -1;
    targets.forEach((t, i) => { if(t.getBoundingClientRect().top < 110) cur = i; });
    // Before the first section is reached, show the first part that cites anything.
    return cur < 0 && cites.length ? cites[0]._r : cur;
  };
  let ticking = false;
  const onScroll = () => {
    ticking = false;
    if(!wide.matches) return;
    const r = current();
    if(r !== shown) render(r);
  };
  addEventListener("scroll", () => { if(!ticking){ ticking = true; requestAnimationFrame(onScroll); } }, {passive:true});
  wide.addEventListener("change", onScroll);
  cites.forEach(c => c.addEventListener("click", ev => {
    ev.preventDefault();
    const k = c.dataset.k;
    if(wide.matches){
      render(c._r, k);
      const on = list.querySelector(".pcard.on");
      if(on) on.scrollIntoView({block:"nearest"});
      return;
    }
    const host = c.closest("li, p") || c.parentElement;
    const inside = host.tagName === "LI";
    const open = inside ? host.querySelector(":scope > .ppop")
      : (host.nextElementSibling && host.nextElementSibling.classList.contains("ppop") ? host.nextElementSibling : null);
    if(open){
      const same = open.dataset.k === k;
      open.remove();
      c.setAttribute("aria-expanded", "false");
      if(same) return;
    }
    const pop = document.createElement("div");
    pop.className = "ppop"; pop.dataset.k = k;
    pop.appendChild(card(k));
    const x = document.createElement("button");
    x.type = "button"; x.className = "pclose"; x.textContent = "×"; x.setAttribute("aria-label", "Close");
    x.addEventListener("click", () => { pop.remove(); c.setAttribute("aria-expanded", "false"); });
    pop.querySelector(".pref").appendChild(x);
    inside ? host.appendChild(pop) : host.after(pop);
    c.setAttribute("aria-expanded", "true");
  }));
  onScroll();
}

// Home: this week's line, by the reader's date (a week starts on Sunday). The
// build writes the week it was built in; a page cached across a Sunday updates here.
let weekPicks = [];         // this week's entries, in a fresh order each visit
let weekShown = new Set();  // the three already in the line, so nothing repeats below
function shuffled(list){
  const a = list.slice();
  for(let i = a.length - 1; i > 0; i--){ const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
function wireWeek(){
  const el = document.getElementById("week"), data = document.getElementById("week-data");
  if(!el || !data) return;
  try{
    const D = JSON.parse(data.textContent);
    const d = new Date(); d.setDate(d.getDate() - d.getDay());
    const pad = n => String(n).padStart(2, "0");
    const key = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    const w = D.w.find(x => x[0] === key);
    if(!w){ el.hidden = true; return; }
    // One from the Yom Tov, one from the parsha, one from the season, and on
    // round again; each group shuffled, so a second visit brings another three.
    const lists = w[2].map(g => shuffled(D.g[g] || []));
    while(weekPicks.length < 8 && lists.some(l => l.length)){
      for(const l of lists){
        while(l.length && weekPicks.includes(l[0])) l.shift();
        if(l.length && weekPicks.length < 8) weekPicks.push(l.shift());
      }
    }
    weekShown = new Set(weekPicks.slice(0, 3));
    const esc = s => s.replace(/[&<>"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]));
    el.innerHTML = `<span class="week-h">This week &middot; <b>${esc(w[1])}</b></span><span class="week-l">`
      + weekPicks.slice(0, 3).map(s => `<a href="entries/${esc(s)}.html"><bdi lang="he">${esc(D.e[s][1])}</bdi>${esc(D.e[s][0])}`
          + `<span class="chev" aria-hidden="true">&rsaquo;</span></a>`).join("")
      + `</span>`;
    el.hidden = false;
  }catch(err){}
}

// Home: a different group for "Inside an entry" and four questions each visit;
// two of the questions come from this week's entries, after the three in its line.
function wireHome(){
  const tp = document.getElementById("taste-pool"), ap = document.getElementById("ask-pool");
  if(!tp || !ap) return;
  const taste = JSON.parse(tp.textContent), asks = JSON.parse(ap.textContent);
  const esc = s => s.replace(/[&<>"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]));
  const inLine = weekShown;
  const tastes = taste.filter(x => !inLine.has(x.s));
  const pick = tastes.length ? tastes[Math.floor(Math.random() * tastes.length)] : null;
  if(pick){
    document.getElementById("taste").innerHTML =
      `<a class="taste-go" href="entries/${esc(pick.s)}.html" aria-label="Read the ${esc(pick.c)} entry">`
      + `<p class="taste-q">${pick.q}<span class="chev" aria-hidden="true">&rsaquo;</span></p>${pick.cards}</a>`;
  }
  const open = asks.filter(a => (!pick || a.s !== pick.s) && !inLine.has(a.s));
  const seasonal = weekPicks.slice(3).map(s => open.find(a => a.s === s)).filter(Boolean).slice(0, 2);
  const rest = open.filter(a => !seasonal.includes(a));
  for(let i = rest.length - 1; i > 0; i--){ const j = Math.floor(Math.random() * (i + 1)); [rest[i], rest[j]] = [rest[j], rest[i]]; }
  // Keep one or two of the written questions in each set when there are any.
  const curated = rest.filter(a => !a.q.startsWith("What")), plain = rest.filter(a => a.q.startsWith("What"));
  const four = seasonal.concat(curated.slice(0, seasonal.length ? 1 : 2), plain).slice(0, 4);
  document.getElementById("asks").innerHTML = four.map(a =>
    `<a href="entries/${esc(a.s)}.html"><span>${a.q}</span><span class="chev" aria-hidden="true">&rsaquo;</span></a>`).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  wireWeek();
  wireHome();
  wire();
  wireTabs();
  wireToc();
  wirePesukim();
  tally();
  // Focus the home search without the browser scrolling the headline off-screen,
  // which is what plain autofocus does on a short viewport.
  const big = document.querySelector(".bigsearch #q");
  if(big && window.innerWidth > 700) big.focus({preventScroll:true});
});
"""

HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/data.json
  Cache-Control: public, max-age=3600
"""

if __name__ == "__main__":
    main()
