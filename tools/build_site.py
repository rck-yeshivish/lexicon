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
import re, sys, json, html, shutil, pathlib, unicodedata, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "entries"
OUT = ROOT / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "site")

NIKUD = re.compile("[֑-ׇ]")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")
ALEFBET = list("אבגדהוזחטיכלמנסעפצקרשת")


def strip_heb(s):
    """Fold a Hebrew string to its lookup key: no nikud, no final forms."""
    return NIKUD.sub("", unicodedata.normalize("NFC", s)).translate(FINALS).strip()


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
                fm[key] = val
    return fm


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
            cur = {mm.group(1): mm.group(2).strip()}
            continue
        mm = re.match(r"^\s+(\w+):\s*(.*)$", line)
        if mm and cur is not None:
            cur[mm.group(1)] = mm.group(2).strip()
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

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def md(text):
    """Render the narrow markdown subset the entries actually use."""
    out, i = [], 0
    lines = text.split("\n")
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:].strip())}</h3>")
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
                t.append("<tr>" + "".join(f'<td dir="auto">{inline(c)}</td>' for c in r) + "</tr>")
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
                items.append(" ".join(item))
            out.append("<ul>" + "".join(f'<li dir="auto">{inline(x)}</li>' for x in items) + "</ul>")
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
                items.append(" ".join(item))
            out.append("<ol>" + "".join(f'<li dir="auto">{inline(x)}</li>' for x in items) + "</ol>")
            continue
        para = [line]                                            # paragraph
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("|", "#")) \
                and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
            para.append(lines[i])
            i += 1
        out.append(f'<p dir="auto">{inline(" ".join(x.strip() for x in para))}</p>')
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
        for h in fm.get("hebrew", []):
            k = strip_heb(h)
            if not k or k in seen:
                continue
            seen.add(k)
            w = per.get(k, {})
            words.append({"h": k, "t": w.get("tr", ""), "e": w.get("en", ""),
                          "d": w.get("distinct", ""), "c": e["cluster"], "s": slug,
                          "g": e["english"]})
        for k, w in per.items():
            if k in seen:
                continue
            seen.add(k)
            words.append({"h": k, "t": w.get("tr", ""), "e": w.get("en", ""),
                          "d": w.get("distinct", ""), "c": e["cluster"], "s": slug,
                          "g": e["english"]})

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


# ------------------------------------------------------------------ page shells

def shell(title, body, *, depth=0, header_search=True, active="", extra_js=""):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="A Hebrew-to-English translation guide: one entry per synonym cluster, every distinction attributed to the authority who draws it.">
<link rel="stylesheet" href="{up}assets/app.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>א</text></svg>">
</head>
<body data-up="{up}">
<header class="site{'' if header_search else ' bare'}">
  <a class="brand" href="{up}index.html">Lexicon</a>
  {'<div class="hsearch"><input id="q" type="search" placeholder="Search Hebrew or English" autocomplete="off" spellcheck="false" dir="auto"><div id="ac" class="ac" hidden></div></div>' if header_search else ''}
  <nav class="seg">
    <a href="{up}hebrew.html" class="{'on' if active == 'he' else ''}">Hebrew</a>
    <a href="{up}english.html" class="{'on' if active == 'en' else ''}">English</a>
  </nav>
</header>
<main>
{body}
</main>
<footer>
  <p>Grounded only in Orthodox sources. Every distinction is attributed; where the authorities disagree, the entry names the views.</p>
  <p class="muted">Drawn from <em>What&rsquo;s in a Word?</em> by Rabbi Reuven Chaim Klein (Ohr Somayach). Each entry links to the essay it rests on.</p>
</footer>
<script src="{up}assets/app.js"></script>
{extra_js}
</body>
</html>
"""


def entry_page(e):
    # Lay the words out left to right in the same order as the At-a-glance table,
    # with each word marked RTL on its own. A single dir="rtl" block would be
    # correct Hebrew but would right-align the group away from the heading and
    # reverse it against the table beneath it.
    heb = " &middot; ".join(f'<span dir="rtl">{html.escape(h)}</span>' for h in e["hebrew"][:6])
    anchors = "".join(
        f'<span id="{html.escape(strip_heb(h))}"></span>' for h in e["hebrew"])
    parts = [f'''<article class="entry">
{anchors}
<p class="eyebrow">{html.escape(e["domain"])}{' &middot; draft' if e["status"] == "draft" else ''}</p>
<h1>{html.escape(e["cluster"])}</h1>
<p class="heb-title">{heb}</p>''']
    for headname, mdtext in e["sections"]:
        if headname == "Notes for a project" and mdtext.strip() in ("None yet.", ""):
            continue
        cls = {"Bottom line": "bottomline", "At a glance": "glance",
               "Where the authorities disagree": "disagree"}.get(headname, "")
        parts.append(f'<section class="{cls}"><h2>{html.escape(headname)}</h2>{md(mdtext)}</section>')
    parts.append("</article>")
    return shell(f'{e["cluster"]} — Lexicon', "\n".join(parts), depth=1, active="")


# ------------------------------------------------------------------------ build

def main():
    entries, words, english = collect()
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

    words.sort(key=lambda w: (w["h"], w["c"]))
    english.sort(key=lambda x: (x["e"].lower(), x["c"]))
    data = {
        "built": datetime.date.today().isoformat(),
        "counts": {"entries": len(entries), "words": len(words), "english": len(english)},
        "words": words,
        "english": english,
    }
    emit("data.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    for e in entries:
        emit(f'entries/{e["slug"]}.html', entry_page(e))

    n_words, n_entries = len(words), len(entries)
    home = f'''<section class="hero">
  <h1>Which English word does it take?</h1>
  <p class="lede">{n_words:,} Hebrew headwords across {n_entries} clusters of near-synonyms.
  Each entry gives every word its own English and attributes the distinction to the
  authority who draws it.</p>
  <div class="bigsearch">
    <svg viewBox="0 0 24 24" class="mag" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
    <input id="q" type="search" placeholder="Type Hebrew or English&hellip;" autocomplete="off" spellcheck="false" dir="auto">
    <div id="ac" class="ac" hidden></div>
  </div>
  <p class="hint">Try <button class="chip" data-q="בושה">בושה</button>
    <button class="chip" data-q="chochmah">chochmah</button>
    <button class="chip" data-q="humiliation">humiliation</button></p>
</section>
<section class="split">
  <a class="card" href="hebrew.html"><h3>Browse Hebrew</h3><p>Alef to tuf, every headword in order.</p></a>
  <a class="card" href="english.html"><h3>Browse English</h3><p>A to Z, from the English back to the Hebrew.</p></a>
</section>'''
    emit("index.html", shell("Lexicon — Hebrew to English, precisely", home, header_search=False))

    letters = "".join(f'<button class="ltr" data-l="{l}">{l}</button>' for l in ALEFBET)
    he_body = f'''<section class="browse">
  <h1>Hebrew</h1>
  <p class="lede">Alef to tuf. Pick a letter.</p>
  <div class="letters heb">{letters}</div>
  <div id="list" class="rows"></div>
</section>'''
    emit("hebrew.html", shell("Hebrew — Lexicon", he_body, active="he",
                              extra_js='<script>initBrowse("he");</script>'))

    en_letters = "".join(f'<button class="ltr" data-l="{c}">{c}</button>'
                         for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    en_body = f'''<section class="browse">
  <h1>English</h1>
  <p class="lede">A to Z, from the English rendering back to the Hebrew it translates.</p>
  <div class="letters">{en_letters}</div>
  <div id="list" class="rows"></div>
</section>'''
    emit("english.html", shell("English — Lexicon", en_body, active="en",
                               extra_js='<script>initBrowse("en");</script>'))

    emit("assets/app.css", CSS)
    emit("assets/app.js", JS)
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
  --radius:14px; --heb:"SF Hebrew","Noto Sans Hebrew","Arial Hebrew","Times New Roman",serif;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#000; --panel:#1c1c1e; --ink:#f5f5f7; --dim:#a1a1a6; --faint:#8a8a8e;
  --line:#2c2c2e; --accent:#409cff; --accent-soft:#12243c; --shadow:0 1px 3px rgba(0,0,0,.5);
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
.brand{font-weight:600;letter-spacing:-.01em;color:var(--ink);font-size:16px;flex:0 0 auto}
.hsearch{flex:1 1 auto;position:relative;max-width:520px;margin:0 auto}
.hsearch input{width:100%;height:36px;padding:0 14px;border:1px solid var(--line);
  border-radius:10px;background:var(--panel);color:var(--ink);font-size:15px;outline:none}
.hsearch input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
header.bare .brand{flex:1}
.seg{display:flex;gap:2px;padding:2px;background:var(--line);border-radius:9px;flex:0 0 auto}
.seg a{padding:5px 13px;border-radius:7px;font-size:14px;color:var(--dim);font-weight:500}
.seg a:hover{text-decoration:none;color:var(--ink)}
.seg a.on{background:var(--panel);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}

/* home -------------------------------------------------------------------- */
.hero{padding:86px 0 30px;text-align:center}
.hero h1{font-size:44px;line-height:1.08;letter-spacing:-.022em;font-weight:600;margin:0 0 14px}
.lede{color:var(--dim);font-size:19px;max-width:620px;margin:0 auto 34px}
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
@media (max-width:640px){.split{grid-template-columns:1fr}.hero h1{font-size:33px}.hero{padding:52px 0 20px}}
.card{display:block;padding:24px;border:1px solid var(--line);border-radius:var(--radius);
  background:var(--panel);color:var(--ink);transition:transform .15s,box-shadow .15s}
.card:hover{text-decoration:none;transform:translateY(-2px);box-shadow:var(--shadow)}
.card h3{margin:0 0 6px;font-size:18px;font-weight:600}
.card p{margin:0;color:var(--dim);font-size:15px}

/* autocomplete ------------------------------------------------------------ */
.ac{position:absolute;left:0;right:0;top:calc(100% + 8px);background:var(--panel);
  border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);
  overflow:hidden;text-align:left;max-height:60vh;overflow-y:auto;z-index:60}
.ac .row{display:flex;align-items:baseline;gap:12px;padding:11px 16px;cursor:pointer;
  border-bottom:1px solid var(--line);color:var(--ink)}
.ac .row:hover{text-decoration:none}
.ac .row:last-child{border-bottom:0}
.ac .row:hover,.ac .row.sel{background:var(--accent-soft)}
.ac .h{font-family:var(--heb);font-size:20px;min-width:88px;direction:rtl;text-align:right}
.ac .t{color:var(--dim);font-size:14px;font-style:italic;min-width:96px}
.ac .e{font-weight:500;flex:1}
.ac .c{color:var(--faint);font-size:13px}
.ac .none{padding:16px;color:var(--dim);font-size:15px}

/* browse ------------------------------------------------------------------ */
.browse{padding:46px 0 0}
.browse h1{font-size:36px;letter-spacing:-.02em;font-weight:600;margin:0 0 8px}
.letters{display:flex;flex-wrap:wrap;gap:7px;margin:26px 0 30px;
  padding-bottom:22px;border-bottom:1px solid var(--line)}
.ltr{min-width:44px;height:44px;padding:0 8px;border:1px solid var(--line);background:var(--panel);
  color:var(--ink);border-radius:11px;font:inherit;font-size:17px;cursor:pointer;
  transition:background .12s,border-color .12s}
.letters.heb .ltr{font-family:var(--heb);font-size:22px}
.ltr:hover{border-color:var(--dim)}
.ltr.on{background:var(--accent);border-color:var(--accent);color:#fff}
.ltr[disabled]{opacity:.3;cursor:default}
.rows{display:flex;flex-direction:column}
.rows .r{display:grid;grid-template-columns:120px 130px 1fr;gap:16px;align-items:baseline;
  padding:14px 6px;border-bottom:1px solid var(--line)}
.rows .r{color:var(--ink)}
.rows .r:hover{background:var(--panel);text-decoration:none}
.rows .h{font-family:var(--heb);font-size:24px;direction:rtl;text-align:right}
.rows .en{font-family:inherit;font-size:19px;font-weight:600;direction:ltr;text-align:left}
.rows .t{color:var(--dim);font-style:italic;font-size:15px}
.rows .e{font-weight:500}
.rows .d{color:var(--dim);font-size:15px;display:block;margin-top:2px}
.rows .cl{color:var(--faint);font-size:14px}
@media (max-width:700px){.rows .r{grid-template-columns:1fr;gap:2px}.rows .h{text-align:right}}
.count{color:var(--faint);font-size:14px;margin:0 0 14px}

/* entry ------------------------------------------------------------------- */
.entry{padding:44px 0 0;max-width:760px}
.eyebrow{color:var(--faint);font-size:13px;text-transform:uppercase;letter-spacing:.07em;margin:0 0 8px}
.entry h1{font-size:38px;letter-spacing:-.021em;font-weight:600;margin:0 0 6px;text-transform:capitalize}
.heb-title{font-family:var(--heb);font-size:29px;color:var(--dim);margin:0 0 30px;
  direction:ltr;text-align:left;display:flex;flex-wrap:wrap;gap:0 10px}
.entry section{margin:0 0 34px}
.entry h2{font-size:13px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);
  font-weight:600;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.entry h3{font-size:19px;font-weight:600;margin:24px 0 6px}
.entry p{margin:0 0 14px}
.entry li{margin:0 0 8px}
.bottomline{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 24px 8px;box-shadow:var(--shadow)}
.bottomline h2{border:0;padding:0}
.bottomline p{font-size:18px}
.disagree{border-left:3px solid var(--line);padding-left:20px}
.tablewrap{overflow-x:auto;margin:0 0 16px}
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

function search(q, limit=12){
  if(!DATA || !q.trim()) return [];
  const out = [];
  // Half a rank for carrying its own English: between two equally good string
  // matches, the word whose entry actually rules on it is the better answer.
  const own = w => (w.e ? 0 : 0.5);
  if(isHeb(q)){
    const k = foldHeb(q);
    for(const w of DATA.words){
      const i = w.h.indexOf(k);
      if(w.h === k) out.push([0 + own(w), w]);
      else if(i === 0) out.push([1 + own(w), w]);
      else if(i > 0) out.push([3 + own(w), w]);
    }
  } else {
    const k = foldLat(q);
    if(!k) return [];
    for(const w of DATA.words){
      const t = foldLat(w.t), e = foldLat(w.e), g = foldLat((w.g||[]).join(" "));
      if(t === k || e === k) out.push([0 + own(w), w]);
      else if(t.startsWith(k)) out.push([1 + own(w), w]);
      else if(e.startsWith(k)) out.push([2 + own(w), w]);
      else if(t.includes(k) || e.includes(k)) out.push([3 + own(w), w]);
      else if(g.includes(k)) out.push([4 + own(w), w]);
      else if(foldLat(w.c).includes(k)) out.push([5 + own(w), w]);
    }
  }
  out.sort((a,b) => a[0]-b[0] || a[1].h.localeCompare(b[1].h));
  const seen = new Set(), res = [];
  for(const [,w] of out){
    const id = w.h + "|" + w.s;
    if(seen.has(id)) continue;
    seen.add(id);
    res.push(w);
    if(res.length >= limit) break;
  }
  return res;
}

function href(w){ return UP + "entries/" + w.s + ".html#" + encodeURIComponent(w.h); }

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
    ac.innerHTML = list.map((w,i) =>
      `<a class="row${i===sel?" sel":""}" href="${href(w)}">
         <span class="h">${esc(w.h)}</span>
         <span class="t">${esc(w.t)}</span>
         <span class="e">${esc(w.e || (w.g||[]).slice(0,3).join(", "))}</span>
         <span class="c">${esc(w.c)}</span>
       </a>`).join("");
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
    if(ac.hidden) return;
    if(e.key === "ArrowDown" || e.key === "ArrowUp"){
      e.preventDefault();
      sel = Math.max(0, Math.min(rows.length-1, sel + (e.key === "ArrowDown" ? 1 : -1)));
      [...ac.children].forEach((c,i) => c.classList.toggle("sel", i === sel));
      ac.children[sel]?.scrollIntoView({block:"nearest"});
    } else if(e.key === "Enter"){
      if(sel >= 0 && rows[sel]){ e.preventDefault(); location.href = href(rows[sel]); }
    } else if(e.key === "Escape"){ close(); q.blur(); }
  });
  document.addEventListener("click", e => { if(!ac.contains(e.target) && e.target !== q) close(); });
  document.querySelectorAll(".chip").forEach(b =>
    b.addEventListener("click", () => { q.value = b.dataset.q; q.focus(); run(); }));
}

function initBrowse(mode){
  const list = document.getElementById("list");
  const btns = [...document.querySelectorAll(".ltr")];
  // The buttons do nothing until data.json is in; say so rather than look broken.
  list.innerHTML = '<p class="count">Loading&hellip;</p>';
  load().then(() => {
    const bucket = {};
    if(mode === "he"){
      for(const w of DATA.words) (bucket[w.h[0]] ||= []).push(w);
    } else {
      for(const x of DATA.english){
        const c = (x.e[0]||"").toUpperCase();
        if(c >= "A" && c <= "Z") (bucket[c] ||= []).push(x);
      }
    }
    btns.forEach(b => { if(!(bucket[b.dataset.l]||[]).length) b.disabled = true; });
    const show = l => {
      btns.forEach(b => b.classList.toggle("on", b.dataset.l === l));
      const items = bucket[l] || [];
      const rows = items.map(w => mode === "he"
        ? `<a class="r" href="${href(w)}">
             <span class="h">${esc(w.h)}</span>
             <span class="t">${esc(w.t)}</span>
             <span>
               ${w.e ? `<span class="e">${esc(w.e)}</span>` :
                       `<span class="cl">in the ${esc(w.c)} cluster: ${esc((w.g||[]).slice(0,4).join(", "))}</span>`}
               ${w.d ? `<span class="d">${esc(w.d)}</span>` : ""}
             </span></a>`
        : `<a class="r" href="${UP}entries/${w.s}.html${w.h ? "#" + encodeURIComponent(w.h) : ""}">
             <span class="en">${esc(w.e)}</span>
             <span class="h">${esc(w.h)}</span>
             <span class="cl">${esc(w.c)}</span></a>`).join("");
      list.innerHTML = `<p class="count">${items.length} ${items.length === 1 ? "word" : "words"}</p>` + rows;
      history.replaceState(null, "", "#" + encodeURIComponent(l));
    };
    btns.forEach(b => b.addEventListener("click", () => show(b.dataset.l)));
    const want = decodeURIComponent(location.hash.slice(1));
    show(btns.some(b => b.dataset.l === want && !b.disabled)
         ? want : (btns.find(b => !b.disabled)?.dataset.l));
  });
}
window.initBrowse = initBrowse;
document.addEventListener("DOMContentLoaded", () => {
  wire();
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
