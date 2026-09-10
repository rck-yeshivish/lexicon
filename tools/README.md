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
