# GitHub Meta Dashboard — Design

**Date:** 2026-06-20
**Owner:** sanjaygupta-professional
**Status:** Approved design, pre-implementation

## Problem

Lots of repos created (50 public owned + 3 orgs), many recently, much meant to be
shared via deployed GitHub Pages links. After sharing, the link is forgotten — no
central index. Cognitive load of remembering "where is the link, what is that repo"
is too high. Need one window into the whole GitHub system: every repo + every live
deployed link, organized, searchable, shareable with others.

## Goal

A single public web page that is the canonical window to the user's GitHub world:
- Every public repo (owned + org), auto-pulled, no manual upkeep.
- Every live deployed link surfaced at the top (the share targets).
- Searchable, grouped by owner, always reasonably fresh.

## Non-Goals

- No private repo data on the public page (privacy).
- No topic-based grouping (0/50 repos have topics today; deferred — see Open Items).
- No live client-side GitHub API calls (would require exposing a token publicly).
- No analytics, no auth, no write-back to GitHub repos in v1.

## Decisions (from brainstorming)

| Question | Decision |
|----------|----------|
| Scope | All repos, auto-pulled (public only on public page) |
| Deploy links | Mostly GitHub Pages → auto-detected via API |
| Refresh + host | GitHub Pages + auto-refresh via GitHub Action |
| Private repos | Public repos only on the public page |
| Organization | Live-deploys hero on top, then grouped by owner/org, search box |
| Topics | Skipped for v1 (no repos have topics) |
| Repo home | sanjaygupta-professional/dashboard → Pages at sanjaygupta-professional.github.io/dashboard |

## Architecture

Three units, each independently testable.

### 1. Fetcher (build.py — fetch stage)
Uses gh api GraphQL + REST. Pulls:
- All **public** repos owned by the user.
- All **public** repos in every org the user belongs to (discovered via
  user/orgs, not hardcoded — today: rai-learning-map, copilot-sm-course,
  ai-research-money-map).
- Per repo: name, description, primaryLanguage, stargazerCount,
  pushedAt, url (html_url), homepageUrl, GitHub Pages URL.

**Live link resolution:** Pages URL (from repos/{owner}/{repo}/pages) when
has_pages, else homepageUrl when present → the repo's "live link". A repo with
neither = no live link (excluded from hero).

**Output:** a normalized JSON list of repo records. This is the unit's interface —
the renderer consumes JSON only, never calls the API.

### 2. Renderer (build.py — render stage)
Takes the JSON, emits one self-contained index.html:
- Anthropic / Claude parchment design system (per global CLAUDE.md). Georgia
  serif headings, parchment #f5f4ed, terracotta #c96442 accents. No purple,
  no glassmorphism.
- Data embedded as a <script> JSON blob → client-side JS does search/filter/
  collapse. **No network calls at runtime** → no token on the page.

**Page sections:**
1. Header — title, last-updated stamp, counts (N repos · M live sites · K orgs).
2. Search box — live filter across name + description + owner.
3. **Hero "Live Sites"** — one card per repo with a live link. Card: large title
   linking to the live site, secondary "repo →" link, description.
4. **Grouped repos** — collapsible <details> section per owner (You first, then
   each org alphabetically). Card: name → repo, live badge if deployed,
   description, language dot, star count, "updated Nd ago".

### 3. Refresh workflow (.github/workflows/build.yml)
- Triggers: daily schedule cron + workflow_dispatch (manual) + push to main.
- Steps: checkout → setup python + gh → run build.py → commit index.html if
  changed → GitHub Pages deploys from main.
- **Auth:** needs a Personal Access Token (classic: repo + read:org, or
  fine-grained equivalent) stored as Actions secret GH_DASHBOARD_TOKEN. The
  default GITHUB_TOKEN only sees the dashboard repo itself, not the user's other
  repos/orgs. **This PAT creation is the one manual human step** — documented in
  README with exact click-steps. Claude cannot create the PAT.

## Data Flow

```
gh API (GraphQL+REST) ──► Fetcher ──► normalized JSON ──► Renderer ──► index.html
                                                                          │
GitHub Action (cron/manual/push) ──── runs build.py ──── commits ────────┘
                                                                          │
                                                          GitHub Pages ──► public URL
```

## Error Handling

- gh not authed / rate-limited → fail loud with clear message, non-zero exit
  (Action surfaces failure). No partial/silent HTML.
- A repo missing optional fields (no description, no language) → render gracefully
  (omit the element), never crash.
- Pages API 404 for a repo → that repo simply has no live link; not an error.
- Build produces identical index.html when nothing changed → Action skips commit
  (no empty commits).

## Testing

- build.py --dry-run → dumps normalized JSON to stdout, makes no file changes.
- **Count assertion:** dry-run repo count == gh api user --jq .public_repos plus
  org public counts (sanity check fetch completeness).
- **Render snapshot:** feed a small fixture JSON (3 repos: one with Pages, one with
  homepage, one bare) → assert resulting HTML contains the hero card, the bare repo
  absent from hero, all three present in grouped list.
- Manual: open generated index.html locally, verify search + collapse work.

## Open Items / Future (not v1)

- Topic-based grouping — revisit by auto-tagging repos and writing topics back to
  GitHub (deferred; user chose org-grouping for v1).
- Optional second **private/local build** showing all repos including private.
- Possible later move to a dedicated meta-governance org.

## One-Time Human Steps

1. Create the public repo sanjaygupta-professional/dashboard (Claude can do via gh).
2. Enable GitHub Pages (source: main branch root) — Claude can do via gh api.
3. **Create PAT** (repo + read:org) and add as Actions secret
   GH_DASHBOARD_TOKEN — manual, user does this; README gives exact steps.
