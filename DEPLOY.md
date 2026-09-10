# Deploying to Cloudflare Pages

The site is a plain static folder. `site/` is generated, so build it first:

```bash
python tools/build_site.py
```

## Deploy only the built folder (recommended)

This uploads `site/` and nothing else, which is what keeps the harvested corpus
off the web. It is Rabbi Klein's and Ohr Somayach's copyright and must not be
published; only our own entries go up.

```bash
npx wrangler pages deploy site --project-name=lexicon
```

The first run opens a browser to authorise your Cloudflare account and creates
the project. Every later run is the same one line, and Cloudflare gives you a
`lexicon.pages.dev` URL plus a preview URL per deploy.

## The alternative, and why it is second choice

Cloudflare Pages can instead watch the GitHub repo and build on every push
(build command `python tools/build_site.py`, output directory `site`). It is
more automatic, but it clones the whole private repo into Cloudflare's build
environment, corpus included. Nothing is served from it, yet the copyrighted
text does leave your machine. Direct upload avoids that question entirely.

## Keeping it private

Cloudflare Access can put the whole site behind a login: Pages project →
Settings → Access policy. Worth doing while the entries are still marked
`status: draft`, since none of them has yet been read against its source by a
person.

## What gets served

| | |
|---|---|
| Pages | 342 entries, plus home, Hebrew and English browse |
| Data | one `data.json`, about 580 KB, fetched once and cached |
| Total | roughly 4.6 MB |

`_headers` sets long immutable caching on `/assets/*` and an hour on
`data.json`, so a redeploy of the data does not strand visitors on a stale copy.
