"""Repair damage that came from ohr.edu's own API, not from our harvest.

  python lexicon/tools/repair_corpus.py --check     report damage, change nothing
  python lexicon/tools/repair_corpus.py --fix-encoding
  python lexicon/tools/repair_corpus.py --list-truncated

Two separate defects:

1. MANGLED HEBREW. The API serves some articles' Hebrew as UTF-8 bytes that were
   decoded as Windows-1252 upstream, so Hebrew arrives looking like a run of
   multiplication signs and accented Latin. The five bytes cp1252 leaves
   undefined (0x81 0x8D 0x8F 0x90 0x9D) came through as raw codepoints U+0081
   and friends. Reversing both together restores the original bytes exactly, so
   this is repaired locally with no refetch.

2. TRUNCATED BODIES. The API's stored body for a few articles stops mid-word.
   Nothing local can recover the missing text; it has to come from the author's
   Times of Israel mirror, which carries the full piece. --list-truncated names
   them; the recovered text is pasted in and the file records where it came from.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "whats-in-a-word" / "raw"

# cp1252 for the bytes it defines, raw codepoint for the five it does not.
CP1252_UNDEFINED = {0x81, 0x8D, 0x8F, 0x90, 0x9D}

# Every character a UTF-8-read-as-cp1252 pass can emit: the Latin-1 supplement
# (including those five undefined codepoints) plus the cp1252 specials that sit
# in 0x80-0x9F. Written as explicit escapes on purpose: putting the literal
# characters in this source file invites a second round of the very mangling
# the function undoes.
_MANGLE_CHARS = (
    "-ÿŒœŠšŸŽžƒˆ˜"
    "–—‘-„†-•…‰‹›€™"
)
_LEAD = "×Ã"          # the two bytes that begin a mangled Hebrew or accented run
MANGLED_RUN = re.compile(f"[{_MANGLE_CHARS}]*[{_LEAD}][{_MANGLE_CHARS}]*")


def unmangle(s):
    """Undo one UTF-8-read-as-cp1252 pass. None if this run is not that."""
    out = bytearray()
    for ch in s:
        cp = ord(ch)
        if cp in CP1252_UNDEFINED:
            out.append(cp)
            continue
        try:
            out.extend(ch.encode("cp1252"))
        except UnicodeEncodeError:
            return None
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return None


def is_mangled(t):
    return any(c in t for c in _LEAD)


# A sign-off is recognised by how the line OPENS, not by a word buried in it:
# "authored the works entitled Chatam Sofer" is body text, not an author bio.
SIGNOFF = re.compile(
    r"(in memory|memory of|nishmat|nishmas|l'?e?'?ilu[yi]|l'?zechut|le'?zechut|refuah|"
    r"dedicat|this issue|to be continued|rabbi reuven|author'?s? note|the author|"
    r"for questions|chazak|sponsor)", re.I)


def normalise(s):
    return s.replace("’", "'").replace("‘", "'")


def truncated_tail(t):
    """The tail of a body that stops mid-sentence, or None if it ends properly."""
    body = t.split("\n---\n", 1)[-1].rstrip()
    lines = [l for l in body.split("\n") if l.strip()]
    if not lines:
        return None
    last = normalise(lines[-1].strip().rstrip("*_ "))
    if re.search(r"[.!?…»”’\"'\)\]:]$", last):
        return None
    if SIGNOFF.search(last[:40]):        # a dedication announces itself up front
        return None
    return last[-100:]


def repair(t):
    def repl(m):
        r = unmangle(m.group(0))
        return r if r else m.group(0)
    return MANGLED_RUN.sub(repl, t)


def main():
    files = sorted(RAW.glob("*.md"))
    mangled = [p for p in files if is_mangled(p.read_text(encoding="utf-8"))]
    trunc = [(p, tail) for p in files
             if (tail := truncated_tail(p.read_text(encoding="utf-8")))]

    if "--fix-encoding" in sys.argv:
        fixed, failed = 0, []
        for p in mangled:
            t = p.read_text(encoding="utf-8")
            new = repair(t)
            if new != t and not is_mangled(new):
                p.write_text(new, encoding="utf-8")
                fixed += 1
            else:
                failed.append(p.name)
        print(f"encoding repaired in {fixed} files")
        for n in failed:
            print("  STILL MANGLED:", n)
        return

    if "--list-truncated" in sys.argv:
        for p, tail in trunc:
            print(f"{p.name}\n    ...{tail}")
        return

    print(f"{len(files)} articles")
    print(f"  mangled Hebrew: {len(mangled)}")
    for p in mangled:
        print("   ", p.name)
    print(f"  truncated bodies: {len(trunc)}")
    for p, tail in trunc:
        print(f"    {p.name}\n        ...{tail}")


if __name__ == "__main__":
    main()
