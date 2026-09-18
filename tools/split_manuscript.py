#!/usr/bin/env python3
"""Split Rabbi Klein's book manuscript into one Markdown file per essay.

WTDBAW.docx is the column gathered by parsha. Its outline carries the shape:
a level one heading is a sefer or a moed, level two is the parsha, level three
is an essay, and level four is a section inside an essay, which is what a
multi-part column looks like once the parts are joined.

Word stores those levels two ways, and the manuscript uses both: a Heading
style on some paragraphs, a direct outlineLvl on the rest. Reading only the
styles finds 122 of the 346 essays, so both are read here.

Footnotes are kept with the essay that cites them, numbered as Word numbers
them. The last footnote of most essays is the Hebrew list of everything the
essay quotes; it is pulled out as `sources_note` as well, because that list is
the only place many of the citations are written down.

    python tools/split_manuscript.py [docx] [--out DIR] [--quiet]

Writes `<out>/chapters/NNN-slug.md` and `<out>/chapters.json`, sweeping stale
chapter files rather than deleting the tree, the way build_site.py does, since
a OneDrive-synced folder holds directory handles.
"""
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / 'sources' / 'klein-book-manuscript'

# A footnote counts as his Hebrew source list when this much of its letters are
# Hebrew. The lists are Hebrew throughout apart from the odd English aside.
HEBREW_SHARE = 0.5


def _runs(p):
    """(italic, text) for each run of a paragraph, in document order."""
    for r in p.iter(W + 'r'):
        rPr = r.find(W + 'rPr')
        italic = rPr is not None and rPr.find(W + 'i') is not None
        out = []
        for node in r:
            tag = node.tag
            if tag == W + 't':
                out.append(node.text or '')
            elif tag == W + 'tab':
                out.append('\t')
            elif tag == W + 'br':
                out.append('\n')
            elif tag == W + 'footnoteReference':
                out.append('[^%s]' % node.get(W + 'id'))
        if out:
            yield italic, ''.join(out)


def para_text(p):
    """Paragraph text, with italic runs marked the Markdown way."""
    merged = []
    for italic, text in _runs(p):
        if merged and merged[-1][0] == italic:
            merged[-1][1] += text
        else:
            merged.append([italic, text])
    out = []
    for italic, text in merged:
        if not italic or not text.strip():
            out.append(text)
            continue
        # Emphasis markers have to sit against the words, not the spaces.
        lead = text[:len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        out.append('%s*%s*%s' % (lead, text.strip(), trail))
    return ''.join(out)


def para_level(p):
    """Heading level 1 to 4, or None for body text."""
    pPr = p.find(W + 'pPr')
    if pPr is None:
        return None
    style = pPr.find(W + 'pStyle')
    if style is not None:
        m = re.fullmatch(r'Heading(\d)', style.get(W + 'val') or '')
        if m:
            return int(m.group(1))
    outline = pPr.find(W + 'outlineLvl')
    if outline is not None:
        try:
            return int(outline.get(W + 'val')) + 1
        except (TypeError, ValueError):
            return None
    return None


def read_paragraphs(docx):
    root = ET.fromstring(zipfile.ZipFile(docx).read('word/document.xml'))
    body = root.find(W + 'body')
    for p in (body if body is not None else root).iter(W + 'p'):
        yield para_level(p), para_text(p)


def read_footnotes(docx):
    z = zipfile.ZipFile(docx)
    try:
        root = ET.fromstring(z.read('word/footnotes.xml'))
    except KeyError:
        return {}
    notes = {}
    for fn in root.iter(W + 'footnote'):
        parts = [para_text(p) for p in fn.iter(W + 'p')]
        text = re.sub(r'\s+', ' ', ' '.join(parts)).strip()
        if text:
            notes[fn.get(W + 'id')] = text
    return notes


def hebrew_share(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum('֐' <= c <= '׿' for c in letters) / len(letters)


def slugify(title):
    slug = re.sub(r"[’'](?=[a-z])", '', title.lower())
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return slug or 'untitled'


def split(docx):
    """Walk the outline into chapters."""
    notes = read_footnotes(docx)
    chapters = []
    section = parsha = ''
    current = None

    def start(title):
        nonlocal current
        current = {'title': title, 'section': section, 'parsha': parsha,
                   'lines': []}
        chapters.append(current)

    start('(front matter)')
    for level, text in read_paragraphs(docx):
        text = text.strip()
        if not text:
            continue
        if level == 1:
            section, parsha = text, ''
        elif level == 2:
            parsha = text
        elif level == 3:
            start(text)
            continue
        elif level == 4:
            current['lines'].append('## ' + text)
            continue
        else:
            current['lines'].append(text)
            continue
        # A level one or two heading closes nothing; it only renames where we
        # are, so the next essay picks up the new sefer or parsha.

    for n, ch in enumerate(chapters):
        body = '\n\n'.join(ch['lines'])
        cited = []
        for fid in re.findall(r'\[\^(\d+)\]', body):
            if fid in notes and fid not in cited:
                cited.append(fid)
        ch['n'] = n
        ch['file'] = '%03d-%s.md' % (n, slugify(ch['title']))
        ch['body'] = body
        ch['footnote_ids'] = cited
        ch['footnotes'] = {fid: notes[fid] for fid in cited}
        ch['words'] = len(body.split())
        # His source list is the last Hebrew footnote of the essay.
        ch['sources_note'] = ''
        for fid in reversed(cited):
            if hebrew_share(notes[fid]) >= HEBREW_SHARE:
                ch['sources_note'] = notes[fid]
                ch['sources_note_id'] = fid
                break
        del ch['lines']
    return chapters


def render(ch):
    out = ['# %s' % ch['title'], '']
    where = ' / '.join(x for x in (ch['section'], ch['parsha']) if x)
    if where:
        out += ['<!-- %s -->' % where, '']
    out.append(ch['body'])
    if ch['footnote_ids']:
        out += ['', '---', '']
        out += ['[^%s]: %s' % (fid, ch['footnotes'][fid])
                for fid in ch['footnote_ids']]
    return '\n'.join(out).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('docx', nargs='?', default=None,
                    help='the manuscript (default: the one in sources/)')
    ap.add_argument('--out', default=None,
                    help='where chapters/ and chapters.json go')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else DEFAULT_DIR
    docx = Path(args.docx) if args.docx else out_dir / 'WTDBAW.docx'
    if not docx.exists():
        sys.exit('no manuscript at %s' % docx)

    chapters = split(docx)
    ch_dir = out_dir / 'chapters'
    ch_dir.mkdir(parents=True, exist_ok=True)

    written = set()
    for ch in chapters:
        (ch_dir / ch['file']).write_text(render(ch), encoding='utf-8')
        written.add(ch['file'])
    stale = [p for p in ch_dir.glob('*.md') if p.name not in written]
    for p in stale:
        p.unlink()

    index = [{k: ch[k] for k in ('n', 'file', 'title', 'section', 'parsha',
                                 'words', 'sources_note')
              if k in ch} | {'footnotes': len(ch['footnote_ids'])}
             for ch in chapters]
    (out_dir / 'chapters.json').write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding='utf-8')

    if not args.quiet:
        essays = [c for c in chapters if c['n']]
        with_sources = sum(1 for c in essays if c['sources_note'])
        print('%d essays, %d with a Hebrew source list, %d stale files swept'
              % (len(essays), with_sources, len(stale)))


if __name__ == '__main__':
    main()
