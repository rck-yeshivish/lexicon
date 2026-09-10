# Connecting this repo to Cloudflare Pages

Cloudflare builds the site itself from this repo, so nothing generated needs to
be committed. Create the project from the dashboard: **Workers & Pages → Create
→ Pages → Connect to Git**, pick `lexicon`, then set:

| Setting | Value |
|---|---|
| Framework preset | None |
| Build command | `python tools/build_site.py` |
| Build output directory | `site` |
| Root directory | *(leave blank)* |

Nothing else is needed. There is no `package.json`, no dependencies to install,
and the build takes seconds: the script reads `entries/` and writes `site/`.

`.python-version` pins 3.11. Without it a build image still on v1 would use
Python 2.7 and fail on the first f-string. The script needs nothing newer than
3.8, so 3.11 is a safe floor that works on every current image.

## The trade-off worth knowing

Git integration clones the **whole repository** into Cloudflare's build
environment, including `sources/whats-in-a-word/raw/`. Those 374 essays are
Rabbi Klein's and Ohr Somayach's copyright. They are never *served*, since only
`site/` is published and the build never copies them there, but they do leave
your machine and sit in a build environment.

If you would rather they did not, deploy the built folder directly instead and
skip Git integration entirely:

```bash
npx wrangler pages deploy site --project-name=lexicon
```

That uploads `site/` and nothing else. The cost is that you run one command
after each change rather than getting a deploy on every push.

## Either way, before it is public

- A Pages project is reachable at `lexicon.pages.dev` by default.
- All 342 entries are `status: draft`: sourced and lint-clean, but not yet read
  against their sources by a person.
- **Workers & Pages → your project → Settings → Access policy** puts the whole
  site behind a Cloudflare Access login, which is worth having while that is
  still true.
