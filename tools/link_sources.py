"""Tidy each entry's Sources section: link the essay, plain-label the list.

The citation line is written as
    Rabbi Reuven Chaim Klein, "<title>," *What's in a Word?*, Ohr Somayach, <date>.
and the front matter's `sources:` list already carries each essay's ohr.edu
address. This matches them by title and turns the title into a link, so every
citation on the site opens the essay itself. It is idempotent: a title that is
already a link is left alone.

It also relabels the list of texts. Drafts wrote that line as "Loci:", which is
Latin scholars' shorthand most readers do not know; it reads "Cited in the
essay:" instead.

    python tools/link_sources.py            # rewrite in place
    python tools/link_sources.py --check    # report only
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = re.compile(r'^\s+- wiaw:\d+ "(?P<title>.+)" \(\d{4}-\d{2}-\d{2}\) (?P<url>https://articles\.ohr\.edu/articles/[a-z0-9-]+)\s*$', re.M)


def norm(t):
    return re.sub("[^a-z0-9]+", " ", t.lower().replace("\u2019", "'")).strip()


def link(text, urls):
    head, sep, tail = text.partition("## Sources")
    if not sep:
        return text, 0
    n = 0

    def sub(m):
        nonlocal n
        title = m.group(2)
        url = urls.get(norm(title))
        if not url:
            return m.group(0)
        n += 1
        return m.group(1) + "[" + title + "](" + url + ")" + m.group(3)

    # "Rabbi Reuven Chaim Klein, "Title," ..." -> title becomes a link.
    # A title already written as [Title](url) has no bare quote run, so it is skipped.
    tail = re.sub(r'(Rabbi Reuven Chaim Klein, ")([^"\[\]]+?)(,?")', sub, tail)
    relabeled = re.sub("(?m)^Loci:", "Cited in the essay:", tail)
    if relabeled != tail:
        n += 1
        tail = relabeled
    return head + sep + tail, n


def main():
    check = "--check" in sys.argv
    total = files = 0
    for p in sorted((ROOT / "entries").glob("*.md")):
        t = p.read_text(encoding="utf-8")
        fm = t.split("\n---", 1)[0]
        urls = {norm(m.group("title")): m.group("url") for m in SRC.finditer(fm)}
        new, n = link(t, urls)
        if n:
            files += 1
            total += n
            if not check:
                p.write_text(new, encoding="utf-8")
    verb = "would link" if check else "linked"
    print(f"{verb} {total} citation(s) in {files} entr{'y' if files == 1 else 'ies'}")


if __name__ == "__main__":
    main()
