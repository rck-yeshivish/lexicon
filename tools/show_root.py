"""Print Radak's entry for a root, and what our entries use it for.

  python tools/show_root.py שלח קרב        # by root letters, finals folded
  python tools/show_root.py --todo 20      # the roots with no English yet,
                                           # most cited first, with their text

Written for whoever is drafting references/radak-gloss.json, by hand or
otherwise: everything needed to write a gloss is here, and nothing has to be
fetched. GLOSS-BRIEF.md is the brief for writing them. A root he files under another headword prints that headword, and a
root he treats twice prints both entries.
"""
import json, pathlib, re, sys, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = str.maketrans("ךםןףץ", "כמנפצ")
LETTERS = re.compile("[א-ת]")


def fold(s):
    return "".join(LETTERS.findall(s)).translate(BASE)


def load():
    r = json.loads((ROOT / "references" / "shorashim.json").read_text(encoding="utf-8"))["roots"]
    g = json.loads((ROOT / "references" / "radak-gloss.json").read_text(encoding="utf-8"))["glosses"]
    return r, g


def uses():
    """root -> the clusters that name it, and the words they give it."""
    out = collections.defaultdict(lambda: {"clusters": [], "words": set()})
    for p in sorted((ROOT / "entries").glob("*.md")):
        src = p.read_text(encoding="utf-8")
        m = re.search(r"^roots: \[(.*)\]$", src, re.M)
        c = re.search(r"^cluster: (.+)$", src, re.M)
        h = re.search(r"^hebrew: \[(.*)\]$", src, re.M)
        words = [w.strip() for w in h.group(1).split(",")] if h else []
        for r in (m.group(1).split(",") if m else []):
            k = fold(r)
            if k:
                out[k]["clusters"].append(c.group(1).strip() if c else p.stem)
                out[k]["words"].update(words)
    return out


def show(key, roots, glosses, use):
    v = roots.get(key)
    print("=" * 72)
    u = use.get(key, {})
    print(f"ROOT {key}")
    if u.get("clusters"):
        print(f"  our entries: {', '.join(sorted(set(u['clusters'])))}")
    if not v:
        print("  (his dictionary has no entry for it)")
        return
    for p in [v] + v.get("more", []):
        note = f"   [he files our root under this headword]" if p.get("under") else ""
        done = "  [English already written]" if p["hw"] in glosses else ""
        print(f"\n-- headword {p['hw']}{note}{done}  ({len(p['text'])} characters)")
        print(p["text"])


def main():
    roots, glosses, use = *load(), uses()
    args = sys.argv[1:]
    if args[:1] == ["--finish"]:
        # Roots grouped by the entry they would complete, the entries nearest
        # done first. Working by root frequency leaves many entries showing
        # some of their roots in English and not others, which reads as a fault
        # rather than as work in progress; this finishes them one at a time.
        n = int(args[1]) if len(args) > 1 else 8
        done = lambda k: bool(roots.get(k)) and all(
            q["hw"] in glosses for q in [roots[k]] + roots[k].get("more", []))
        by_entry = {}
        for k, u in use.items():
            if not roots.get(k):
                continue
            for c in set(u["clusters"]):
                by_entry.setdefault(c, []).append(k)
        open_ = [(c, [k for k in ks if not done(k)], len(ks)) for c, ks in by_entry.items()]
        open_ = sorted((o for o in open_ if o[1]), key=lambda o: (len(o[1]), -o[2]))
        for c, left, total in open_[:n]:
            print(f"\n### {c}: {len(left)} of {total} roots still without English")
            print("   ", " ".join(left))
        print(f"\n[{len(open_)} entries not yet finished]")
        return
    if args[:1] == ["--todo"]:
        n = int(args[1]) if len(args) > 1 else 10
        want = sorted(use, key=lambda k: -len(use[k]["clusters"]))
        todo = [k for k in want if roots.get(k)
                and not all(p["hw"] in glosses for p in [roots[k]] + roots[k].get("more", []))]
        for k in todo[:n]:
            show(k, roots, glosses, use)
        print(f"\n[{len(todo)} roots still without English]")
        return
    for a in args:
        show(fold(a), roots, glosses, use)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
