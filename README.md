# GitHub Dashboard

One page indexing every public repo (mine + my orgs) and its live link.
Live: https://sanjaygupta-professional.github.io/dashboard

## How it works
`build.py` calls the GitHub API via `gh`, normalizes repos (`fetcher.py`),
and renders a self-contained `index.html` (`render.py`). The page embeds its
data as JSON and makes **no runtime API calls** — safe to host publicly.
Public repos only. A GitHub Action rebuilds it daily and on demand.

## Local build
    python3 build.py            # writes index.html
    python3 build.py --dry-run  # prints JSON, writes nothing
    python3 -m unittest discover -s tests

## REQUIRED one-time setup — Personal Access Token
The Action must read your *other* repos/orgs, which the default `GITHUB_TOKEN`
cannot. Create a PAT and store it as a secret:

1. https://github.com/settings/tokens → **Generate new token (classic)**.
2. Scopes: check **`repo`** and **`read:org`**. Pick an expiry.
3. Generate, copy the token.
4. In THIS repo: **Settings → Secrets and variables → Actions → New repository secret**.
5. Name: `GH_DASHBOARD_TOKEN`. Value: the token. Save.
6. Enable Pages: **Settings → Pages → Source: Deploy from a branch → `main` / root**.

Then trigger **Actions → Build dashboard → Run workflow** to verify.
