# Transcribing and writing the English for Rav Pappenheim

Rav Shlomo Pappenheim's *Cheshek Shlomo* (the Shorashim) is the book Rabbi Klein
cites more than any other dictionary: 131 entries name it. This brief covers two
jobs for each of its roots: a clean Hebrew transcription from the page images,
and the English the site shows above it, the counterpart of what
`GLOSS-BRIEF.md` does for Radak.

## The edition

`sources/cheshek-shlomo/cheshek-shlomo.pdf`: *Sefer Cheshek Shlomo, Shorashim*,
printed for the first time from his manuscript by Moshe Tzuriel, Bnei Brak
5777, as hebrewbooks.org carries it. Only 39 pages of it were printed in his
lifetime. The printed page number is the PDF page less two.

The PDF is a scan under an OCR text layer, and the OCR is rough: it reads ח as
ת or ה, swaps final letters, mangles the voweled pesukim and turns the small
citation type into digits. `references/cheshek-shlomo.json` maps the book from
it: each root's headword (`hw`), the PDF and printed pages it spans, and the OCR
(`ocr`) as a finding aid. The OCR is never quoted, shown or glossed from. The
transcription is made from the page images.

The words are Rav Pappenheim's. The square-bracketed insertions and the
numbered footnotes are the editor's, and must never be credited to him.

## The transcription

The root's entry runs from its bold heading (two or three letters and a period,
**אב.**) to the next bold root heading of the same form, which may stand on the
same page. Where a root heading appears inside the span that the map does not
list, the entry stops there; report it.

- Every word as printed, in order, with its punctuation, quotation marks,
  parentheses and the editor's square brackets.
- No niqqud and no te'amim. The letters exactly as printed, full or defective
  spelling as the page has it.
- The bold lead words that open his paragraphs (**ויקרא**, **ועניין**) in `**`.
- A blank line between paragraphs.
- `[p. 38]` on its own line where a new printed page begins.
- An editor's footnote marker as `[^74]` where it stands, and the footnote's
  text at the end of the entry as `[^74]: מכות ג, ב`.
- Not the running head, the page number, or a letter's section title (אות אל"ף).
- Nothing corrected. A word that looks like a misprint is copied as printed and
  listed under doubts with its page. A word the scan does not let you read is
  `⟦?⟧`, also listed.

## The English

The shape is Radak's:

```json
"אב": {
  "sense": "the line that stands in the root's row, under 170 characters",
  "more": [{"h": "heading under 40 characters", "t": "one thing his entry holds"}]
}
```

Every rule and every trap in `GLOSS-BRIEF.md` binds here, with "Radak" read as
"Rav Pappenheim". In particular: report only what his entry holds; every Hebrew
phrase quoted gets its English; cite in English, from what he prints, and
correct an address only where the pesukim settle it; never name an authority he
does not name; and, after another authority, call him Rav Pappenheim rather
than "he".

What is his own:

- **The root first.** He gives each two-letter root one basic sense (its
  *hanachah* or *hora'ah*) and derives words from it. The `sense` line says
  what that basic sense is, in his terms. Lead with the meaning, not the
  method.
- **One part for each word or family he derives**, saying what the word means
  and how he gets it from the root, with the pesukim he brings, each given its
  English. Where a third letter, a doubled letter or a prefix carries the
  derivation, say what it adds as he says it.
- **Where he sets two words apart, say how.** Telling near-synonyms apart is
  the reason this guide exists, and it is often the most useful part of his
  entry.
- **The editor is not Rav Pappenheim.** A bracketed insertion may be read for
  sense but not quoted as his. A footnote may supply the address of a quotation
  he leaves unsourced; otherwise footnotes stay out of the English.
- **A part earns its place.** His entries run from half a page to many pages.
  Cover the words he derives and the distinctions he draws, not each example.
