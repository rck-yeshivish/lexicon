# Deploying

The site is live at **https://whatsinaword.yehron.workers.dev**

`site/` is generated, so build before deploying:

```bash
python tools/build_site.py
npx wrangler deploy
```

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

Cloudflare Pages is now part of Workers, so new projects deploy to
`*.workers.dev` rather than `*.pages.dev`. The site is the same static site
either way. Deploying to the older Pages platform, and a `pages.dev` address,
means re-running the create command with `--force`.

## Before sharing the link

The site is publicly readable, and every entry is still `status: draft`:
sourced and lint-clean, but not yet read against its source by a person.
Cloudflare Access can gate the whole site in the meantime, under the project's
**Settings → Access policy**.

## Building on Cloudflare instead of here

Cloudflare Pages can also watch the repo and build on every push (build command
`python tools/build_site.py`, output directory `site`, project name
`whatsinaword`). We do not use it: it clones the whole repository into
Cloudflare's build environment, corpus included, where GitHub Actions already
holds the repo and uploads only `site/`. Kept here in case that trade ever
looks different.
