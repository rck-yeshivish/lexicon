"""List the citations whose commentator the site cannot tell by pattern.

A citation the entry gives as a commentator's ("Rashi to Beitzah 4a") opens his
comment; refs.subject() finds the plain forms. The rest name the commentator
some other way ("Rashi renders bitzah as maresc (to Yechezkel 47:11)", "Malbim
at Yeshayahu 19:5"), and the same words can also come before a citation that is
not his ("Tosafos point out that face appears with hishtachavaah as well
(Yeshayahu 49:23)" cites the pasuk). Only reading tells them apart, so each is
read once and judged in references/cite-commentators.json: the entry, the words
just before the list of citations, and whose comment the list is (an empty
list for no one's). This prints the ones not yet judged.

    python tools/cite_commentators.py            # what is left to judge
    python tools/cite_commentators.py --stale    # judged rows no entry has now
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import refs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = re.compile(r"(?<![\w-])(%s)\b(?!\s+(?:HaRosh|Yeshanim|Rid)\b)"
                   % refs._alt(set(refs.COMMENTARIES) | set(refs.TANACH_COMMENTARIES)))
# Where a clause ends: what comes before it is not about this citation.
CLAUSE = re.compile(r"[;:]|\.\s|\s-\s|\*\*|\|")
BEFORE = 50


def block_starts(body):
    """Where each block of an entry begins (a paragraph, a bullet, a heading, a
    table row), as offsets in it. A page holds each block apart, so what is
    before a block is never before a citation in it there."""
    starts, at, prev = [0], 0, ""
    for line in body.split("\n"):
        s = line.strip()
        if (not prev or prev.startswith(("#", "|")) or s.startswith(("#", "|"))
                or re.match(r"(?:[-*]|\d+\.)\s", s)):
            starts.append(at)
        at += len(line) + 1
        prev = s
    return starts


def candidates():
    """(entry, before, citation, names, context) for each list of citations
    with a commentator in its clause that the pattern does not place."""
    seen = set()
    for p in sorted((ROOT / "entries").glob("*.md")):
        raw = p.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        body, starts = raw.replace("\n", " "), block_starts(raw)
        for s, e, kind, _book, _name, pieces in refs.find(body):
            if kind not in ("tanach", "bavli"):
                continue
            head = refs.list_head(body[max(b for b in starts if b <= s):s])
            clause = re.sub(r"^[-*]\s+|^#+\s+", "", CLAUSE.split(head)[-1].lstrip())
            names = NAMES.findall(clause)
            if not names or refs.subject(head, kind == "tanach"):
                continue
            # The row is keyed on the clause alone: on the page a bullet or a
            # paragraph is its own block, and what came before it is not there.
            before = clause[-BEFORE:]
            if (p.stem, before) in seen:
                continue
            seen.add((p.stem, before))
            yield p.stem, before, body[s:e], list(dict.fromkeys(names)), refs.plain(body[max(0, s - 220):e + 80])


def main():
    if "--stale" in sys.argv:
        live = {(c[0], c[1]) for c in candidates()}
        for entry, rows in sorted(refs._BY.items()):
            for r in rows:
                if (entry, r["before"]) not in live:
                    print(f"{entry}: {r['before']!r}")
        return
    left = [c for c in candidates() if not any(r["before"] == c[1] for r in refs._BY.get(c[0], []))]
    for entry, before, cite, names, context in left:
        print(f"{entry} | {', '.join(names)} | {before!r} | {cite}\n    {context}")
    print(f"{len(left)} to judge")


if __name__ == "__main__":
    main()
