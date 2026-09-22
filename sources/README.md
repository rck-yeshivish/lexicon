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
  `git log -p` on the chapters shows one by one.
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
  15 May 2019 and which the harvest missed, and *My Husband, My Man*, *Of Demons and Spirits*
  and *Output Understood*, which appear in neither catalogue.
- **His source lists.** Most essays end with a footnote listing in Hebrew everything the essay
  quotes, which is the only place many citations are written down, because the essays
  frequently name a rabbi without saying where he wrote it. `python tools/klein_sources.py`
  parses those lists to `../references/klein-sources.json`. Where a source is missing from a
  list, the author's rule is that the place is obvious: Kohut's *Aruch HaShalem*, Radak's
  *Sefer HaShorashim*, Rav Pappenheim's *Cheshek Shlomo* on that root, or Rashi or Radak on
  that pasuk. `מהרשא"ו` is Rabbi Shlomo Aharon Wertheimer's *Beiurei Shemos Nirdafim*, and the
  parentheses after it name the entry there that treats those words.
- **Use:** to correct an error the author has since fixed (a locus, a name, a date); not as
  a source for claims the published essays do make differently. The one exception the author
  has since allowed is an essay the published corpus does not hold at all: *My Husband, My
  Man*, *Of Demons and Spirits* and *Output Understood* are entries drawn from the chapter
  alone, and their source line is `ms:<chapter>.md` because there is nothing to link to.
  Each chapter opens with the author's own working notes before the essay proper begins. His
  rule for them: a note that is fully formed and stands on its own may go into an entry; one
  that only names a source without saying what it says, or says "see" something, or is too raw
  to mean anything alone, stays out. The notes he meant for use are usually highlighted yellow,
  and the highlighting survives in the docx (3,953 runs), but it also marks passages inside
  finished essays, so it shortlists and does not decide.

### Klein, "Learning to differentiate between apparent synonyms" (Babel, 2020)
- `klein-babel-2020/` holds the PDF and its extracted text. Rabbi Klein writing
  about the *method* rather than about one cluster: why the question arises, the
  eight ways apparent synonyms differ, and the canon of rabbis who wrote lexicons
  of difference. Distilled into `../references/how-synonyms-differ.md`, which is
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
