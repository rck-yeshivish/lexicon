# Drafting brief for lexicon entries

Read this, `ENTRY-TEMPLATE.md`, and the exemplar
`entries/shame-bushah-klimah-cherpah.md` before writing. The exemplar sets the
texture, voice, and level of attribution; match it.

## The job

You are given a batch file. Each line is one assignment:

```
<article id(s)>	<title>	<terms the article italicises>
```

Several ids joined by `+` are parts of one series: read them all and write
**one** entry covering the cluster, listing every article in `sources:`.

For each line:

1. Read `sources/whats-in-a-word/raw/<id>-*.md` in full.
2. Decide the cluster: the two to six Hebrew words the piece actually
   distinguishes. The title and the terms column are hints, not the answer;
   the article often treats a different or narrower set.
3. Write `entries/<english-cluster>-<translit>-<translit>.md` with the Write
   tool, following the template exactly. Lowercase, hyphens, no apostrophes.
4. **Check the filename is not taken** (`ls entries/`). Never overwrite an
   existing entry. If the natural name is taken by a different cluster, add a
   distinguishing word (`fear-pachad-eimah.md` beside `fear-yirah-daagah.md`).


## Before you write the distinction

Read `references/how-synonyms-differ.md` once. It lists the eight ways apparent
synonyms actually differ, drawn from Rabbi Klein's own account of the method:
general and specific, the same thing seen from different sides, stronger and
weaker, the act and what it leaves behind, different settings, the speaker's
attitude, words from another language, and an old word replaced by a newer one.

Ask which one is at work before writing. It keeps a distinction from being
invented where the real answer is one of these, and it gives the reader the
shape of the answer as well as the answer. Name it in the prose in ordinary
words: *the general term against three specific kinds*, *the act against what it
leaves behind*, *Hebrew against Aramaic*. Where the true account is that one
word replaced another, say so rather than manufacture a difference. If none
fits and no authority draws the line, say the sources do not separate the
words. That is a finding.

## Hard rules

- **Front matter complete.** `hebrew` (unpointed, correctly spelled),
  `roots` (letters with hyphens), `translit` (every plausible form, Ashkenazi
  and Sephardi: *daas* and *daat*, *shabbos* and *shabbat*), `english` (the
  glosses your Bottom line uses), `domain` (one of: emotion, cognition, speech,
  body, action, nature, ritual, society, time, quantity, other), `sources` in
  exactly this shape, one line per article:
  `  - wiaw:<id> "<title>" (<yyyy-mm-dd>) https://articles.ohr.edu/articles/<slug>`
  taking id, title, date, and slug from the raw file's own front matter;
  `authorities` (names as the article gives them); `updated`.
- **The `words:` block.** One item per Hebrew word in the cluster,
  giving that word's own English and the one line that separates it from its
  neighbours, with the authority named. This is what makes the guide a lookup
  rather than an essay: it feeds the Hebrew headword table in `INDEX.md`, so
  somebody meeting the word cold gets the ruling without opening the file.
  Do not repeat the whole cluster's glosses against every word. Entries written
  before this block existed simply lack it, and are not being retrofitted; the
  index falls back to pointing at the entry for those words.
- **The "At a glance" table** repeats that block in the body, so a reader
  scanning the entry sees the contrast in one view before the prose.
- **"Where the authorities disagree" is mandatory whenever they do.** Name each
  view and its holder, then say which one the Bottom line follows and why. A
  dispute smoothed into a single answer is the main way this guide can mislead.
  Delete the heading only when the sources genuinely agree.
- **Bottom line first**, two to five lines: the rendering for each word and the
  one thing a translator must not get wrong. A model must be able to stop there.
- **Attribute every distinction** to the authority the article names (Radak,
  Malbim, Rabbi Shlomo Pappenheim, Rav Hirsch, Rabbi Avraham Bedersi, and so
  on). Where they disagree, list the views; the Bottom line picks the majority
  or most useful reading and says which. **Never invent** a source, a
  distinction, or an authority the article does not give.
- **Report what the article cites, whatever its provenance.** The article is
  the conduit, not the authority. If Rabbi Klein brings Gesenius, an Akkadian
  or Ugaritic cognate, a Greek or Latin etymology, or a named academic, that
  material belongs in the entry, attributed the way he attributes it. He vetted
  it by citing it, and an entry that silently drops it misreports his essay.
  Say "the column notes" or name the scholar, exactly as he does.
- **What you may not do is bring in material of your own** from outside the
  article. The guide reports the essays; it does not supplement them from
  elsewhere. If you know something the article does not say, either leave it
  out or mark it plainly as ours.
- **Do not import a view only to reject it** when the article does not. Where
  the article records a view and rejects it, record both, since the rejection
  is part of what he wrote. Never repeat a slur against an authority while
  dropping the article's defence of him.
- **Notes for a project**: write `None yet.` unless you are told a project
  ruling. Do not invent one.
- **Sources** section: article title, date, raw path, and the primary loci the
  article cites. Where you find a citation error in the article, give the
  correct locus and note the article's form in parentheses.
- **No em dashes anywhere.** The raw articles are full of them; never copy one.
  Use commas, semicolons, parentheses, or recast.
- **No AI register**: no *delve*, *it's worth noting*, *underscores*,
  *navigate*, *leverage*, *journey*, *a testament to*, *nuanced*, *crucial*.
- **Frum register**, as a *talmid chacham* writes: *Chazal teach*, *the pasuk
  says*. Convert Anglicised book names: Bereishis, Shemos, Vayikra, Bamidbar,
  Devarim, Yehoshua, Shoftim, Shmuel, Melachim, Yeshayahu, Yirmiyahu,
  Yechezkel, Tehillim, Mishlei, Iyov, Koheles, Daniel, Divrei HaYamim, Esther.
  Rambam not Maimonides, Ramban not Nachmanides. Hashem, not G-d.
- **Do not narrate** (*the article says*, *the author explains*). State the
  distinction and attribute it: *Malbim: ...*. Referring to the article as a
  text is fine where it matters (*the article prints 33:8; the locus is 34:8*).
- **Rendering guidance** must give at least one trap: an English word that
  would absorb two of the Hebrew words, and what to do when they appear
  together in one pasuk or phrase.

## Length

Size the entry to the article. A thin piece with one authority and two words
takes 40 to 60 lines; a rich one takes up to 120.

**140 is the target, not 200.** The lint warns past 140 and fails only at 240,
because a cluster with five words and four live disputes genuinely needs the
room. That headroom is an exception, not an allowance: when the cap was raised
from 180 to 200, the next batch came back at 168 to 199 lines almost uniformly,
which is the budget becoming the target. Write the entry the cluster needs and
stop. Never pad, and never drop an attribution to hit a number either way.

## Do not

Run any build script (`build_index.py`, `build_catalogue.py`,
`check_entries.py`), or touch anything outside `entries/`. The caller lints and
rebuilds the index after the batch.
