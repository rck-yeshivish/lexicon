---
name: lexicon
description: The Hebrew-to-English translation guide in lexicon/ (grounded in Rabbi Reuven Chaim Klein's "What's in a Word?" and, later, Radak's Shorashim and Jastrow). Use whenever choosing the English for a Hebrew word or deciding whether two Hebrew words are true synonyms -- e.g. "what's the difference between X and Y", "how should I render X", "is X the same as Y", "which is stronger", "translate this term precisely", or when a chapter draft needs a rendering the ledger does not settle. Also use to ADD to the guide: "add an entry for X", "ingest this article", "look up X in what's in a word", or /lexicon. Not for house-style questions (transliterate vs translate, \tr{} wrapping, spelling): those belong to the transliteration skill's ledger, which outranks this guide.
---

# Lexicon

The guide lives in `lexicon/`. Read `lexicon/README.md` once per session if you
have not; it explains the format and the rules for entries.

## Look up a term

1. Read `lexicon/INDEX.md` whole (one line per entry).
2. Open the matching `lexicon/entries/<file>.md`; apply its **Bottom line**.
3. No entry: run `python lexicon/tools/lookup.py <term>` (Hebrew unpointed,
   transliteration, or English). If a raw article in `lexicon/sources/` covers
   the term, draft an entry from it (below), then rebuild the index.
4. Nothing anywhere: say the guide has no source for it. Never invent a
   distinction or an authority.
5. The project's own ledger (the project's own overlay file)
   outranks the guide on house form. Record any disagreement in the entry's
   *Notes for a project* section.

## Add an entry

- Source first: find the article in `lexicon/sources/whats-in-a-word/catalogue.md`
  (the *terms* column names the words) and read its raw file.
- Copy `lexicon/ENTRY-TEMPLATE.md`; one synonym cluster per file; every
  heading kept; front matter complete (Hebrew unpointed, roots, all plausible
  transliterations, English glosses, domain, source line with the `wiaw:<id>`
  key, authorities, status, date).
- Bottom line first and short. Attribute each distinction to the authority the
  article names. No em dashes, no AI register.
- Then: `python lexicon/tools/build_index.py` and
  `python lexicon/tools/build_catalogue.py`.

## Grow the guide in bulk

`python lexicon/tools/coverage.py --groups` lists every harvested article no
entry draws on yet, with multi-part series grouped. `make_batches.py` splits
that list into batch files for subagents; the drafting brief they follow is
`lexicon/CONTRIBUTING.md`. Run about ten agents per wave, then lint and rebuild
the index yourself. Agents must never run the build scripts.

## Grow the corpus

- `python lexicon/tools/harvest_wiaw.py` pulls any articles newer than the
  local copy (idempotent). Articles newer than the ohr.edu listing are listed
  at the foot of the catalogue with Times of Israel links; fetch those with
  WebFetch (curl is blocked there).
- New source types (Radak, Jastrow, Malbim...) go under `lexicon/sources/<name>/`
  with an access note in `lexicon/sources/README.md`.
