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
   English.
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
