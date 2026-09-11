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
    python tools/link_sources.py entries/a.md entries/b.md   # only these
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


SLUG_REF = re.compile("`([a-z0-9]+(?:-[a-z0-9]+)+)[.]md`")
CLUSTER = re.compile("^cluster:[ ]*(.+)$", re.M)


def crossrefs(text, names):
    """A pointer to another entry written as its file name becomes a link.

    "see `animal-behemah-chayah.md`" reads as a file path on the site; it
    becomes "see [animal](animal-behemah-chayah.html)", named for that entry's
    cluster. Entry pages sit side by side, so the bare file name is the link.
    """
    n = 0

    def sub(m):
        nonlocal n
        slug = m.group(1)
        if slug not in names:
            return m.group(0)
        n += 1
        return "[" + names[slug] + "](" + slug + ".html)"

    return SLUG_REF.sub(sub, text), n


def main():
    check = "--check" in sys.argv
    only = {Path(a).name for a in sys.argv[1:] if a.endswith(".md")}
    every = sorted((ROOT / "entries").glob("*.md"))
    names = {}
    for p in every:
        m = CLUSTER.search(p.read_text(encoding="utf-8").split(chr(10) + "---", 1)[0])
        if m:
            names[p.stem] = m.group(1).strip()
    total = files = refs = 0
    for p in every:
        if only and p.name not in only:
            continue
        t = p.read_text(encoding="utf-8")
        fm = t.split(chr(10) + "---", 1)[0]
        urls = {norm(m.group("title")): m.group("url") for m in SRC.finditer(fm)}
        new, n = link(t, urls)
        new, r = crossrefs(new, names)
        if n or r:
            files += 1
            total += n
            refs += r
            if not check:
                p.write_text(new, encoding="utf-8")
    verb = "would change" if check else "changed"
    print(f"{verb} {files} entr{'y' if files == 1 else 'ies'}: {total} citation fix(es), {refs} cross-reference link(s)")


if __name__ == "__main__":
    main()
