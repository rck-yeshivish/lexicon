# Deploying

The site is live at **https://whatsinaword.pages.dev**

It lives on the Cloudflare account `Yeshivish@gmail.com's Account`
(`0a49ac6b67a80b90d2c1d3a3130c7b12`). It moved there on 4 November 2026 from
`Yehron@gmail.com's Account`, keeping its address and its page-view count.

Every push to `main` builds and deploys it, so ordinarily there is nothing to
run. `site/` is generated, so to deploy by hand, build first. A login that
reaches more than one account has to be told which, or wrangler will ask:

```bash
python tools/build_site.py
CLOUDFLARE_ACCOUNT_ID=0a49ac6b67a80b90d2c1d3a3130c7b12 npx wrangler pages deploy site --project-name=whatsinaword --branch=main
```

It must be `pages deploy`, and the same is true in the workflow. Plain `wrangler
deploy` publishes a *Worker* to `whatsinaword.yehron.workers.dev`, which is a
second and separate copy of the site rather than an update to this one. There is
one such Worker, left over from before the workflow existed, still serving the
site as it stood on 10 September with 342 entries. Check `data.json` for
`"built"` to see which copy you are looking at.

`wrangler.jsonc` holds the project name and points at `site/` as the asset
directory. Only that directory is uploaded, which is what keeps the harvested
corpus in `sources/` off the web.

## Automatic deploys

`.github/workflows/deploy.yml` rebuilds and deploys on every push to `main`.
It lints the entries first and refuses to deploy if the corpus ever appears in
the payload.

It needs two repository secrets, under **Settings → Secrets and variables →
Actions** on GitHub:

| Secret | Value |
|---|---|
| `CLOUDFLARE_API_TOKEN` | a token with the **Edit Cloudflare Workers** template, scoped to the Yeshivish account |
| `CLOUDFLARE_ACCOUNT_ID` | `0a49ac6b67a80b90d2c1d3a3130c7b12` |

Create the token at **My Profile → API Tokens → Create Token** in the
Cloudflare dashboard.

### Why not Cloudflare's own Git integration

It would clone the whole repository into Cloudflare's build environment, corpus
included. GitHub already holds this repo, so building on a GitHub runner adds
no new party to the copyrighted text, and only `site/` reaches Cloudflare.

## The page-view counter

The home page's footer says how many pages have been viewed since 6 October
2026. Every page posts once to `/api/hit` as it loads, which adds one;
`functions/api/hit.js` answers it, and `pages deploy` picks up the `functions/`
folder from the repository root. The number lives in a one-row table in the D1
database `whatsinaword-hits`, bound as `HITS` in `wrangler.jsonc`. Nothing about
the visitor is kept, only the total and the date it started. A view is any page
load that runs the script, so it counts reloads and our own visits, and not
crawlers that skip JavaScript.

To look at it or set it back:

```bash
npx wrangler d1 execute whatsinaword-hits --remote --command "SELECT * FROM hits"
npx wrangler d1 execute whatsinaword-hits --remote --command "UPDATE hits SET n = 0, since = '<d Month yyyy>' WHERE id = 1"
```

A local `python -m http.server` preview has no counter, and the footer line
stays hidden there. `wrangler pages dev site --d1 HITS=<database id>` runs one
against a local copy of the table.

## A note on the URL

Cloudflare Pages is now part of Workers, and a new project deploys to
`*.workers.dev` rather than `*.pages.dev`. This project predates that and lives
on Pages, which is why the workflow says `pages deploy` and why the live address
is `whatsinaword.pages.dev`.

That matters because the two commands do not compete: they publish to two
different places. A `wrangler deploy` run on 10 September created a Worker at
`whatsinaword.yehron.workers.dev`, and because nothing ran it again, that copy
sat at 342 entries while Pages moved on, publicly readable and eight days out of
date. It was deleted on 18 September and that address now returns 404. If a
`wrangler deploy` is ever run here again it will recreate it, which is the
reason this file no longer gives that command anywhere.

## Before sharing the link

The site is publicly readable. Cloudflare Access can gate the whole site if it
should not be, under the project's **Settings → Access policy**.

## Building on Cloudflare instead of here

Cloudflare Pages can also watch the repo and build on every push (build command
`python tools/build_site.py`, output directory `site`, project name
`whatsinaword`). We do not use it: it clones the whole repository into
Cloudflare's build environment, corpus included, where GitHub Actions already
holds the repo and uploads only `site/`. Kept here in case that trade ever
looks different.
