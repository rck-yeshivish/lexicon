"""Fetch the diaspora calendar from Hebcal into references/calendar.json.
  python tools/fetch_calendar.py [first_year] [last_year]   (default: this year + 3)

Keeps only what the home page's "This week" needs: the Shabbos parsha, the
Yamim Tovim and fasts, Rosh Chodesh, and the special Shabbosos. Hebcal's data
is CC BY 4.0 (hebcal.com); the site credits it.
"""
import datetime, json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "references" / "calendar.json"
URL = ("https://www.hebcal.com/hebcal?v=1&cfg=json&year={y}&i=off"
       "&maj=on&min=on&mod=off&nx=on&ss=on&s=on&mf=off&c=off&D=off&d=off&o=off")


def fetch(year):
    req = urllib.request.Request(URL.format(y=year), headers={"User-Agent": "whatsinaword-build"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["items"]


def main():
    this = datetime.date.today().year
    first = int(sys.argv[1]) if len(sys.argv) > 1 else this
    last = int(sys.argv[2]) if len(sys.argv) > 2 else this + 3
    items = []
    for y in range(first, last + 1):
        for i in fetch(y):
            items.append({"date": i["date"][:10], "category": i["category"],
                          "title": i["title"], "hebrew": i.get("hebrew", "")})
    items.sort(key=lambda i: (i["date"], i["title"]))
    OUT.write_text(json.dumps({"source": "Hebcal (hebcal.com), diaspora, CC BY 4.0",
                               "fetched": datetime.date.today().isoformat(),
                               "years": [first, last], "items": items},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(items)} items, {first} to {last}")


if __name__ == "__main__":
    main()
