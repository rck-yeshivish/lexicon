#!/usr/bin/env python3
"""Read the author's own Hebrew source list for each essay and tie it to entries.

Most essays end with a footnote listing, in Hebrew, everything the essay
quotes. The essays themselves often name a rabbi without saying where he wrote
it, so that footnote is the only place many citations are written down. Where a
source is missing from the list, the author's rule is that the place is obvious:
Kohut's *Aruch HaShalem*, Radak's *Sefer HaShorashim*, Rav Pappenheim's *Cheshek
Shlomo* on that root, or Rashi or Radak on that pasuk.

The lists use his own shorthand. `מהרשא"ו` is Rabbi Shlomo Aharon Wertheimer's
*Beiurei Shemos Nirdafim*, and what follows in parentheses is the entry there
that treats those words, which is why that one is worth expanding even though
nothing else in the list names him.

Only shorthand that is attested here is expanded, and the English is the
spelling the entries already use. Anything not in the table keeps its Hebrew,
because a guessed attribution is worse than an unexpanded one.

    python tools/klein_sources.py [--report] [--entry NAME]

Writes `references/klein-sources.json`, keyed by entry file.
"""
import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MS = ROOT / 'sources' / 'klein-book-manuscript'
OUT = ROOT / 'references' / 'klein-sources.json'

# Hebrew shorthand -> (work, author). An empty work means the shorthand names
# the author alone. Spellings follow the entries.
WORKS = {
    'חשק שלמה': ('Cheshek Shlomo', 'Rabbi Shlomo Pappenheim'),
    'ח"ש': ('Cheshek Shlomo', 'Rabbi Shlomo Pappenheim'),
    'יריעות שלמה': ('Yerios Shlomo', 'Rabbi Shlomo Pappenheim'),
    'י"ש': ('Yerios Shlomo', 'Rabbi Shlomo Pappenheim'),
    'ספר הכרמל': ('Sefer HaCarmel', 'Malbim'),
    'הכרמל': ('Sefer HaCarmel', 'Malbim'),
    'יאיר אור': ('Yair Ohr', 'Malbim'),
    'מלבי"ם': ('', 'Malbim'),
    'מהרשא"ו': ('Beiurei Shemos Nirdafim', 'Rabbi Shlomo Aharon Wertheimer'),
    'הכתב והקבלה': ('HaKsav VeHaKabbalah', 'Rabbi Yaakov Tzvi Mecklenburg'),
    'הכתב והקבלה': ('HaKsav VeHaKabbalah', 'Rabbi Yaakov Tzvi Mecklenburg'),
    'קסת הסופר': ('Keses HaSofer', 'Rabbi Aharon Marcus'),
    'רשר"ה': ('', 'Rav Hirsch'),
    'פירוש הרש"ר הירש': ('', 'Rav Hirsch'),
    'ביאור הגר"א': ('', 'the Vilna Gaon'),
    'אדרת אליהו': ('Aderes Eliyahu', 'the Vilna Gaon'),
    'אוצר נרדפים': ('Otzar Nirdafim', 'Rabbi Moshe Tedeschi-Ashkenazi'),
    'ספר התשבי': ('Sefer HaTishbi', 'Rabbi Eliyahu HaBachur'),
    'התשבי': ('Sefer HaTishbi', 'Rabbi Eliyahu HaBachur'),
    'מתורגמן': ('Meturgeman', 'Rabbi Eliyahu HaBachur'),
    'חותם תכנית': ('Chotam Tochnit', 'Rabbi Avraham Bedersi'),
    'חותם תוכנית': ('Chotam Tochnit', 'Rabbi Avraham Bedersi'),
    'הרכסים לבקעה': ('HaRechasim LeVik\'ah', 'Rabbi Yehuda Leib Shapira-Frankfurter'),
    'ערוך השלם': ('Aruch HaShalem', 'Dr. Alexander Kohut'),
    'רבינו בחיי': ('', 'Rabbeinu Bachya'),
    'רבינו אפרים': ('', 'Rabbeinu Efrayim'),
    'פירוש הרוקח עה"ת': ('Peirush HaRokeach', ''),
    'פ\' הרוקח עה"ת': ('Peirush HaRokeach', ''),
    'שד"ל': ('', 'Shadal'),
    'מהרש"א': ('', 'Maharsha'),
    'ספר השרשים לרד"ק': ('Sefer HaShorashim', 'Radak'),
    'אהל מועד': ('Ohel Moed', 'Rabbi Shlomo of Urbino'),
    'אהלי יהודה': ('Ohalei Yehuda', 'Rabbi Yehudah Aryeh of Carpentras'),
    'אבן עזרא': ('', 'Ibn Ezra'),
    'ספר הגלוי': ('Sefer HaGalui', 'Rabbi Yosef Kimchi'),
    'מושב זקנים': ('Moshav Zekeinim', ''),
    'העמק דבר': ('Haamek Davar', 'the Netziv'),
    'משך חכמה': ('Meshech Chochmah', 'Rabbi Meir Simcha of Dvinsk'),
    'מצודת ציון': ('Metzudas Tzion', ''),
    'תשובות דונש': ('Teshuvos Dunash', 'Dunash ben Labrat'),
    'רש"ר הירש': ('', 'Rav Hirsch'),
    'פירוש הרוקח': ('Peirush HaRokeach', ''),
    'פ\' רד"צ הופמן': ('', 'Rabbi Dovid Tzvi Hoffmann'),
    'בני יששכר': ('Bnei Yissaschar', 'Rabbi Tzvi Elimelech of Dinov'),
    'שדי חמד': ('Sdei Chemed', 'Rabbi Chaim Chizkiyahu Medini'),
    'שיחות הרב צבי יהודה': ('Sichos', 'Rabbi Tzvi Yehuda Kook'),
    # Read off his own essays: each of these is named in English, with its
    # author, in entries drawn from the very essays whose footnotes use the
    # shorthand. `אור חדש` is his Chumash citations and his לוח השרשים, which is
    # Rabbi Chelouche's; the one Esther locus is likelier Maharal's book of that
    # name, and is left for the author to say.
    'אור חדש': ('Ohr Chadash', 'Rabbi David Chaim Chelouche'),
    'מכתם לדוד': ('Michtam LeDavid', 'Rabbi David Chaim Chelouche'),
    'ברזילי': ('Barzilai', 'Rabbi Aharon Marcus'),
    'ברזילאי': ('Barzilai', 'Rabbi Aharon Marcus'),
    'תרגומנא': ('Targumna', 'Rabbi David Golumb'),
    'שרש ישע': ('Shoresh Yesha', 'Rabbi Yitzchak of Zeldin'),
    'מקרא ולשון': ('Mikra V\'Lashon', 'Rabbi Dr. Asher Weiser'),
    'לשון חכמים': ('Leshon Chachamim', 'Rabbi Shimon Yehuda Leib Goldblit'),
    'אמרי רש"ד': ('Imrei RaShaD', 'Rabbi Shimon Dov Ber Analak of Shidlitz'),
    'אמת ליעקב': ('Emes LeYaakov', 'Rabbi Yaakov Kamenetsky'),
    'גבעת שאול': ('Givas Shaul', 'Rabbi Shaul Mortera'),
    'מהר"יט צהלון': ('', 'Rabbi Yom Tov Tzahalon'),
    'אסף המזכיר': ('Asaf HaMazkir', 'Rabbi Meir Mazuz'),
    'חכמוני': ('Chachmoni', 'Rabbi Shabsai Donnolo'),
    'מלים ותולדותיהן': ("Milim V'Toldoteihen", 'Professor Edward Yechezkel Kutscher'),
    'כד הקמח': ('Kad HaKemach', 'Rabbeinu Bachaya'),
    # Ten of the thirteen essays whose footnote cites רדיפי מיא name Rabbi Yehuda
    # Leib Edel in the body and no work with him, and the book names him only
    # fifteen times all told. Its loci are all `ערך` and `שורש`, a lexicon by
    # root, which is what he wrote. The English of the title wants his word.
    'רדיפי מיא': ('Redifei Maya', 'Rabbi Yehuda Leib Edel'),
    'תורת האלהים': ('Toras HaElokim', ''),
    # His essay on excrement credits the zevel etymology to "Rabbi Tanchum the
    # Jerusalemite" and its footnote gives המדריך המספיק (ערך זבל) for it.
    'המדריך המספיק': ('HaMadrich HaMaspik', 'Rabbi Tanchum HaYerushalmi'),
    # Named from his own locus: the memorial Torah journal for Rav Kook.
    'אזכרה': ('Azkarah', ''),
}


def split_items(note):
    """Split a source note on top level commas, keeping parentheses whole."""
    note = re.sub(r'^\s*מקורות:\s*', '', note.strip())
    out, depth, cur = [], 0, ''
    for c in note:
        if c in '([':
            depth += 1
        elif c in ')]':
            depth = max(0, depth - 1)
        if c == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += c
    out.append(cur)
    return [x.strip(' .,;') for x in out if x.strip(' .,;')]


# His working notes to himself run in capitals at the end of a list.
ASIDE = re.compile(r'\b[A-Z][A-Z\'’\s,.!?]{6,}$')


def lookup_work(head):
    """Match a head to the table through his prefixes and his 'sefer' forms."""
    if head in WORKS:
        return WORKS[head]
    trimmed = re.sub(r'^(?:ספר|פירוש|פי\'|עי\'|ע\')\s+', '', head).strip()
    if trimmed in WORKS:
        return WORKS[trimmed]
    # A one letter prefix (in, to, and, like, from) glued to the title.
    if trimmed[:1] in 'בלוכמשה' and trimmed[1:] in WORKS:
        return WORKS[trimmed[1:]]
    # Otherwise a title sitting inside a longer phrase, long enough to be safe.
    for key, val in WORKS.items():
        if len(key) >= 6 and key in trimmed:
            return val
    return ('', '')


def parse_item(item):
    """-> {'raw', 'head', 'locus', 'work', 'author'}"""
    item = ASIDE.sub('', item).strip(' .,;')
    m = re.match(r'^(.*?)[\(\[](.*)[\)\]]\s*$', item, re.S)
    head = (m.group(1) if m else item).strip(' .,;')
    locus = (m.group(2) if m else '').strip(' .,;')
    work, author = lookup_work(head)
    out = {'raw': item, 'head': head, 'locus': locus,
           'work': work, 'author': author}
    # `ערך X` inside the parentheses names an entry in a dictionary or a
    # lexicon of synonyms, which is the locus for that kind of work.
    if locus:
        svs = [s.strip() for s in re.split(r'ערך\s*', locus) if s.strip()]
        if locus.startswith('ערך') and svs:
            out['sv'] = [p.strip(' ,.') for p in svs]
        elif head in WORKS and '/' in locus and ':' not in locus:
            out['sv'] = [p.strip() for p in locus.split('/') if p.strip()]
    return out


def english(item):
    """A readable English form, or '' when the shorthand is not in the table."""
    if not (item['work'] or item['author']):
        return ''
    bits = []
    if item['author']:
        bits.append(item['author'])
    if item['work']:
        bits.append('*%s*' % item['work'])
    text = ', '.join(bits)
    if item.get('sv'):
        text += ', s.v. ' + ', '.join(item['sv'])
    elif item['locus']:
        text += ' (%s)' % item['locus']
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--entry', help='print the list for one entry and stop')
    args = ap.parse_args()

    chapters = {c['n']: c for c in
                json.loads((MS / 'chapters.json').read_text(encoding='utf-8'))}
    mapping = json.loads((MS / 'chapter-essay-map.json').read_text(encoding='utf-8'))

    by_entry = OrderedDict()
    chapters_with, chapters_without = 0, []
    for row in mapping:
        note = chapters[row['n']].get('sources_note', '')
        if not note:
            chapters_without.append(row['title'])
            continue
        chapters_with += 1
        items = [parse_item(i) for i in split_items(note)]
        for it in items:
            it['english'] = english(it)
        block = {'chapter': row['file'], 'chapter_title': row['title'],
                 'note': note, 'items': items}
        for entry in row['entries']:
            by_entry.setdefault(entry, []).append(block)

    OUT.write_text(json.dumps(by_entry, ensure_ascii=False, indent=1),
                   encoding='utf-8')

    if args.entry:
        for block in by_entry.get(args.entry, []):
            print('== %s (%s)' % (block['chapter_title'], block['chapter']))
            for it in block['items']:
                print('   %-46s %s' % (it['raw'][:46], it['english'] or '-'))
        return

    if args.report:
        total = sum(len(b['items']) for bs in by_entry.values() for b in bs)
        named = sum(1 for bs in by_entry.values() for b in bs
                    for i in b['items'] if i['english'])
        print('%d chapters carry a source list, %d do not' %
              (chapters_with, len(chapters_without)))
        print('%d entries get a list; %d of %d items expand to English'
              % (len(by_entry), named, total))
        heads = {}
        for bs in by_entry.values():
            for b in bs:
                for i in b['items']:
                    if not i['english']:
                        heads[i['head']] = heads.get(i['head'], 0) + 1
        print('\n== shorthand not in the table, most cited first ==')
        for h, n in sorted(heads.items(), key=lambda kv: -kv[1])[:30]:
            print('  %3d  %s' % (n, h))


if __name__ == '__main__':
    main()
