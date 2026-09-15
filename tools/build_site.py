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
import re, sys, json, html, shutil, pathlib, unicodedata, datetime, hashlib

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
    <a class="meth {'on' if active == 'me' else ''}" href="{up}method.html">Methodology</a>
    <span class="seg">
      <a href="{up}hebrew.html" class="{'on' if active == 'he' else ''}">Hebrew</a>
      <a href="{up}english.html" class="{'on' if active == 'en' else ''}">English</a>
    </span>
  </nav>
</header>
<main>
{body}
</main>
<footer>
  <p>Every distinction is attributed; where the authorities disagree, the entry names the views.</p>
  <p class="muted">Built on <em>What&rsquo;s in a Word?</em> by Rabbi Reuven Chaim Klein, published by Ohr Somayach, and each entry links to the essay it rests on. This is an independent rendering guide: the entries are written here, and the site is not published by or affiliated with Ohr Somayach.</p>
</footer>
<script src="{up}assets/{ASSETS["js"]}"></script>
{extra_js}
</body>
</html>
"""


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
    for he, tr, en, d in rows[2:]:
        # Attributions in parentheses, "(Malbim)", sit a shade darker so the
        # authority behind each line can be picked out at a glance.
        dhtml = re.sub(r"\(([A-Z][^()]*)\)", r'(<span class="who">\1</span>)', inline(d))
        cards.append(f'<div class="wcard"><div class="wh" dir="rtl" lang="he">{inline(he)}</div>'
                     f'<div class="wmeta"><span class="we">{inline(en)}</span>'
                     f'<span class="wt">{inline(tr)}</span></div>'
                     f'<div class="wd">{dhtml}</div></div>')
    return '<div class="wcards">' + "".join(cards) + "</div>"


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
    parts = [f'''<article class="entry">
{anchors}
<p class="eyebrow">{html.escape(e["domain"])}</p>
<h1>{html.escape(e["cluster"])}</h1>
<p class="heb-title">{heb}</p>''']
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
            text = m.group(1)
            he = re.search(r"\(([^()]*[֐-׿][^()]*)\)\s*$", text)
            # Only "name (Hebrew)"; a heading naming two words keeps its text.
            if he and "(" not in text[:he.start()]:
                label = (f'<span class="th" dir="rtl" lang="he">{he.group(1)}</span>'
                         f'<span class="tt">{text[:he.start()].strip()}</span>')
            else:
                label = f'<span class="tt">{text}</span>'
            subs.append((f"d-{n}", label, re.sub(r"<[^>]+>", "", text)))
            return f'<h3 id="d-{n}">{text}</h3>'
        return re.sub(r"<h3>(.*?)</h3>", tag, block), subs

    # Where the entry has word cards they come first: they are the easiest thing
    # on the page to read, and the Bottom line mostly restates them. It follows
    # as a plain "In short" for what the cards do not carry (how the words
    # relate, and any dispute). The markdown keeps its order either way.
    has_cards = any(h == "At a glance" and glance_cards(m) for h, m in e["sections"])
    deferred = None
    for headname, mdtext in e["sections"]:
        if headname == "Notes for a project" and mdtext.strip() in ("None yet.", ""):
            continue
        if headname == "Bottom line" and has_cards:
            deferred = (f'<section class="inshort" id="s-in-short"><h2>In short</h2>{md(mdtext)}</section>',
                        ("s-in-short", "In short", []))
            continue
        if headname == "Sources" and XREF.get(e["slug"]):
            # Other entries that discuss the same word or root, so a reader can
            # follow a word from one essay to the next.
            items = "".join(
                f'<li><a href="{html.escape(s)}.html">{html.escape(c[:1].upper() + c[1:])}</a>'
                f'<span class="xw">{inline(w)}</span></li>'
                for c, s, w in XREF[e["slug"]])
            parts.append(f'<section class="xref" id="s-also"><h2>Also discussed in</h2><ul>{items}</ul></section>')
            toc.append(("s-also", "Also discussed in", []))
        cls = {"Bottom line": "bottomline", "At a glance": "glance",
               "Where the authorities disagree": "disagree"}.get(headname, "")
        i = sid(headname)
        if headname == "Rendering guidance":
            # Collapsed by default: most readers come to understand the words,
            # not to translate them, and this section is advice for the second
            # group. <details> needs no script, and a crawler or an LLM reading
            # the HTML still gets the full text.
            parts.append(f'<details class="guide" id="{i}"><summary><h2>{html.escape(headname)}</h2>'
                         f'<span class="guide-hint">For translators</span></summary>{md(mdtext)}</details>')
            toc.append((i, headname, []))
            continue
        if headname == "At a glance" and glance_cards(mdtext):
            parts.append(f'<section class="glance" id="{i}"><h2>At a glance</h2>{glance_cards(mdtext)}</section>')
            toc.append((i, headname, []))
            if deferred:
                parts.append(deferred[0])
                toc.append(deferred[1])
                deferred = None
            continue
        body, subs = md(mdtext), []
        if headname == "Distinctions":
            body, subs = distinction_ids(body)
        parts.append(f'<section class="{cls}" id="{i}"><h2>{html.escape(headname)}</h2>{body}</section>')
        toc.append((i, headname, subs))
    parts.append("</article>")
    links = []
    for i, name, subs in toc:
        sub = "".join(f'<li><a href="#{d}" title="{html.escape(plain, quote=True)}">{label}</a></li>'
                      for d, label, plain in subs)
        links.append(f'<li><a href="#{i}">{html.escape(name)}</a>'
                     + (f'<ul>{sub}</ul>' if sub else "") + "</li>")
    nav = (f'<nav class="toc" aria-label="On this page"><p class="toc-h">On this page</p>'
           f'<ul>{"".join(links)}</ul></nav>')
    page = f'<div class="entry-layout">{nav}\n' + "\n".join(parts) + "</div>"
    return shell(f'{e["cluster"]} — What’s in a Word?', page, depth=1, active="")


# ------------------------------------------------------------------------ build

def main():
    for kind, text in (("css", CSS), ("js", JS)):
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
        ASSETS[kind] = f"app.{h}.{kind}"

    entries, words, english = collect()
    clusters = {e["slug"]: e["cluster"] for e in entries}
    xref_file = ROOT / "xref.json"
    if xref_file.exists():
        for p in json.loads(xref_file.read_text(encoding="utf-8"))["pairs"]:
            if p["a"] in clusters and p["b"] in clusters:
                XREF.setdefault(p["a"], []).append((clusters[p["b"]], p["b"], p["word"]))
                XREF.setdefault(p["b"], []).append((clusters[p["a"]], p["a"], p["word"]))
        for v in XREF.values():
            v.sort(key=lambda x: x[0].lower())
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

    # "Try" examples: a Hebrew word, a transliteration and an English concept, each
    # from a different entry, chosen in the browser on every visit. The pool is a
    # few kilobytes inlined in the page, so the home page does not fetch data.json
    # just to fill three buttons, and the static three stay for anyone without
    # scripts. Only words with their own ruling go in, so every pick finds something.
    def strip_nikud(s):
        return "".join(ch for ch in s if not (0x0591 <= ord(ch) <= 0x05C7))
    heb_word = re.compile("[" + chr(0x05D0) + "-" + chr(0x05EA) + "]{2,6}")
    pool = {"h": {}, "t": {}, "e": {}}
    for w in words:
        if not w["d"]:
            continue
        if heb_word.fullmatch(w["k"]) and heb_word.fullmatch(strip_nikud(w["h"])):
            pool["h"].setdefault(w["s"], strip_nikud(w["h"]))
        if re.fullmatch("[a-z][a-z']{2,11}", w["t"] or ""):
            pool["t"].setdefault(w["s"], w["t"])
        if re.fullmatch("[a-z]{4,14}", w["e"] or ""):
            pool["e"].setdefault(w["s"], w["e"])
    try_pool = json.dumps({k: [[v, s] for s, v in d.items()] for k, d in pool.items()},
                          ensure_ascii=False, separators=(",", ":"))

    n_words, n_entries = len(words), len(entries)
    home = f'''<section class="hero">
  <div class="banner">
    <h1 class="wm">What&rsquo;s in a Word?</h1>
    <p class="wm-sub">Synonyms in the Hebrew Language</p>
    <p class="wm-by">By Rabbi Reuven Chaim Klein</p>
  </div>
  <p class="lede">Search in Hebrew or in English. <span class="tally" data-to="{n_words}">{n_words:,}</span> words in <span class="tally" data-to="{n_entries}">{n_entries}</span> groups of
  near-synonyms, each with its own meaning and the source that draws the line.</p>
  <div class="bigsearch">
    <svg viewBox="0 0 24 24" class="mag" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
    <input id="q" type="search" placeholder="Type Hebrew or English&hellip;" autocomplete="off" spellcheck="false" dir="auto">
    <div id="ac" class="ac" hidden></div>
  </div>
  <p class="hint">Try <button class="chip" lang="he" data-q="בושה">בושה</button>
    <button class="chip" data-q="chochmah">chochmah</button>
    <button class="chip" data-q="humiliation">humiliation</button></p>
  <script type="application/json" id="try-pool">{try_pool}</script>
</section>
<section class="split">
  <a class="card" href="hebrew.html"><h3>Browse Hebrew</h3><p class="he" dir="rtl" lang="he">א&#1523; ועד ת&#1523;</p></a>
  <a class="card" href="english.html"><h3>Browse English</h3><p>A to Z, from the English back to the Hebrew.</p></a>
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
        emit("method.html", shell("Methodology — What’s in a Word?",
                                  f'<article class="entry prose">{tabs}'
                                  f'<div class="pane" id="pane-summary">{md(body)}</div>'
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
  --bg:#fbfbfd; --panel:#fff; --ink:#1d1d1f; --dim:#6e6e73; --faint:#86868b;
  --line:#e3e3e6; --accent:#0066cc; --accent-soft:#e8f0fe; --shadow:0 1px 3px rgba(0,0,0,.06),0 8px 28px rgba(0,0,0,.05);
  --radius:14px; --heb:"Frank Ruhl Libre","SF Hebrew","Noto Sans Hebrew","Arial Hebrew","Times New Roman",serif;
  --brand:#14601f; --brand-sub:#2f6b3a;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#000; --panel:#1c1c1e; --ink:#f5f5f7; --dim:#a1a1a6; --faint:#8a8a8e;
  --line:#2c2c2e; --accent:#409cff; --accent-soft:#12243c; --shadow:0 1px 3px rgba(0,0,0,.5);
  --brand:#5fbf72; --brand-sub:#89c996;
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
header.site{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:18px;
  padding:11px 22px;background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);
  border-bottom:1px solid var(--line)}
.brand{font-weight:800;letter-spacing:-.015em;color:var(--brand);font-size:17px;flex:0 0 auto;
  white-space:nowrap}
.brand:hover{text-decoration:none;opacity:.75}
.hsearch{flex:1 1 auto;position:relative;max-width:520px;margin:0 auto}
.hsearch input{width:100%;height:36px;padding:0 14px;border:1px solid var(--line);
  border-radius:10px;background:var(--panel);color:var(--ink);font-size:15px;outline:none}
.hsearch input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
header.bare .brand{flex:1}
.navs{display:flex;align-items:center;gap:16px;flex:0 0 auto}
.seg{display:inline-flex;gap:2px;padding:2px;background:var(--line);border-radius:9px}
/* Quieter than the browse control: it is a different kind of page, not a third
   way of looking at the same list. */
.meth{color:var(--faint);font-size:14px;font-weight:500;white-space:nowrap}
.meth:hover{color:var(--ink);text-decoration:none}
.meth.on{color:var(--ink)}
.seg a{position:relative;padding:5px 14px;border-radius:7px;font-size:14px;color:var(--dim);font-weight:500}
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
  .brand{font-size:15px}
  .navs{gap:8px;margin-left:auto}
  .meth{font-size:13px;padding:6px 0}
  .seg a{padding:4px 9px;font-size:13px}
  .hsearch{order:3;flex:1 1 100%;max-width:none;margin:0}
  .hsearch input{height:34px}
}
@media (max-width:400px){
  header.site{gap:8px}
  .brand{font-size:14px;letter-spacing:-.02em}
  .navs{gap:6px}
  .meth{font-size:12.5px}
  .seg a{padding:4px 8px;font-size:12.5px}
}

/* home -------------------------------------------------------------------- */
.hero{padding:64px 0 30px;text-align:center}
.banner{margin:0 0 30px}
.wm{font-weight:800;color:var(--brand);font-size:52px;line-height:1.02;
  letter-spacing:-.025em;margin:0 0 6px}
.wm-sub{color:var(--brand-sub);font-size:20px;font-weight:600;margin:0 0 14px;
  letter-spacing:-.005em}
.wm-by{color:var(--ink);font-size:19px;margin:0;font-weight:400}
@media (max-width:640px){.wm{font-size:34px}.wm-sub{font-size:16px}.wm-by{font-size:16px}}
.hero h1{font-size:44px;line-height:1.08;letter-spacing:-.022em;font-weight:600;margin:0 0 14px}
.lede{color:var(--dim);font-size:17px;max-width:620px;margin:0 auto 30px}
.tally{font-variant-numeric:tabular-nums;display:inline-block;text-align:right;color:var(--ink);font-weight:500}
/* margin:0 here would drop the auto side-margins that centre the block, leaving the text centred inside a left-hugging box rather than on the page */
.browse .lede[lang="he"]{font-family:var(--heb);font-size:22px;margin:0 auto}
.bigsearch{position:relative;max-width:620px;margin:0 auto}
.bigsearch input{width:100%;height:60px;padding:0 22px 0 54px;font-size:19px;
  border:1px solid var(--line);border-radius:16px;background:var(--panel);color:var(--ink);
  box-shadow:var(--shadow);outline:none;transition:border-color .15s,box-shadow .15s}
.bigsearch input:focus{border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft),var(--shadow)}
.mag{position:absolute;left:20px;top:20px;width:20px;height:20px;fill:none;
  stroke:var(--faint);stroke-width:2;stroke-linecap:round;pointer-events:none}
.hint{margin-top:18px;color:var(--faint);font-size:14px}
.chip{border:1px solid var(--line);background:var(--panel);color:var(--dim);
  border-radius:999px;padding:4px 12px;font:inherit;font-size:14px;cursor:pointer;margin:0 3px}
.chip:hover{color:var(--ink);border-color:var(--dim)}
.split{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:56px}
@media (max-width:860px){.split{grid-template-columns:1fr}}
@media (max-width:640px){.hero h1{font-size:33px}.hero{padding:52px 0 20px}}
.card{display:block;padding:24px;border:1px solid var(--line);border-radius:var(--radius);
  background:var(--panel);color:var(--ink);transition:transform .15s,box-shadow .15s}
.card:hover{text-decoration:none;transform:translateY(-2px);box-shadow:var(--shadow)}
.card h3{margin:0 0 6px;font-size:18px;font-weight:600}
.card p{margin:0;color:var(--dim);font-size:15px}
.card p.he{font-family:var(--heb);font-size:19px;line-height:1.3;text-align:left}

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
.rows .r{display:grid;grid-template-columns:130px minmax(0,1fr) 20px;gap:18px;align-items:center;
  padding:15px 6px;border-bottom:1px solid var(--line)}
.rows.en3 .r{grid-template-columns:minmax(0,230px) minmax(0,130px) minmax(0,1fr) 20px}
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
.rows .h{font-family:var(--heb);font-size:24px;direction:rtl;text-align:left}
.rows .en{font-family:inherit;font-size:19px;font-weight:600;direction:ltr;text-align:left}
.rows .t{color:var(--dim);font-style:italic;font-size:15px}
.rows .e{font-weight:500}
.rows .d{color:var(--dim);font-size:15px;display:block;margin-top:2px}
.rows .cl{color:var(--faint);font-size:14px}
/* Phones: one tidy line per row, word then text then chevron, instead of the
   word stacked over its text with nothing to tap toward. The search dropdown
   drops its fixed transliteration column, which left a wide empty gap and
   squeezed the English to one word per line. */
@media (max-width:700px){
  .rows .r{grid-template-columns:88px minmax(0,1fr) 18px;gap:12px;padding:14px 4px}
  .rows .h{text-align:right}
  .rows.en3 .r{grid-template-columns:minmax(0,1fr) auto 18px;grid-template-areas:"en h go" "cl cl go";row-gap:2px}
  .rows.en3 .en{grid-area:en}.rows.en3 .h{grid-area:h}.rows.en3 .cl{grid-area:cl}.rows.en3 .go{grid-area:go}
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
.wcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.wcard{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px 16px}
.wh{font-family:var(--heb);font-size:34px;font-weight:500;line-height:1.15;text-align:right}
.wmeta{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:0 10px;
  margin:6px 0 10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.we{font-weight:600;font-size:16px}
.wt{font-style:italic;color:var(--dim);font-size:15px}
.wd{font-size:15px;line-height:1.5;color:var(--dim)}
.wd .who{color:var(--ink)}
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
  .toc .th{font-family:var(--heb);font-size:17px;color:var(--ink)}
  .toc a.on .th{color:var(--accent)}
  .toc .tt{overflow:hidden;text-overflow:ellipsis}
  .toc .th+.tt{font-size:12.5px;color:var(--faint);font-style:italic}
}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
@media (max-width:520px){.wcards{grid-template-columns:1fr}.wh{font-size:30px}.heb-title{font-size:26px;gap:0 22px}}
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
/* Hebrew inside English text (a gloss in a sentence, the Also-discussed roots,
   the Hebrew "Try" chip) takes the Hebrew face too, a touch larger, since a
   serif Hebrew set at the sans size reads small beside it. */
[lang="he"]{font-family:var(--heb)}
:not([lang="he"]) > bdi[lang="he"]{font-size:1.08em;line-height:1}
.disagree{border-left:3px solid var(--line);padding-left:20px}
.tablewrap{overflow-x:auto;margin:0 0 16px}
details.guide{margin:28px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
details.guide>summary{display:flex;align-items:baseline;gap:12px;padding:14px 2px;cursor:pointer;
  list-style:none;-webkit-user-select:none;user-select:none}
details.guide>summary::-webkit-details-marker{display:none}
details.guide>summary h2{margin:0;display:inline}
details.guide>summary::before{content:"";flex:0 0 auto;width:7px;height:7px;align-self:center;
  border-right:2px solid var(--faint);border-bottom:2px solid var(--faint);
  transform:rotate(-45deg);transition:transform .15s}
details.guide[open]>summary::before{transform:rotate(45deg)}
details.guide>summary:hover h2{color:var(--accent)}
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
    const group = w => SIBS()[w.s] || [];
    const heb = x => `<span dir="rtl" lang="he">${esc(x.n || x.h)}</span>`;
    const oneGroup = list.every(w => w.s === list[0].s);
    const cap = oneGroup
      ? `${group(list[0]).length} words in the ${esc(ent(list[0]).c)} group, each with its own shade`
      : "Each word has near-synonyms. Open one to see how they differ";
    ac.innerHTML = `<div class="ac-cap">${cap}</div>` + list.map((w,i) => {
      const E = ent(w), tr = w.t ? `<span class="tr">${esc(w.t)}</span>` : "";
      const others = group(w).filter(x => x.k !== w.k);
      if(i === 0){
        const teaser = w.d
          ? `<span class="d">${esc(w.d)}</span>`
          : `<span class="d">in the ${esc(E.c)} group: ${esc((E.g || []).slice(0,4).join(", "))}</span>`;
        const n = group(w).length;
        return `<a class="row top${i===sel?" sel":""}" href="${href(w)}">
         <span class="h">${esc(w.n || w.h)}</span>
         <span class="tx">
           <span class="top-line">${w.e ? `<span class="e">${esc(w.e)}</span>` : ""}${tr}</span>
           ${teaser}
           <span class="cta">See how the ${n > 1 ? n + " words" : "words"} differ <span aria-hidden="true">›</span></span>
         </span>
       </a>`;
      }
      const vs = others.length
        ? `vs. ${others.slice(0,3).map(heb).join(", ")}${others.length > 3 ? "…" : ""}`
        : `in the ${esc(E.c)} group`;
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
  // A click outside the search closes the list, but not a click on a "Try"
  // chip: the chip has just opened it, and the same click reaching here used to
  // close it again before the reader could see it.
  document.addEventListener("click", e => {
    if(!ac.contains(e.target) && e.target !== q && !e.target.closest(".chip")) close();
  });
  // Swap the three static examples for a fresh set on every visit: one Hebrew
  // word, one transliteration, one English concept, from three different entries.
  const pool = document.getElementById("try-pool");
  if(pool){
    try{
      const P = JSON.parse(pool.textContent), used = new Set();
      const chips = document.querySelectorAll(".hint .chip");
      const pick = list => {
        const ok = (list || []).filter(x => !used.has(x[1]));
        if(!ok.length) return null;
        const x = ok[Math.floor(Math.random() * ok.length)];
        used.add(x[1]);
        return x;
      };
      ["h", "t", "e"].forEach((k, i) => {
        const x = pick(P[k]);
        if(x && chips[i]){ chips[i].textContent = x[0]; chips[i].dataset.q = x[0]; }
      });
    }catch(err){}
  }
  document.querySelectorAll(".chip").forEach(b =>
    b.addEventListener("click", () => { q.value = b.dataset.q; q.focus(); run(); }));
}

function initBrowse(mode){
  // The rows are already in the HTML, so this only filters them. That is what
  // lets the page work with scripts off and gives a crawler real links.
  const list = document.getElementById("list");
  const rows = [...list.querySelectorAll(".r")];
  const btns = [...document.querySelectorAll(".ltr")];
  const count = document.getElementById("count");
  const have = new Set(rows.map(r => r.dataset.l));
  btns.forEach(b => { if(!have.has(b.dataset.l)) b.disabled = true; });

  const noun = mode === "en" ? "terms" : "words";
  const show = l => {
    btns.forEach(b => b.classList.toggle("on", b.dataset.l === l));
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

document.addEventListener("DOMContentLoaded", () => {
  wire();
  wireTabs();
  wireToc();
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
