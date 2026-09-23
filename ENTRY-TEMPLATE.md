---
cluster: <one English label for the cluster, e.g. shame>
hebrew: [<unpointed Hebrew words, e.g. בושה, כלימה, חרפה>]
roots: [<root letters with hyphens, e.g. ב-ו-ש, כ-ל-ם, ח-ר-ף>]
translit: [<every plausible transliteration, Ashkenazi and Sephardi, e.g. bushah, busha, klimah, kelimah, cherpah, cherpa>]
english: [<the English glosses used in the Bottom line, e.g. shame, humiliation, disgrace>]
domain: <one of: emotion, cognition, speech, body, action, nature, ritual, society, time, quantity, other>
words:                    # one item per Hebrew word: its OWN English and what sets it apart.
  - he: <Hebrew word, unpointed>        # This block feeds the Hebrew headword table in INDEX.md,
    tr: <transliteration>               # so a reader who meets the word cold gets the ruling
    en: <its English rendering>         # without opening anything. Name the authority in `distinct`.
    distinct: <the one line that tells this word from its neighbours, with the authority in parentheses>
sources:
  - wiaw:<id> "<article title>" (<yyyy-mm-dd>) https://ohr.edu/<id>
authorities: [<names as the source gives them, e.g. Radak, Rabbeinu Yonah, Malbim, Rabbi Shlomo Pappenheim>]
updated: <yyyy-mm-dd>
---
# <Cluster>: <word> / <word> / <word>

## Bottom line

<Two to five lines. The rendering to use for each word, and the one fact a
translator must not get wrong (order, intensity, register, which is the general
term). Written so a model can stop reading here.>

## At a glance

| Hebrew | translit | English | what sets it apart |
|---|---|---|---|
| <word> | <translit> | <English> | <the distinguishing fact, authority in parens> |

## Where the authorities disagree

<Only when they do, and then always. Name each view and who holds it: "Bedersi
says klimah is the most intense; Malbim says chafrah." Say which the Bottom line
follows and why. Never flatten a dispute into one smooth answer. Delete this
heading if the sources genuinely agree.>

## Distinctions

### <word> (<Hebrew>)
<Root, core sense, what it adds against its neighbors, who says so.>

### <word> (<Hebrew>)
<...>

## Rendering guidance

<How to translate when the words appear together (a doubled pair, a list in
ascending order), traps (an English word that covers two of the Hebrew words),
and a sentence or two of worked example where the source gives one.>

## Notes for a project

<Optional, and usually "None yet." Where a project using this guide applied or
departed from the ruling above, one line saying which project and what it did.
Record the disagreement; do not resolve it. Projects should keep their rulings
in their own overlay file rather than accumulate them here.>

## Sources

<Restate the source line(s) in prose with the article title and link, plus any
primary loci the article cites (Radak to Yeshayahu 45:16; Sefer HaShorashim s.v.).>

<!-- Remove these angle-bracket placeholders entirely; keep every heading. -->
