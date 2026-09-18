#!/usr/bin/env python3
"""Match each manuscript chapter to the published essays and to our entries.

The manuscript is the column gathered by parsha, so a chapter is usually one
published essay, but a multi-part column was joined into a single chapter when
the book was assembled, and a chapter also carries whatever the author has
revised since. Titles alone do not settle it: the site retitles pieces and
prefixes the parsha. So the match is made on the text, by eight word shingles,
and a chapter claims an essay when enough of that essay's shingles are in it.

Entries name their essays already, in the `wiaw:` lines of their front matter,
so the entry side of the map needs no guessing.

    python tools/map_manuscript.py [--out FILE] [--report]

Writes `chapter-essay-map.json` beside the chapters. `--report` prints the
three things worth acting on: chapters that match no published essay (an essay
the corpus lacks), published essays no chapter matched, and essays no entry
draws on.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MS = ROOT / 'sources' / 'klein-book-manuscript'
RAW = ROOT / 'sources' / 'whats-in-a-word' / 'raw'
ENTRIES = ROOT / 'entries'

SHINGLE = 8
# An essay counts as carried by a chapter at this share of its shingles. The
# chapters run about 87% of the published text, and a rerun of another piece
# inside an essay can lend a few shingles, so the bar sits well below that.
CLAIM = 0.25


def words(text):
    text = re.sub(r'\[\^\d+\]', ' ', text)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return text.split()


def shingles(text):
    w = words(text)
    return {' '.join(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


def strip_front_matter(text):
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            return text[end + 4:]
    return text


def load_essays():
    essays = {}
    for p in sorted(RAW.glob('*.md')):
        eid = p.name.split('-', 1)[0]
        body = strip_front_matter(p.read_text(encoding='utf-8'))
        title = ''
        m = re.search(r'^title:\s*"?(.*?)"?\s*$',
                      p.read_text(encoding='utf-8'), re.M)
        if m:
            title = m.group(1)
        essays[eid] = {'id': eid, 'file': p.name, 'title': title,
                       'shingles': shingles(body)}
    return essays


def load_entry_essays():
    """essay id -> [entry file]"""
    by_essay = {}
    for p in sorted(ENTRIES.glob('*.md')):
        for eid in re.findall(r'^\s*-\s*wiaw:(\d+)', p.read_text(encoding='utf-8'), re.M):
            by_essay.setdefault(eid, []).append(p.name)
    return by_essay


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=str(MS / 'chapter-essay-map.json'))
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()

    chapters = json.loads((MS / 'chapters.json').read_text(encoding='utf-8'))
    essays = load_essays()
    by_essay = load_entry_essays()

    # shingle -> essay ids, so each chapter is read once rather than 374 times
    index = {}
    for eid, e in essays.items():
        for s in e['shingles']:
            index.setdefault(s, []).append(eid)

    rows, claimed = [], set()
    for ch in chapters:
        if ch['n'] == 0:
            continue
        body = strip_front_matter((MS / 'chapters' / ch['file']).read_text(encoding='utf-8'))
        hits = {}
        for s in shingles(body):
            for eid in index.get(s, ()):
                hits[eid] = hits.get(eid, 0) + 1
        matched = []
        for eid, n in sorted(hits.items(), key=lambda kv: -kv[1]):
            share = n / max(1, len(essays[eid]['shingles']))
            if share >= CLAIM:
                matched.append({'id': eid, 'title': essays[eid]['title'],
                                'share': round(share, 2),
                                'entries': by_essay.get(eid, [])})
                claimed.add(eid)
        rows.append({'n': ch['n'], 'file': ch['file'], 'title': ch['title'],
                     'section': ch['section'], 'parsha': ch['parsha'],
                     'words': ch['words'], 'essays': matched,
                     'entries': sorted({f for m in matched for f in m['entries']})})

    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                              encoding='utf-8')

    if args.report:
        no_essay = [r for r in rows if not r['essays']]
        no_entry = [r for r in rows if r['essays'] and not r['entries']]
        unclaimed = [e for eid, e in sorted(essays.items()) if eid not in claimed]
        print('%d chapters, %d matched an essay, %d of %d essays claimed\n'
              % (len(rows), len(rows) - len(no_essay), len(claimed), len(essays)))
        print('== chapters matching no published essay (%d) ==' % len(no_essay))
        for r in no_essay:
            print('  %-42s %5dw  %s / %s' % (r['title'][:42], r['words'],
                                             r['section'], r['parsha']))
        print('\n== chapters whose essays no entry uses (%d) ==' % len(no_entry))
        for r in no_entry:
            print('  %-42s %s' % (r['title'][:42],
                                  ', '.join(m['id'] for m in r['essays'])))
        print('\n== published essays no chapter matched (%d) ==' % len(unclaimed))
        for e in unclaimed:
            print('  %-8s %s' % (e['id'], e['title'][:60]))


if __name__ == '__main__':
    main()
