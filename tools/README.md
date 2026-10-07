# Tools

Two are routine. The rest earn their keep when the corpus changes.

## Run after every change to entries

- **`check_entries.py`** the lint gate: schema, required headings, source-line
  format, house voice (no em dashes, no AI register, no narration), length.
  Exit code 1 if any entry fails.
- **`build_index.py`** regenerates `INDEX.md`. The index goes stale the moment
  an entry changes, and a stale index is worse than none, because it sends a
  reader to a ruling that is no longer there.

## Run when the corpus grows

The column publishes weekly, so this path runs again whenever you want the new
pieces in:

- **`harvest_wiaw.py`** pulls the listing and any article not already local.
  Idempotent; `--refresh` re-downloads everything.
- **`repair_corpus.py --check`** immediately after a harvest. The source has
  served mangled Hebrew and truncated bodies before. `--fix-encoding` repairs
  the first locally; `--list-truncated` names the second, which only another
  copy of the article can fix.
- **`build_catalogue.py`** regenerates the source catalogue.
- **`coverage.py --groups`** what no entry draws on yet, series grouped.
- **`make_batches.py <dir> --size 11`** splits that into agent-sized batches.
  `--exclude <tsv>` holds back what a running agent already has.

## Run when the author sends a new manuscript

He revises the book as he goes, so a fresh `WTDBAW.docx` is the one place his
later corrections are written down. Drop it on the old one and run these three.

- **`split_manuscript.py`** writes `chapters/` and `chapters.json`. Then
  `git diff sources/klein-book-manuscript/chapters` is the list of what he
  changed, one correction at a time, which is what the entries then follow.
- **`map_manuscript.py --report`** rebuilds `chapter-essay-map.json` and names
  the three things worth acting on: chapters matching no published essay (an
  essay the corpus lacks), chapters whose essays no entry uses, and published
  essays no chapter matched.
- **`klein_sources.py --report`** rebuilds `references/klein-sources.json` from
  the Hebrew source footnote at the end of each essay, which is where his exact
  loci live. `--entry <file>` prints one entry's list. The report ends with the
  shorthand its table does not cover, most cited first; that list is the
  question to put to the author, since guessing an attribution is worse than
  leaving the Hebrew as it stands.

## Occasional

- **`cite_commentators.py`** after new entries land. A citation the entry gives
  as a commentator's opens his comment on the site, not the pasuk or the
  Gemara. The plain forms ("Rashi to Beitzah 4a") are found by pattern; the
  rest ("Rashi renders *bitzah* as *maresc* (to Yechezkel 47:11)") have to be
  read, and are judged once in `references/cite-commentators.json`. This lists
  the ones still to judge, each with its sentence; `--stale` lists judged rows
  an edit has orphaned. Run `fetch_pesukim.py` after adding rows, so the
  comments they name are on hand.
- **`lookup.py <term>`** searches entries then the raw corpus, by Hebrew
  (nikud stripped), transliteration, or English.
- **`find_dupes.py`** near-duplicate source articles (the column reruns pieces
  under new ids) and entries whose word lists overlap enough to merge.
- **`patch_truncated.py`** completes a truncated article from another copy and
  records the provenance in its front matter. Kept for the method as much as
  the use.

## The site

- **`build_site.py`** generates `site/` from the entries: home, Hebrew and
  English browse, one page per entry, and a single `data.json` the pages fetch
  once. Run it after `build_index.py`. It writes in place and sweeps stale
  files rather than deleting the tree, because a OneDrive-synced folder holds
  directory handles and `rmtree` fails part way through.
- **`trace_logo.py`** traces the two logo images in `brand/` (words beside
  the drawing for the header, words under it for the home page) into the SVGs,
  `favicon.ico` and `apple-touch-icon.png` beside them. Run it only when the
  logo changes, then `build_site.py`, which copies what it wrote and adds the
  green. It needs Pillow, OpenCV and `potracer`; the build needs none of them,
  which is why its output is committed. In the header version the drawing is
  scaled down to the height of the words (`MARK_TO_WORDS`), since at the
  image's own proportions the English came out about 13px tall.
- **`fetch_calendar.py [first] [last]`** saves the diaspora parshiyos and
  Yamim Tovim from Hebcal to `references/calendar.json`. It covers four years
  by default; run it again before they run out.
- **`build_seasons.py [--sample]`** writes `references/seasons.json`, the home
  page's "This week" line: which entries go with each parsha and Yom Tov
  (following Rabbi Klein's book, with its `ADJUST` list for the few plain
  misfits) and what each week shows. Run it after new entries land or the
  calendar is refetched, then `build_site.py`.
- **`split_cheshek.py`** maps Rav Pappenheim's *Cheshek Shlomo* into
  `references/cheshek-shlomo.json`: one row per root, found from the bold
  headings in the PDF's text layer and kept only where they run in
  alphabetical order, with the pages each spans. Headings the search misses
  are read off the page images and listed in `EXTRA`. The OCR it stores is a
  finding aid only; a rerun keeps any transcription already made.
- **`fetch_shorashim.py [--refresh] [--retry-empty] [--reformat] [--homonyms]`**
  saves Radak's *Sefer HaShorashim* for each root of three letters or more to
  `references/shorashim.json`. Sefaria carries the Berlin 1847 edition, which
  is public domain, so the site shows his own Hebrew with a credit. It reads
  the edition's whole headword list first (2,101 of them), which settles three
  things. The dictionary spells a root ברך where our entries fold it to ברכ.
  Radak has the same letters twice where they are two roots, mostly shin and
  sin (חרשׁ, חרשׂ); both are kept, the one that cites the entry's word first.
  And he files some words elsewhere than our entries do (צאן under צון, מטה
  under נטה and מטט); those filings are the `FILED_UNDER` table in the tool,
  each read in his text before it went in, and each used only if his entry
  there cites the word. A new root that comes up empty and is Biblical wants
  a line there, after looking. Each entry is kept twice: `text` plain, for the
  opening shown in a row, and `html` with the edition's own bold (the root's
  form in each pasuk) and its citations as `.ref` spans, which is what makes
  a long entry readable. `--reformat` reads again any entry stored without
  `html`, and `--homonyms` any root stored before second entries were kept.
- **`show_root.py`** prints his entry for a root with the clusters of ours that
  name it. `--todo N` lists the roots still without English, most cited first;
  `--finish N` groups them by the entry each would complete, the entries nearest
  done first. Prefer `--finish`: working by root frequency leaves many entries
  showing some of their roots in English and not others, which reads as a fault
  rather than as work in progress.
- **`check_glosses.py`** checks `references/radak-gloss.json`, the English the
  roots page shows above Radak's Hebrew, against his own entries: every Hebrew
  phrase quoted must be in the entry, every pasuk cited must be one he cites,
  every authority named must be one he names. It cannot tell whether the
  English renders the Hebrew rightly, which is what a human review is for, so a
  gloss stays `draft` until a person has read it against the source. It also
  refuses a citation printed in Hebrew and a part that is nearly all Hebrew,
  both of which fail the reader the glosses are written for. `--thin` sets his
  longest entries against the English written for them, thinnest first: it
  cannot say a gloss is wrong, only that much of an entry has gone unreported,
  which is a different fault from invention and invisible to every other check
  here. That is how שׁבע was found carrying 23 characters on an entry of 3,654
  that holds the week and the swearing of an oath as well as the number. Run it
  with `check_entries.py` after writing any. `GLOSS-BRIEF.md` is the brief.
- **`fetch_radak_pesukim.py [--refresh]`** saves the pesukim Radak cites, the
  ones `pesukim.json` does not already hold, to `references/radak-pesukim.json`,
  so the roots page can show a citation's text. Run it after
  `fetch_shorashim.py`. The two stores are kept apart because `pesukim.json`
  answers to the entries: `fetch_pesukim.py` rebuilds it from what they cite,
  and Radak's nine thousand would be swept out on the next refresh.
