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
- `klein-book-manuscript/WTDBAW.docx`, from the author, as of 14 September 2026: the column
  gathered into a book by parsha, 1,258 pages, with footnotes and his working notes.
  Unpublished and still being edited; held for private research use, never for the site.
- `chapters/` is the text split one essay per file (footnotes kept); `chapter-essay-map.json`
  maps each chapter to the corpus essay it matches by content. It holds 371 of the 375
  harvested essays, a typical chapter being about 87% the published text plus revisions,
  and five essays the corpus lacks.
- **Use:** to correct an error the author has since fixed (a locus, a name, a date); not as
  a source for claims the published essays do not make.

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
