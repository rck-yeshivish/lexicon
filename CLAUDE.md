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

   A citation is the one thing an entry may quietly put right. Where the essay
   prints a chapter or a pasuk that is plainly a slip, the entry gives the
   correct one without a note, and the audits have found it doing so: Rav
   Hirsch to Bereishis 17:7 given as 17:17, the pasuk that has ויצחק; Hoshea
   5:19 given as Mishlei 5:19, the one with אהבים, Hoshea having only fourteen
   chapters; Iyov 21:21 as 21:12, which has the עוגב; Shmuel I 12:4 as Shmuel
   II 12:4, Nasan's parable with the הלך. The bar is certainty and not
   likelihood: put it right only where the text itself settles it, as each of
   those does, and check it against references/pesukim.json rather than from
   memory. Where you are not certain, keep what the essay prints and say in the
   entry that it is the essay's.

   When a citation is wrong, the author's rule is to assume a typo and look for
   it rather than to conclude he cited nothing. Either the chapter and verse are
   right and the book is wrong, or the book is right and the numbers are off,
   most often two digits transposed or one digit out. Search that way before
   giving up: Vayikra 22:17 has no *et* and looked unsalvageable, and the verse
   he meant was 22:14.

   Midrash Rabbah is the exception to checking against another text. Every
   Midrash Rabbah reference he gives follows the numbering of the
   Wagshal/Moznaim edition, which differs from Sefaria's and from others, so a
   Midrash Rabbah locus is never renumbered to match another edition. Four that
   had been (Koheles Rabbah 8:4, Bereishis Rabbah 12:12, Bamidbar Rabbah 20:21,
   Eichah Rabbah 2:48) are back as he gives them.
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

## The site

`python tools/build_site.py` generates `site/`, a static Cloudflare Pages
folder: a home page whose search is the page, Hebrew and English browse pages
driven by a letter strip, and one page per entry. It reads the entries directly,
so the site is never a second copy of the data to keep in sync. Rebuild it after
`build_index.py`. Deployment, and why only `site/` should ever be uploaded, is
in `DEPLOY.md`.
