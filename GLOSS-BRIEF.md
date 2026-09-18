# Writing the English for Radak

`references/radak-gloss.json` is the English the roots page shows above Radak's
own Hebrew. This is the brief for writing it, whether by hand or by an agent
given a batch of roots. `tools/check_glosses.py` enforces what a machine can
enforce; everything here that it cannot enforce still binds.

## What is being written

Keyed by **his headword** as `references/shorashim.json` stores it, not by the
root letters our entries use. The two differ where he files a word elsewhere,
and an entry that serves two roots is glossed once.

```json
"headword": {
  "sense": "the line that stands in the root's row, under 170 characters",
  "more": [{"h": "heading under 40 characters", "t": "one thing his entry holds"}]
}
```

`sense` stands in a table row beside a thousand others, so a reader scanning the
list sees what the root means before opening anything. `more` is what the open
panel adds above his Hebrew: a few short labelled parts, each one thing his
entry holds. Both are the guide's summary of his entry, not his words and not a
translation, and the page says so.

## Reading his entry

```
python tools/show_root.py שלח קרב
```

prints his Hebrew, the headword he files it under, and which of our entries name
it. Everything needed to write a gloss is there. Fetch nothing from the web and
bring nothing from your own knowledge of the word.

`python tools/show_root.py --finish 50` gives the roots still to do, grouped by
the entry each would complete.

## The rules

1. **Report only what the entry holds.** Where he names a view and its holder,
   name both. Where he disputes one, say so and say whom. Nothing from outside
   the entry, and nothing from memory: not a verse number, not a gloss, not a
   cross-reference.
2. **Every Hebrew phrase quoted gets its English.** This is the rule most often
   broken, and the reason the site exists: a part that lists four pesukim and
   renders none of them gives a reader without Hebrew nothing at all. Quote a
   pasuk, then say what it says.
3. **Cite in English.** `(Yirmiyahu 22:14)`, never `(ירמיה כב, יד)`. Take the
   chapter and pasuk from his Hebrew and write the book's name in English. A
   citation left in Hebrew is one the reader cannot read and one the check
   cannot verify against his own citations.

   What he brings from outside Tanach goes the same way, named in English with
   the place he gives: a masechta by daf, `(Sanhedrin 63b)`, as a hundred-odd
   already do; a Mishnah by chapter and mishnah, `(Avos 5:15)`; a midrash by its
   parsha, `(Bereishis Rabbah 43)`. Where the edition prints the address in a
   form that will not carry over, name the work and leave the address off rather
   than reproduce his Hebrew or invent a form of your own.
4. **Lead with what the word means.** Grammar is named only where he rests
   something on it, and then by what it does, since binyan names are not
   English. עומד is intransitive and יוצא transitive; פועל עבר is a past verb;
   הכבד and הפעל הכבד are the heavy form. The bare עובר is transitive as well,
   which the corpus settles three times over: at עמם פועל עובר labels
   עֲמָמוּהוּ, carrying an object suffix, and at פטר and חלץ הפעל העובר stands
   in explicit contrast to עומד. The one place it will not bear that reading is
   דשׁן, where וְדָשֵׁן governs nothing and the contrast he draws is with תאר,
   an adjective, exactly as at אור he sets פועל עבר against בינוני; either the
   edition has slipped a vav into עבר or the label is a tense there. That gloss
   reports the contrast and rests on neither reading, which is what to do when
   his label and his examples pull apart.
   The standing way of doing that, "where the verb takes an object", was
   checked against his own labels in all 59 places it appears. Thirty-eight sit
   under a heavy form he marks himself, `[הפעיל]` or `[פעל]`; three that looked
   like passives or reflexives carry his `[הפעיל]` or `[פעל]` immediately before
   the pasuk quoted; and at פטר and בוס transitivity is his own term, `והפעל
   העובר` and `תאר יוצא`. One was wrong, at סכך, where it stood directly above a
   kal with an object, and that one now reads "of one who covers another".

   The seam sweep then broke it four more times, which is five failures in the
   sixty-odd places it is used, and they are worth listing because they are all
   one fault. At רבה the run marked `הפעל הכבד [הִפְעִיל]` holds מַרְבֵּה
   רַגְלַיִם, which governs nothing. At עור he splits his own `[הפעיל]` run
   himself, three words `פעלים יוצאים` and two `פעלים עומדים`, so the English
   had to contradict itself two clauses later. At עמד the same run holds
   וּמֶלֶךְ יִשְׂרָאֵל הָיָה מַעֲמִיד בַּמֶּרְכָּבָה, which governs nothing and
   which he glosses reflexively, היה מחזיק עצמו ומתחזק. At לון the one word
   under the heading that governs no object is מָקוֹם לָנוּ לָלִין, and the note
   that would make it transitive, `כמו להלין`, had been dropped with the label;
   and a `והנפעל` there was called a passive over a word that is active.

   The convention is a claim about the run and not about the label, so read the
   pesukim under it before using it. Where his own words settle the case, as at
   עור and עמד, give his labels and not the convention. Whether the convention
   should stand at all, at a known failure rate of about one in twelve, is the
   site owner's call and not a drafter's.

5. **Do not narrate the entry.** "He brings X for reading Y" is about the page;
   what X reads, and why, is about the word. The exception is an entry that
   gives no gloss at all, where saying so plainly is the honest report of a thin
   entry.
6. **A part earns its place by being worth knowing.** Where his entry is one
   line, the gloss is one line.
7. **House voice**, as `CLAUDE.md` sets it: no em dashes, no AI register, no
   *whence*, frum register and Hebrew book names, Hashem.

## Three traps that have caught every wave

- **Quoting across a break.** Copy a run that is actually contiguous in his
  text. The commonest failure is quoting across the divine name or across a
  citation in parentheses, which makes a phrase he never wrote. Copy; do not
  retype from memory.
- **Verse numbers from memory.** Cite what his text prints, even where you are
  sure he is a pasuk off. Where his edition differs, say so: `(Ezra 1:4 in his
  edition)`.
- **A misprinted book is not an edition difference.** Where the chapter and
  pasuk are right and the book is not, as at שוע, where ולכילי לא יאמר שוע of
  Yeshayahu 32:5 is printed (במדבר לב, ה), do not write "Bamidbar 32:5 in his
  edition": that tells a reader his edition puts the pasuk in the Chumash, and
  Bamidbar 32:5 is a real pasuk about something else. Quote the phrase, give it
  its English, and leave it uncited.
- **Two of his own addresses swapped between two phrases** are the one case
  where you may repair a citation, because the repair uses nothing but his own
  text. At גדר he prints גדר דרכי בגזית as (איכה ג, ז) and גדר בעדי ולא אצא as
  (איכה ג, ט), and the two pesukim are the other way about. Both addresses are
  his, and the site shows a pasuk's words when a reader opens the citation, so
  printing them as he has them puts Hebrew on the screen that contradicts the
  Hebrew beside it. Pair each phrase with the pasuk whose words it actually is.
  This is not licence to correct a number you think is wrong: it applies only
  where he cites both pesukim himself and the texts settle which is which.
- **The same goes for a chapter number that lands somewhere real.** At כתר בי
  יכתירו צדיקים is printed (תהלים קטב, ח), a קטב for קמב: that reads as Tehillim
  111:8, a real pasuk and the wrong one, where the pasuk is 142:8. "In his
  edition" is for a number a pasuk or two out, not for one that sends a reader
  somewhere else entirely. The check cannot help here, since it reads his
  printed citation the same way you do and finds them agreeing; only your eye
  catches it. Quote the phrase, give it its English, leave it uncited.
- **Naming an authority he does not name.** Rabbi Yonah, Ibn Ezra, the Targum,
  Rav Saadiah Gaon, Rashi, the Mesorah, Chazal and the rest go in only where his
  Hebrew names them.
- **Giving the lemma a sense he reports in somebody else's name.** At קצה he
  explains אֶת־הֶעָפָר אֲשֶׁר הִקְצוּ as הסיעו אותו לקצה הבית, they moved the
  dust to the edge of the house, which is his own reading off קָצֶה, an edge;
  the peeling sense comes next and is Yonasan's, ויונתן תרגם לשון קלוף. A gloss
  that renders the lemma "the dust that they scraped off" has taken Yonasan's
  reading for the plain one, and his explanation then reads as a restatement of
  Yonasan rather than the alternative to him. Check whose the plain sense is
  before writing it as the word's.
- **A verb whose subject is the clause before.** At טטף ואמרו שהם ד' בתים
  follows רבותינו ז"ל, so the four batim are Chazal's count and not his ruling.
  ואמרו, ופירשו and the like carry the subject forward; read back to find it.
- **A Masoretic note inverted.** לית is "unique", never a denial: לית מלא the
  only one written full, לית חסר the only one defective, לית סגול the only one
  so pointed, ב' בתרי לישני twice in two senses. At אחז he writes שם איש and
  then cites והמסורת עליו לית שום בר נש in support of it; his own usage at חמם,
  לית קמץ וכל שום בר נש כותיה, shows שום בר נש is the category the word is
  unique within. A gloss that read it as "no man's name at all" had him citing
  a note against the reading he had just given.
- **A heading that settles what the part leaves open.** At דשׁן he writes והנה
  לא תרגם והדשן או תרגם אותו משרית אתורא, an either/or about Yonasan, and the
  heading had picked the first branch as fact. The heading may not decide what
  he declines to.
- **"He" straight after naming somebody else.** Throughout a gloss "he" is
  Radak, but in the sentence after another authority is named it reads as that
  authority. It matters most where he closes by endorsing a view: והוא נכון is
  "and it is correct", him affirming what he has just reported, and "and he
  holds that right" made it sound as though Rabbi Yehudah were approving his own
  filing. Name Radak there.

## Same letters, other word

A root's letters sometimes carry a word he treats and a word our entry means,
and his dictionary has only the first. Our throat entry names ג-ר-ן, and his
only entry under those letters is the threshing floor. Do not force a
connection: say plainly what his entry is about, which is what tells a reader
the two are different words.

## How to pick what to audit

Auditing by index, taking headwords in whatever order a list holds them, turns
up three or four faults in a batch of twenty-four. Auditing by *class* turns up
ten times that. The seam above is the class that has paid best: search his
Hebrew for an authority named (רבותינו, רבי יונה, רבי יהודה, אדני אבי, התרגום,
יונתן, אונקלוס, רבינו שלמה, אבן עזרא, יעקב בן אלעזר, הגאון, מנחם, יש מפרשים,
יש מי ש, ויש אומרים) followed within a couple of hundred characters by one of
his hand-off words (פירוש, כלומר, רצה לומר, רצונו לומר, והוא ש, ויש לפרש, ואף
על פי כן, ויתכן, ואין צורך, ולדעתי, ועל דעתי, ואני אומר), and audit those
headwords whose gloss names somebody. Twenty-nine such headwords held
twenty-eight faults. Rank them by the number of seams times the number of gloss
parts that name anyone, and the densest come first.

The reason it works is that the fault is structural and not random: the English
has to decide where one man stops speaking and the next begins, and his Hebrew
marks that boundary with a word rather than with punctuation.

## Checking

```
python tools/check_glosses.py --file <batch>.json   # a batch, before merging
python tools/check_glosses.py                       # the whole file
```

It must print no problems. It cannot tell whether the English renders the Hebrew
rightly, which is what a human review is for, and why a gloss stays `draft`
until a person has read one against its source.

**If the check is wrong, say so; do not work around it.** It has had real gaps
found this way: spellings the edition prints oddly (אבן עורא for Ibn Ezra, with
a vav for the zayin), word orders it did not know (ויונתן תרגם, which he uses
more often than the form the check knew), book names it misread (מלאכים for
מלכים, matching the prefix מלאכי and resolving to Malachi). Leave that gloss out
and report the refusal with the exact Hebrew, so the check can be fixed rather
than the prose bent around it. The same goes for an entry that looks corrupt at
the source: `נצח` is one, and saying so was worth more than a gloss papering
over it.
