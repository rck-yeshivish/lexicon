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

## Occasional

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
- **`fetch_calendar.py [first] [last]`** saves the diaspora parshiyos and
  Yamim Tovim from Hebcal to `references/calendar.json`. It covers four years
  by default; run it again before they run out.
- **`build_seasons.py [--sample]`** writes `references/seasons.json`, the home
  page's "This week" line: which entries go with each parsha and Yom Tov
  (following Rabbi Klein's book, with its `ADJUST` list for the few plain
  misfits) and what each week shows. Run it after new entries land or the
  calendar is refetched, then `build_site.py`.
- **`fetch_shorashim.py [--refresh] [--retry-empty]`** saves Radak's
  *Sefer HaShorashim* for each root of three letters or more to
  `references/shorashim.json`. Sefaria carries the Berlin 1847 edition, which
  is public domain, so the site shows his own Hebrew with a credit. A root is
  looked up twice, folded and with its last letter in final form, because the
  dictionary spells it ברך and our entries fold it to ברכ.
