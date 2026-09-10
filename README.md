# Lexicon: a Hebrew-to-English translation guide for LLMs

A guide to rendering Hebrew (Biblical, Rabbinic, and *mussar* vocabulary) into
precise English, written in the form an LLM uses best and grounded only in
Orthodox sources. Each entry takes one cluster of near-synonyms, gives each word
its own English, and attributes every distinction to the authority who draws it.

It is meant to be used by any translation project. A project keeps its own house
rulings in its own overlay file; the guide stays general.

## What is in here

```
lexicon/
  README.md            this file: purpose, format rationale, how an LLM should use it
  INDEX.md             GENERATED. One line per entry. The only file loaded up front.
  ENTRY-TEMPLATE.md    the fixed schema every entry follows
  CONTRIBUTING.md      the drafting brief: how to turn a source article into an entry
  entries/<slug>.md    one synonym cluster per file (e.g. shame-bushah-klimah-cherpah.md)
  sources/
    README.md          the source roadmap: what is ingested, what is planned, how to reach each
    whats-in-a-word/   Rabbi Reuven Chaim Klein's column (Ohr Somayach)
      catalogue.md     GENERATED. Every article: id, date, title, terms, links, entry status
      catalogue.json   machine copy (ohr.edu API listing)
      toi_catalogue.json  the Times of Israel mirror listing (its titles name the terms)
      raw/<id>-<slug>.md  the harvested article text, one per article
  tools/
    harvest_wiaw.py    pull the column (catalogue + bodies) from the ohr.edu API; idempotent
    build_catalogue.py rebuild sources/whats-in-a-word/catalogue.md
    build_index.py     rebuild INDEX.md from the entries' front matter
    lookup.py          python lexicon/tools/lookup.py <hebrew|translit|english>
                       searches entries first, then the raw corpus
    check_entries.py   lint entries against the schema and the house voice
    coverage.py        which harvested articles no entry draws on yet
    make_batches.py    split the uncovered articles into agent-sized batch files
```

## Why this format (the research, briefly)

The guide is **Markdown files with a YAML front-matter block, plus one generated
index**. The choice follows what is known about how current models read
reference material:

- **Markdown is the format models have seen most** (documentation, GitHub,
  notebooks, Q&A sites), so it costs the least comprehension. In published
  comparisons it also runs about 30 to 40 percent fewer tokens than the same
  content as JSON, and heading-delimited chunks retrieve markedly better than
  unstructured prose. JSON wins only for genuinely tabular data; XML has the
  worst token efficiency and the lowest comprehension scores of the three.
- **XML tags are for delimiting a prompt, not for storing knowledge.**
  Anthropic's own guidance uses tags such as `<documents>` to separate sections
  *inside a prompt*. So a session that pastes several entries into a prompt
  should wrap each in a tag; the files themselves stay Markdown.
- **The index is Hebrew-first.** The guide is used in one direction: you are
  looking at a Hebrew word and need its English. So `INDEX.md` opens with a
  headword table in alef-bet order, one row per Hebrew word, and nothing in it
  is truncated. A row states that word's own English only when the entry
  carries a per-word `words:` block; otherwise it points at the entry rather
  than guess from the neighbouring words in the cluster.
- **Progressive disclosure beats one big file.** A model works best when it
  loads a short index, then only the entries it needs. That is the pattern of
  Claude's skills and its memory index, and it keeps the guide usable when it
  reaches hundreds of entries. Hence `INDEX.md` (one line each) and small
  per-cluster files.
- **Answer first.** Each entry opens with a *Bottom line* block: the rendering
  to use, in two to five lines. The reasoning follows for a reader who wants it.
  Models weight the opening of a document, and a translator in mid-sentence
  needs the ruling, not the essay.
- **Grep keys in the front matter.** Every entry lists the Hebrew (unpointed),
  the root letters, every plausible transliteration, and the English glosses.
  A model searching in any of those forms finds the file with a plain
  `grep -ril`, no embedding index required.

Sources for the format claims (read 2026-09-09):
[Webex Developers on Markdown for LLMs](https://developer.webex.com/blog/boosting-ai-performance-the-power-of-llm-friendly-content-in-markdown),
[Checksum: JSON vs XML vs Markdown experiment](https://checksum.ai/blog/does-output-format-actually-matter-an-experiment-comparing-json-xml-and-markdown-for-llm-tasks),
[TianPan: context format decision](https://tianpan.co/blog/2026-05-07-context-format-decision-agent-reasoning-json-markdown-plain-text),
[Anthropic: use XML tags](https://console.anthropic.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags).

## How an LLM should use this guide

1. **Read `INDEX.md`** when a translation choice comes up (which English word
   for a Hebrew term; whether two Hebrew words are true synonyms; the order or
   intensity of a pair). One line per entry, so it is cheap to load whole.
2. **Open the matching entry** in `entries/`. Apply the *Bottom line*. Read the
   *Distinctions* only when the passage turns on the difference.
3. **No entry?** Run `python lexicon/tools/lookup.py <term>`. It searches the
   entries' front matter, then the raw corpus in `sources/`. If a raw article
   covers the term, draft a new entry from it (schema in `ENTRY-TEMPLATE.md`),
   then run `python lexicon/tools/build_index.py`.
4. **Still nothing?** Say so. Do not invent a distinction. The guide records
   what the sources say; a rendering with no source behind it is a judgment
   call and must be labeled as one in the project's own ledger, not here.
5. **A project's own rulings outrank this guide.** The guide says what a word
   means and how the classical authorities separate it from its neighbors. A
   project's own style ledger decides whether to transliterate, which house form
   to use, and any project-specific carve-out. Keep those rulings in the
   project, not here. Where an entry needs to record that a project reads a word
   differently, its *Notes for a project* section states the disagreement rather
   than resolving it.

## Writing an entry

- One **synonym cluster** per file, named `<english-cluster>-<translit>-<translit>.md`,
  lowercase, hyphens, no apostrophes.
- Follow `ENTRY-TEMPLATE.md` exactly: the headings are load-bearing for the
  index builder and for a model skimming by heading.
- **Attribute every distinction** to the authority the source names (Radak,
  Malbim, Rabbi Shlomo Pappenheim, the Vilna Gaon, Rav Hirsch, and so on).
  Where authorities disagree, list the views; the *Bottom line* picks the
  majority or the most useful reading and says which it is.
- **Source line is mandatory** and points at a real article or page in
  `sources/`. No entry without a source.
- Keep the house voice: no em dashes, no AI register, frum terms as a
  *talmid chacham* writes them. Entries are short (40 to 120 lines).
- After adding or editing entries: `python lexicon/tools/check_entries.py`, then
  `python lexicon/tools/build_index.py` and `python lexicon/tools/build_catalogue.py`.

## Growing the guide in bulk

The corpus is far larger than the entries written from it. To work through it:

```
python lexicon/tools/coverage.py --groups          # what is left, series grouped
python lexicon/tools/make_batches.py <dir> --size 11
```

Then hand each `batch-NN.tsv` to a subagent whose brief is `CONTRIBUTING.md`,
the template, and the exemplar entry. Ten agents at a time is comfortable.
Lint and rebuild the index once the wave reports; the agents must not run the
build scripts themselves, or they will race each other.

## Source roadmap

See `sources/README.md`. Ingested: **What's in a Word?** (Rabbi Reuven Chaim
Klein, Ohr Somayach), 374 articles 2016 to Aug 2025 via the ohr.edu API, with
the Times of Israel mirror for the Aug 2025 onward tail. Planned: Radak's
*Sefer HaShorashim*, Jastrow's dictionary (for sources and Rabbinic usage),
Malbim's *Yair Ohr* / *HaCarmel*, Rabbi Shlomo Pappenheim's *Cheshek Shlomo*,
Rav Hirsch's etymological comments, and the Vilna Gaon's synonym notes.

## The site

`python tools/build_site.py` generates `site/` and `DEPLOY.md` covers shipping
it. The pages are static: the browse lists are rendered into the HTML rather
than assembled by script, so the site reads with JavaScript off and a crawler
sees real links to all 342 entries. `site/llms.txt` points a model at
`data.json` and documents the record shape.
