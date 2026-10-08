"""List the passages a card shows on the strength of a match that may be a
homonym, and that no one has yet read.

A card for a daf or a commentary shows the passages holding the entry's words,
and finds them by spelling. A long word is itself (אושפיזא); a short one often
is not, and neither is a word that only shares a root: רָעָה, evil, in a
passage shown for rei'a, a friend; מהול, diluted, for a mohel; לימין for uman.
Each such passage is read once, with the entry's sense of the word in hand, and
judged in references/excerpt-senses.json: the entry, the source, the passage's
fingerprint, and the words in it that are not the entry's (an empty list where
all are). The build then leaves those words unmarked, and the card shows
another passage, or offers the text on Sefaria.

This runs the site build (it rewrites site/, as build_site.py does) and prints
what is left to judge, as JSON with --json.

    python tools/check_excerpts.py
    python tools/check_excerpts.py --json out.json
"""
import contextlib
import io
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build_site as B  # noqa: E402
import refs  # noqa: E402

SHORT = 3   # a headword of this many letters or fewer is a spelling many words share


def risky(marks):
    """Every word that put the passage on the card is short or only a root's."""
    return all(len(B.bare_word(m)) <= SHORT or not own for _w, m, own in marks)


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        B.main()
    judged = set(B.EXCERPT_NOT)
    seen, left = set(), []
    for entry, src, i, seg, marks in B.SHOWN:
        key = (entry, src, B.seg_id(seg))
        if key in seen or key in judged or not marks or not risky(marks):
            continue
        seen.add(key)
        left.append({"entry": entry, "src": src, "seg": key[2], "text": seg,
                     "marks": sorted({(w, m) for w, m, _own in marks})})
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        pathlib.Path(out).write_text(json.dumps(left, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        for r in left:
            print(f"{r['entry']} | {r['src']} | {', '.join(f'{w}={m}' for w, m in r['marks'])}\n    {r['text'][:160]}")
    print(f"{len(left)} to judge")


if __name__ == "__main__":
    main()
