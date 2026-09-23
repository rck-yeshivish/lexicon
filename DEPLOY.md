# Deploying

The site is live at **https://whatsinaword.pages.dev**

Every push to `main` builds and deploys it, so ordinarily there is nothing to
run. `site/` is generated, so to deploy by hand, build first:

```bash
python tools/build_site.py
npx wrangler pages deploy site --project-name=whatsinaword --branch=main
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
| `CLOUDFLARE_API_TOKEN` | a token with the **Edit Cloudflare Workers** template |
| `CLOUDFLARE_ACCOUNT_ID` | `bcb0f74507b5013b6b3188ef7a30a267` |

Create the token at **My Profile → API Tokens → Create Token** in the
Cloudflare dashboard.

### Why not Cloudflare's own Git integration

It would clone the whole repository into Cloudflare's build environment, corpus
included. GitHub already holds this repo, so building on a GitHub runner adds
no new party to the copyrighted text, and only `site/` reaches Cloudflare.

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
