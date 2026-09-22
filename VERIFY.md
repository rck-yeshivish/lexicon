# The verification pass

Every entry was written from its source article and checked for form. None was
checked for fidelity. A 15-entry audit (September 2026, seeded random sample, each entry read in full
against its source) found **58 faults, about 3.9 per entry**. Every one of the
fifteen came back MINOR: none clean, none serious. They cluster hard:

| Fault | Count | What it looks like |
|---|---|---|
| Overreach | 24 | "may have led to the supposition" becomes "is the natural support for" |
| Misattribution | 12 | a view the article gives anonymously, or as the columnist's own guess, credited to a named authority |
| Citation | 12 | a locus the article never gives, or the article's own slip repeated silently |
| Omission | 9 | the article's answer to its own opening question missing from the entry |
| Fabrication | 1 | a distinction the article does not contain |
| Reversal | 0 | a distinction stated backwards |

Nothing found was fatal: no invented authorities, no invented works, no
distinction backwards. The clusters and the main rulings hold. What drifted is
confidence, always upward.

## What a verification pass does

For one entry, with its source article open beside it:

1. **Read both in full.** Not the Bottom line against a skim.
2. **Walk every claim in the entry back to a sentence in the article.** A claim
   that cannot be walked back is either cut or marked as ours.
3. **Restore every hedge.** If the article says "seems to", "presumably",
   "some explain", "may have", "in some versions", the entry says so too. This
   is the single most common fault and the easiest to fix.
4. **Check who said it.** The columnist's own inference is not the authority's
   view. An anonymous "some explain" stays anonymous. A named academic whose
   substance the entry keeps must either be credited or the substance dropped.
5. **Check every locus.** Against the article, and where the article is itself
   wrong, say so in the Sources paragraph rather than repeating it silently.
6. **Check what is missing.** Especially the article's own answer to the
   question it opens with.
7. **Check the verse numbers against a text, not just the article.** The
   articles mix Hebrew and English versification, and at least one wrong locus
   was repeated in four places within a single entry, carrying a quotation the
   verse does not contain. Where book names were converted to Hebrew, the
   numbers were not always converted with them.
   A count the article gives is checked by occurrences, not by pesukim. It
   said *peresh* appears seven times and listed six pesukim, and the count was
   right: Malachi 2:3 has it twice. Counting the loci instead of the words
   raised a slip that was not there.
8. **Check the Sources paragraph last, as a separate step, against the finished
   body.** Every Sources-level slip a cold audit of corrected entries found sat
   in a footer nobody re-read after the body was fixed: two citations fused into
   one, a work listed that the article names only to say its author never
   revisits it. It must not claim an omission the entry did not make, must not
   list a locus the entry never uses, and must split what the article splits.
9. **Check the boundary of every named attribution.** The commonest fault left
   after a correction pass is the columnist's inference quietly promoted to the
   authority's view. The article gives an authority a narrow point, the column
   reasons past it to a broader conclusion, and the entry credits the authority
   with the conclusion. Find the sentence in the article and check where the
   name's responsibility stops.

## What not to do

- Do not smooth a machlokes the article leaves open. If the article closes with
  two live views, the entry closes with two live views.
- **Restore anything dropped as "omitted under house rule 9".** That rule was
  carried over from a different project by mistake. Material the article itself
  cites belongs in the entry whatever its provenance, attributed as the article
  attributes it. Where an entry says it omitted an etymology, a cognate or a
  named scholar, put it back and delete the omission note.
- Do not add material of your own from outside the article. The guide reports
  the essays; it does not supplement them.
- Do not rewrite for style. This pass changes truth conditions, nothing else.
- The `words:` block is optional and carries nikud for colliding spellings; the
  per-word rulings live in the body table. A sparse block, or none at all, is
  not a fault and is not a reason to leave an entry `draft`. Correct a `tr`,
  `en` or `distinct` there only where the article contradicts it, never an
  `nk:`, and never write an unquoted colon inside a YAML value.

## What an entry must not contain

- **Nothing outside Rendering guidance tells anyone how to translate.** The
  site's owner does not want that focus on the platform. In the Bottom line,
  Distinctions, Where the authorities disagree, At a glance and every other
  section except Rendering guidance, keep what a sentence says about the words
  and delete what it tells someone to do. "What a translator must get right is
  that they are not interchangeable" becomes "they are not interchangeable"; "do
  not smooth it to one name", "in roman type", "keep it untranslated" and
  "render it as" simply go. Nothing is moved into Rendering guidance, which
  already carries the translator's advice and stays as it is. This removes a
  focus, not content: every distinction, reading, name and hedge about the
  words themselves stays.
- **Rendering guidance is left as it is, except for project framing.** It is
  the one place translation advice belongs, collapsed by default under "For
  translators". Only remove wording that assumes a particular project: "in a
  mussar sefer", "inside / within a chapter", "the sefer", "house form / style",
  "the Alter".

- **Deleting a misprint note means fixing the locus under it.** A note such as
  "the article prints Shemos 3:16" usually sits beside the wrong locus in the
  body. Removing the note alone leaves a known-wrong reference with nothing to
  warn the reader, which is worse than the note. So the body and the "Cited in
  the essay" line must carry the correct locus, checked against the text
  itself. Where no correct locus can be established, the impossible one comes
  out. "Impossible" means no edition can have it: search every spelling
  (מיאון and מאון, full and defective), and never remove a locus on one digital
  edition's silence when the essay and the author's book both give it.
- **Tell the content; do not narrate the essay.** "The column opens with",
  "closes with a story", "turns to", "the column's opening question" walk the
  reader through the essay instead of telling them what it says. A story, a
  verse, a parallel or an authority's view is simply stated: "Rabbi Dr. Norman
  Lamm is reported to have answered", not "The column closes with a story:
  Rabbi Lamm…". The exception is Rabbi Klein's own conclusion or suggestion
  where other views exist: that keeps its attribution, or it reads as settled
  fact, but it is attributed to him as a person holding a view, "Rabbi Klein
  concludes", as the entry would attribute Malbim.
- **The Sources section is a citation and a list of loci. Nothing else.** It
  reads, in full:

      Rabbi Reuven Chaim Klein, "An Utter Embarrassment," *What's in a Word?*,
      Ohr Somayach, 17 September 2022.

      Cited in the essay: Radak to Yeshayahu 45:16 and *Sefer HaShorashim*; Bedersi,
      *Chotam Tochnit*; Rav Hirsch to Vayikra 13:59 and Tehillim 139:16; ...

  One citation line per article the entry rests on, then one "Cited in the essay:" line
  listing only what the body actually uses, each at its correct locus. No
  commentary of any kind: not what was changed or restored, not how the article
  cross-refers to its own earlier pieces, not why the entry attributes
  something as it does, not what the article misprints or fails to specify, not
  archive details, and never an internal file path. Where the article misprints
  a locus, the body and the loci list simply give the right one.
## Marking

When an entry has been through this pass and its claims trace to the article,
set `status: reviewed` in the front matter. Until then it stays `draft`, and
the site says so. `reviewed` is a claim that someone checked; do not set it on
an entry you only skimmed.
