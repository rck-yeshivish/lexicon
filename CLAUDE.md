# Lexicon

A Hebrew-to-English translation guide, written for LLMs. Each entry takes one
cluster of near-synonyms, gives every word its own English, and attributes each
distinction to the authority who draws it. Where authorities disagree, the entry
says so and names them.

Read `README.md` first. It explains the format, why it is shaped this way, and
the protocol for looking a word up.

## The shape of the thing

- `INDEX.md` is generated and Hebrew-first. Part 1 is a headword table in
  alef-bet order, one row per Hebrew word. Part 2 carries each entry's full
  ruling. Nothing in it is truncated.
- `entries/<cluster>-<translit>-<translit>.md` is one synonym cluster per file.
- `sources/` holds the corpus every entry cites, with a roadmap in its README.
- `tools/` builds and checks. See `tools/README.md` for which are routine.

## Rules that do not bend

1. **No invented distinctions.** Every difference between two words traces to a
   named authority in a real source. If the sources are silent, the entry says
   they are silent. A rendering with nothing behind it is a judgment call and
   must be labelled as one.
2. **Report what the article cites, whatever its provenance.** The article is
   the conduit, not the authority. If Rabbi Klein brings Gesenius, an Akkadian
   or Ugaritic cognate, a Greek or Latin etymology, or a named academic, that
   material belongs in the entry, attributed the way he attributes it. What you
   may not do is bring in material of your own from outside the article.
3. **Disputes stay disputes.** Name each view and its holder. The Bottom line
   says the authorities differ and does not choose between them. Never smooth a
   machlokes into one answer.
4. **Explain the words; do not direct translation.** Outside Rendering
   guidance, an entry says what the words mean and how they differ, never how
   to translate them. Rendering guidance is the one place for that advice.
   `VERIFY.md` has the full rules on what an entry must not contain.
5. **No em dashes.** Commas, semicolons, parentheses, or recast.
6. **No AI register.** No *delve*, *it's worth noting*, *leverage*, *navigate*,
   *underscores*, *a testament to*, *journey*. Write as a *talmid chacham*
   writes.
7. **Frum register.** *Chazal* teach, the *pasuk* says. Hebrew book names:
   Bereishis, Shemos, Vayikra, Bamidbar, Devarim, Yeshayahu, Tehillim, Mishlei,
   Koheles. Rambam, not Maimonides. Hashem, not G-d.
8. **The guide stays general.** It says what a word means and how the
   authorities separate it from its neighbours. What a particular translation
   project decides to *do* with that (transliterate or translate, which house
   spelling, which carve-out) belongs to that project's own overlay, not here.

## Working on it

Adding entries: `CONTRIBUTING.md` is the drafting brief, `ENTRY-TEMPLATE.md`
the schema, and `entries/shame-bushah-klimah-cherpah.md` the worked exemplar.

After any change to entries:

```
python tools/check_entries.py && python tools/build_index.py
```

Entries are marked `status: draft` until a human has read one against its
source; `reviewed` is that human's mark, not the drafter's.

## The site

`python tools/build_site.py` generates `site/`, a static Cloudflare Pages
folder: a home page whose search is the page, Hebrew and English browse pages
driven by a letter strip, and one page per entry. It reads the entries directly,
so the site is never a second copy of the data to keep in sync. Rebuild it after
`build_index.py`. Deployment, and why only `site/` should ever be uploaded, is
in `DEPLOY.md`.
