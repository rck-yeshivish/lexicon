"""Split Rav Pappenheim's Cheshek Shlomo into its roots.
  python tools/split_cheshek.py

The source is sources/cheshek-shlomo/cheshek-shlomo.pdf: Sefer Cheshek Shlomo,
Shorashim, printed for the first time from his manuscript by Moshe Tzuriel
(Bnei Brak 5777), as hebrewbooks.org carries it. The pages are scans under an
OCR text layer, and the OCR is rough: it reads ח as ת or ה (התכמה for החכמה),
mangles voweled pesukim, and turns the small citation type into digits. So what
this writes is a map of the book, not its text:

  Each root opens with its letters in bold followed by a period (אב.), and the
  paragraphs after it open with bold lead words (ויקרא, והמכון). The headings are
  found from the bold font in the text layer, kept only where they run in the
  book's alphabetical order (a bold word inside an entry breaks the order and
  is dropped), and each root gets the PDF pages it spans.

  "ocr" carries the rough text for searching and for finding one's place. It
  is not to be quoted, shown or glossed from; the transcription made from the
  page images is.

The printed page number is the PDF page less two.
"""
import json, pathlib, re, subprocess

import pypdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
PDF = ROOT / "sources" / "cheshek-shlomo" / "cheshek-shlomo.pdf"
OUT = ROOT / "references" / "cheshek-shlomo.json"
FIRST, LAST = 18, 574          # PDF pages: אות א (printed 16) through the end of ת
OFFSET = 2                     # printed page = PDF page - OFFSET
HEAD = re.compile(r"[א-ת]{2,5}\.")
FOLD = str.maketrans("ךםןףץ", "כמנפצ")
# Root headings the bold-font search misses, each read on the page image: one
# set with a comma (כת,), one in regular type (אץ.), and two roots that share
# another's letters, keyed with a number (the particle בַּל, and שב of old age).
EXTRA = [(64, "אץ"), (77, "בב"), (96, "בל 2"), (291, "כת"), (532, "שב 2")]
BIDI = re.compile(r"[‎‏‪-‮]")
MIRROR = str.maketrans("()[]", ")(][")   # the RTL text layer stores brackets mirrored


def bold_heads(reader):
    """(pdf page, root) for every bold 'xx.' run, in reading order."""
    out = []
    for n in range(FIRST, LAST + 1):
        found = []

        def visit(text, cm, tm, font, size):
            name = str((font or {}).get("/BaseFont", ""))
            t = text.strip()
            if "Bold" in name and HEAD.fullmatch(t):
                found.append(t[:-1])

        reader.pages[n - 1].extract_text(visitor_text=visit)
        out += [(n, h) for h in found]
    return out


def in_order(heads):
    """The longest run of headings in strict alphabetical order. A stray bold word
    (כס on a page of א) falls outside it, and one stray cannot block the rest."""
    keys = [h.translate(FOLD) for _, h in heads]
    best, prev = [1] * len(keys), [-1] * len(keys)
    for i in range(len(keys)):
        for j in range(i):
            if keys[j] < keys[i] and best[j] + 1 > best[i]:
                best[i], prev[i] = best[j] + 1, j
    i = max(range(len(keys)), key=lambda k: best[k]) if keys else -1
    chain = []
    while i != -1:
        chain.append(heads[i])
        i = prev[i]
    return chain[::-1]


def page_text(n):
    t = subprocess.run(["pdftotext", "-enc", "UTF-8", "-f", str(n), "-l", str(n), str(PDF), "-"],
                       capture_output=True, check=True).stdout.decode("utf-8")
    t = BIDI.sub("", t).translate(MIRROR)
    lines = [l for l in t.splitlines() if l.strip()]
    # the running head (חשק שלמה - שרשים, often misread) and the page number
    lines = [l for l in lines if not re.fullmatch(r"\s*\d{1,3}\s*", l)
             and not re.fullmatch(r".{0,6}שלמה\s*-\s*שרשים.{0,6}", l.strip())
             and not re.fullmatch(r"אות \S{2,6}", l.strip())]
    return "\n".join(lines)


def main():
    reader = pypdf.PdfReader(str(PDF))
    raw = bold_heads(reader)
    heads = sorted(in_order(raw) + EXTRA, key=lambda x: (x[0], x[1].translate(FOLD)))
    pages = {n: page_text(n) for n in range(FIRST, LAST + 1)}
    roots, unplaced = {}, []
    for i, (n, h) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else LAST
        span = list(range(n, end + 1))
        text = "\n".join(f"[p. {p - OFFSET}]\n{pages[p]}" for p in span)
        m = re.search(r"(?m)^\s*" + re.escape(h.split()[0]) + r"\s*[.,]", text)
        if m:
            text = text[m.start():]
        else:
            unplaced.append(h)
        if i + 1 < len(heads):
            nh = heads[i + 1][1].split()[0]
            m2 = re.search(r"(?m)^\s*" + re.escape(nh) + r"\s*[.,]", text[1:])
            if m2:
                text = text[:m2.start() + 1]
        roots[h] = {"hw": h.split()[0], "pdf_pages": [span[0], span[-1]],
                    "pages": [span[0] - OFFSET, span[-1] - OFFSET], "ocr": text.strip()}
    # a rerun keeps what was made by hand from the page images
    old = json.loads(OUT.read_text(encoding="utf-8"))["roots"] if OUT.exists() else {}
    for k, r in roots.items():
        for f in ("text", "status"):
            if f in old.get(k, {}):
                r[f] = old[k][f]
    data = {"meta": {"work": "Rabbi Shlomo Pappenheim, Cheshek Shlomo (Shorashim)",
                     "edition": "First printing from the manuscript, ed. Moshe Tzuriel, Bnei Brak 5777",
                     "via": "hebrewbooks.org",
                     "source": "sources/cheshek-shlomo/cheshek-shlomo.pdf",
                     "pages": "printed page = PDF page - 2",
                     "ocr": "rough OCR from the PDF's text layer: a map of the book, not its text; not to be quoted or shown"},
            "roots": roots}
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8") + b"\n")
    spans = [r["pdf_pages"][1] - r["pdf_pages"][0] + 1 for r in roots.values()]
    print(f"{len(raw)} bold headings, {len(heads)} in order, {len(roots)} roots; "
          f"pages per root: median {sorted(spans)[len(spans) // 2]}, max {max(spans)}; "
          f"{len(unplaced)} not found in the text layer: {' '.join(unplaced[:20])}")


if __name__ == "__main__":
    main()
