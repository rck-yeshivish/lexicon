# Sources

Every entry in `../entries/` must trace to a file here. Orthodox sources only.

## Ingested

### What's in a Word? (Rabbi Reuven Chaim Klein, Ohr Somayach)
- Weekly column on Hebrew near-synonyms, 2016 to present. Each piece takes a
  cluster of two to six words, brings the classical lexicographers (Menachem
  ibn Saruk, Ibn Janach, Radak in *Sefer HaShorashim*, Malbim, Rabbi Shlomo
  Pappenheim, Rav Hirsch, the Vilna Gaon, and others) and settles how the
  words differ. The single best seed for this guide.
- **Access.** Listing and full text: the JSON API behind articles.ohr.edu,
  `https://articles.ohr.edu/api/v1/articles?category_slug=whats-in-a-word&per_page=50&page=N`
  and `.../api/v1/articles/<slug>`. Plain `curl` works; the WebFetch tool gets
  403 on ohr.edu. Mirror with term-naming titles: the author's Times of Israel
  blog, `https://blogs.timesofisrael.com/author/reuven-chaim-klein/feed/?paged=N`
  (RSS, titles and links only; article pages are behind Cloudflare for curl but
  WebFetch reads them). Also syndicated in the Jewish Press.
- **Harvest.** `python lexicon/tools/harvest_wiaw.py` (idempotent), then
  `python lexicon/tools/build_catalogue.py`. Output in `whats-in-a-word/`.
- Text is copyright the author and Ohr Somayach; it is stored here for private
  research use as source material, not for republication.


### Klein, *What's in a Word? Synonyms in the Hebrew Language* (book manuscript)
- `klein-book-manuscript/WTDBAW.docx`, from the author, as of 18 September 2026: the column
  gathered into a book by parsha, 1,258 pages, with footnotes and his working notes.
  Unpublished and still being edited; held for private research use, never for the site.
  This copy carries the 21 corrections he made after reading the verification pass, which
  `git log -p` on the chapters shows one by one. On 23 September 2026 he confirmed six more
  that the guide had already made against his printed text (Shemos 21:28 for 21:25 in
  *Coming Closer*; Mishnah Bava Basra 2:5 for 2:4 in *Jumping for Passover*; Shemos 9:14-15
  for 9:14 in *Plague of Plagues*; Ramban to Bereishis 14:19 for 14:18 in *Prime Property*;
  Shemos 35:7 for 35:4 in *Seeing Red*; Mishnah Pesachim 4:7 for 5:7 in *Welcome to Rooster
  City*), and for *Olives and Oil* asked that the claim that *yitzhar* is never joined to
  *zayis* stand, with Melachim II 18:32 noted as the one exception.
  On 5 October 2026 he answered a further set. He confirmed Bereishis 49:15 for 49:14 in
  *Good and Pleasant*, and that ח"ש in his notes is Rav Pappenheim's *Cheshek Shlomo*. He gave
  the rule that every Midrash Rabbah reference follows the Wagshal/Moznaim numbering (see
  CLAUDE.md rule 2). He agreed that *kira* is not at Yevamos 76a, and gave Yevamos 120a,
  which he has added to the document. The Zohar (Tazria 48a) makes *adam* the greatest of the
  four names and does not rank the other three; the essay's "successively lower" is withdrawn.
  By "similarly" he means that two authorities draw the same distinction, even where they
  assign it to the opposite words of the pair. The one-letter root that his note on Rabbi
  Zundel Kroizer ties to *neis* is his own remark, and Rav Pappenheim parses *neis* otherwise.
  Tzeruyah from *tzari* is *Daas Mikra*'s, to Divrei HaYamim I 1:32. His note on the root צר
  is his own, since no one source needs naming. The paytanim's coloured gold reached him
  through Y. Y. Stahl, *Segulah* 24 (Chanukah 5782).
- **Split.** `python tools/split_manuscript.py` writes `chapters/`, one essay per file with
  its footnotes, and `chapters.json`. The book's outline carries the shape, and Word stores
  it two ways: a Heading style on some paragraphs, a direct `outlineLvl` on the rest. Reading
  only the styles finds 122 of the 346 essays, so both are read. A level four heading is a
  section inside an essay, which is what a multi-part column looks like once its parts are
  joined, so it stays inside the chapter rather than starting a new one.
- **Map.** `python tools/map_manuscript.py --report` writes `chapter-essay-map.json`, matching
  chapters to published essays by eight-word shingles rather than by title, since the site
  retitles pieces and prefixes the parsha. 340 of the 346 chapters match an essay and 377 of
  the 378 harvested essays are claimed. Four chapters are essays the corpus lacks: *Making
  Mountains out of Hills*, which was published on the author's Times of Israel blog on
  15 May 2019 and which the harvest missed, and *My Husband, My Man*, *Of Demons and Spirits* and *Output Understood*, which appear in neither catalogue. Two have since turned up in the Jewish Press, which syndicates the column: *Output Understood* (25 August 2021) and *My Husband, My Man* (8 June 2022), and their entries link there with a `jp:` source line. *Of Demons and Spirits* is on none of Ohr Somayach, Times of Israel, the author's Google Group or the Jewish Press (all 210 of his posts there checked on 23 September 2026). Jewish Press links take the short form, jewishpress.com/<slug>/; the older dated addresses under /review/in-print-review/ now return 404.
- **His source lists.** Most essays end with a footnote listing in Hebrew everything the essay
  quotes, which is the only place many citations are written down, because the essays
  frequently name a rabbi without saying where he wrote it. `python tools/klein_sources.py`
  parses those lists to `../references/klein-sources.json`. Where a source is missing from a
  list, the author's rule is that the place is obvious: Kohut's *Aruch HaShalem*, Radak's
  *Sefer HaShorashim*, Rav Pappenheim's *Cheshek Shlomo* on that root, or Rashi or Radak on
  that pasuk. `מהרשא"ו` is Rabbi Shlomo Aharon Wertheimer's *Beiurei Shemos Nirdafim*, and the
  parentheses after it name the entry there that treats those words.
- **Use:** to correct an error the author has since fixed (a locus, a name, a date), and,
  since 5 October 2026 with the author's permission, for material the book's text adds that
  the published essay lacks, written into the entry and attributed as the book attributes it.
  Where the book's text and the published essay differ without one correcting the other,
  the entry follows the book. His working notes are a separate matter, governed by the rule
  below. An earlier exception the author allowed is an essay the published corpus does not hold at all: *My Husband, My
  Man*, *Of Demons and Spirits* and *Output Understood* are entries drawn from the chapter
  alone, and their source line is `ms:<chapter>.md`, with a `jp:` line beside it for the two of the three found published since.
  He has read the husband entry; *Of Demons and Spirits*, *Output Understood* and *Making
  Mountains out of Hills* still wait for his reading. Each chapter opens with the author's own working notes before the essay proper begins. His
  rule for them: a note that is fully formed and stands on its own may go into an entry; one
  that only names a source without saying what it says, or says "see" something, or is too raw
  to mean anything alone, stays out. The notes he meant for use are usually highlighted yellow,
  and the highlighting survives in the docx (3,953 runs), but it also marks passages inside
  finished essays, so it shortlists and does not decide. The notes pass of 22 September
  2026 read all 598 candidate notes and wrote the 262 that met his rule into 155 entries,
  each under the word it treats, as part of the entry and not set apart; the chapter joins
  the entry's `sources:` as an `ms:` line and its Sources section as a citation, and the
  note's loci join "Cited in the essay". Where a note corrects the essay, the entry follows
  the note. A second round took up the 79 notes first held for a closer look (readers'
  letters, notes that seemed to name no authority, notes on a word beside the cluster) and
  wrote in 55 whose source checked out and whose word the entry treats. Held back: readers'
  and colleagues' own views with no source behind them, and three passages whose author
  is not yet traced.

### Klein, "Learning to differentiate between apparent synonyms" (Babel, 2020)
- `klein-babel-2020/` holds the PDF and its extracted text. Rabbi Klein writing
  about the *method* rather than about one cluster: why the question arises, the
  formulae the answers follow (unnumbered in the article; the eight headings are
  ours), and seven of the rabbis who wrote lexicons of difference. Distilled into `../references/how-synonyms-differ.md`, which is
  what the drafting brief points at.
- It also treats several clusters directly, including the eight words for road
  and path, of which our entry currently covers only two.
- *Babel: The Language Magazine*, May 2020, pages 30 to 33. Copyright the author
  and the magazine; held here for research use.

## Planned

- **Radak, *Sefer HaShorashim*.** The root dictionary the column leans on most.
  On Sefaria (Hebrew, by root) and as scanned PDFs (the user has one to add).
  Plan: ingest per root as `radak-shorashim/<root>.md` when an entry needs it,
  not the whole book at once.
- **Jastrow, *Dictionary of the Targumim, Talmud Babli and Yerushalmi, and the
  Midrashic Literature*.** For Rabbinic usage and the source citations behind
  each sense. Public domain; on Sefaria with an API. Use for *mareh mekomos*
  and Rabbinic senses, not for theology.
- **Malbim** (*Yair Ohr* / *HaCarmel* and his synonym notes in the Tanach
  commentary), **Rabbi Shlomo Pappenheim** (*Cheshek Shlomo*, *Yeriot Shlomo*),
  **Rav Hirsch** (etymological comments in the Chumash commentary),
  **Vilna Gaon** (synonym distinctions scattered through his commentary on
  Mishlei and Yeshayahu). Ingest as excerpts attached to entries.
- **Rabbi Klein's books** (*Lashon HaKodesh: History, Holiness, & Hebrew*,
  *God versus Gods*) as background, not as entry sources.
