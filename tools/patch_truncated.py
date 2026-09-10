"""Complete a truncated article from the author's Times of Israel mirror.

  python lexicon/tools/patch_truncated.py <raw file> <tail file> <mirror url>

`tail file` holds the FULL text of the article's final paragraph as it reads on
the mirror. The script finds where the stored body was cut, replaces the cut
paragraph with the complete one, and records the provenance in the front matter
so nobody later mistakes patched text for what ohr.edu served.

Why by hand: the ohr.edu API stores the truncation, so a refetch reproduces it,
and the mirror is behind Cloudflare for curl. The text is pulled with the
browser and pasted into `tail file`.
"""
import sys, pathlib, difflib


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    raw = pathlib.Path(sys.argv[1])
    tail = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8").strip()
    url = sys.argv[3]

    t = raw.read_text(encoding="utf-8")
    fm_end = t.index("\n---\n") + len("\n---\n")
    head, body = t[:fm_end], t[fm_end:]
    lines = body.rstrip().split("\n")
    idx = max(i for i, l in enumerate(lines) if l.strip())
    cut = lines[idx].strip()

    # The stored paragraph is a prefix of the true one; confirm before writing.
    norm = lambda s: " ".join(s.replace("*", "").replace("’", "'").split()).lower()
    if not norm(tail).startswith(norm(cut)[:60]):
        ratio = difflib.SequenceMatcher(None, norm(cut)[:200], norm(tail)[:200]).ratio()
        print(f"REFUSED: the tail does not continue the cut paragraph (similarity {ratio:.2f})")
        print(f"  stored: ...{cut[-90:]}")
        print(f"  mirror: {tail[:90]}...")
        return

    lines[idx] = tail
    gained = len(tail) - len(cut)
    if "completed_from:" not in head:
        head = head.replace("\n---\n",
                            f"\ncompleted_from: \"{url}\"  # ohr.edu's stored body is truncated; "
                            f"final paragraph restored from the author's mirror\n---\n", 1)
    raw.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"patched {raw.name}: +{gained} chars restored, provenance recorded")


if __name__ == "__main__":
    main()
