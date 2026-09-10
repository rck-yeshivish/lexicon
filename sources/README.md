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
