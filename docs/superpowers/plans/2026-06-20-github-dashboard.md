# GitHub Meta Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One self-contained, auto-refreshed public HTML page indexing every public repo (owned + org) with its live GitHub Pages link, searchable and grouped by owner.

**Architecture:** A pure-Python `build.py` orchestrates two stdlib-only modules — `fetcher.py` (shells out to `gh api`, returns normalized repo records) and `render.py` (records → static `index.html` with embedded JSON + client-side search). No runtime API calls in the page → no token exposure. A GitHub Action reruns `build.py` daily/on-demand and commits the HTML; GitHub Pages serves it.

**Tech Stack:** Python 3.12 stdlib only (`subprocess`, `json`, `html`, `datetime`, `argparse`), `unittest`. `gh` CLI for data. GitHub Actions + Pages.

## Global Constraints

- Python 3 stdlib only — NO third-party packages (keeps CI dependency-free).
- Tests use `unittest` (`python -m unittest`), not pytest.
- Public repos only in output — every fetch path filters `private == true` out.
- Design system: Anthropic parchment (bg `#f5f4ed`, card `#faf9f5`, accent terracotta `#c96442`, text `#141413`). Georgia serif headings. NO purple, NO glassmorphism, NO pure-white bg.
- Page makes ZERO network calls at runtime (data embedded as JSON).
- Repo home: `sanjaygupta-professional/dashboard`; live at `sanjaygupta-professional.github.io/dashboard`.
- Owner login: `sanjaygupta-professional`.

---

## File Structure

- Create `fetcher.py` — gh calls + normalization. Responsibility: GitHub → list of repo dicts.
- Create `render.py` — records → HTML string. Responsibility: presentation only.
- Create `build.py` — CLI entry: orchestrate fetch + render + write file; `--dry-run` prints JSON.
- Create `tests/test_fetcher.py` — normalization + live-link resolution unit tests.
- Create `tests/test_render.py` — render snapshot/content assertions on fixtures.
- Create `tests/fixtures/raw_repos.json` — sample raw `gh` repo objects.
- Create `.github/workflows/build.yml` — refresh workflow.
- Create `README.md` — usage + the manual PAT step.
- Generated at runtime: `index.html`.

---

### Task 1: Project scaffold + normalization (fetcher core)

**Files:**
- Create: `fetcher.py`
- Create: `tests/test_fetcher.py`
- Create: `tests/fixtures/raw_repos.json`

**Interfaces:**
- Produces: `normalize(raw: dict, user_login: str) -> dict` returning a record with keys
  `name, owner, description, language, stars, pushed_at, repo_url, live_url, is_owner`.
  `live_url` = `homepage` if non-empty, else `https://{owner}.github.io/{name}` when `has_pages` is true, else `None`.
- Produces: `record_sort_key(rec) -> tuple` sorting by `pushed_at` descending (newest first).

- [ ] **Step 1: Write fixture** `tests/fixtures/raw_repos.json`

```json
[
  {"name":"alpha-site","private":false,"description":"A deployed site","language":"HTML","stargazers_count":3,"pushed_at":"2026-06-18T10:00:00Z","html_url":"https://github.com/sanjaygupta-professional/alpha-site","homepage":"","has_pages":true,"owner":{"login":"sanjaygupta-professional"}},
  {"name":"beta-tool","private":false,"description":"CLI with external deploy","language":"Go","stargazers_count":0,"pushed_at":"2026-06-10T08:00:00Z","html_url":"https://github.com/sanjaygupta-professional/beta-tool","homepage":"https://beta.example.com","has_pages":false,"owner":{"login":"sanjaygupta-professional"}},
  {"name":"gamma-lib","private":false,"description":null,"language":null,"stargazers_count":1,"pushed_at":"2026-05-01T08:00:00Z","html_url":"https://github.com/rai-learning-map/gamma-lib","homepage":"","has_pages":false,"owner":{"login":"rai-learning-map"}},
  {"name":"secret-x","private":true,"description":"hidden","language":"Python","stargazers_count":0,"pushed_at":"2026-06-19T08:00:00Z","html_url":"https://github.com/sanjaygupta-professional/secret-x","homepage":"","has_pages":false,"owner":{"login":"sanjaygupta-professional"}}
]
```

- [ ] **Step 2: Write the failing test** `tests/test_fetcher.py`

```python
import json, os, unittest
import fetcher

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "raw_repos.json")
USER = "sanjaygupta-professional"

class TestNormalize(unittest.TestCase):
    def setUp(self):
        with open(FIX) as f:
            self.raw = json.load(f)

    def test_pages_repo_live_url_constructed(self):
        rec = fetcher.normalize(self.raw[0], USER)
        self.assertEqual(rec["live_url"], "https://sanjaygupta-professional.github.io/alpha-site")
        self.assertTrue(rec["is_owner"])

    def test_homepage_overrides_pages(self):
        rec = fetcher.normalize(self.raw[1], USER)
        self.assertEqual(rec["live_url"], "https://beta.example.com")

    def test_bare_repo_no_live_url(self):
        rec = fetcher.normalize(self.raw[2], USER)
        self.assertIsNone(rec["live_url"])
        self.assertFalse(rec["is_owner"])
        self.assertEqual(rec["owner"], "rai-learning-map")
        self.assertEqual(rec["description"], "")
        self.assertEqual(rec["language"], "")

    def test_sort_key_newest_first(self):
        recs = [fetcher.normalize(r, USER) for r in self.raw]
        recs.sort(key=fetcher.record_sort_key)
        self.assertEqual(recs[0]["name"], "alpha-site")  # but secret-x is newer

if __name__ == "__main__":
    unittest.main()
```

Note: `secret-x` is newest but is private; sorting here operates on whatever list it's given (filtering happens in Task 2). Fix the assertion to reflect raw sort:

```python
    def test_sort_key_newest_first(self):
        recs = [fetcher.normalize(r, USER) for r in self.raw]
        recs.sort(key=fetcher.record_sort_key)
        self.assertEqual(recs[0]["name"], "secret-x")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m unittest tests.test_fetcher -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetcher'`

- [ ] **Step 4: Write minimal `fetcher.py`**

```python
"""Fetch GitHub repos via gh CLI and normalize to dashboard records."""
import json
import subprocess


def normalize(raw, user_login):
    owner = raw["owner"]["login"]
    homepage = (raw.get("homepage") or "").strip()
    if homepage:
        live_url = homepage
    elif raw.get("has_pages"):
        live_url = "https://{}.github.io/{}".format(owner, raw["name"])
    else:
        live_url = None
    return {
        "name": raw["name"],
        "owner": owner,
        "description": (raw.get("description") or "").strip(),
        "language": raw.get("language") or "",
        "stars": raw.get("stargazers_count", 0),
        "pushed_at": raw.get("pushed_at") or "",
        "repo_url": raw["html_url"],
        "live_url": live_url,
        "is_owner": owner == user_login,
    }


def record_sort_key(rec):
    # Newest pushed first: invert by using reverse-sortable string trick.
    # pushed_at is ISO8601 UTC (lexicographically sortable); negate via tuple.
    return (rec["pushed_at"] == "", _neg(rec["pushed_at"]))


def _neg(s):
    # Lexicographic descending: map each char to its complement so sort asc == date desc.
    return "".join(chr(0x10FFFF - ord(c)) if ord(c) < 0x10FFFF else c for c in s)
```

Simpler alternative if `_neg` feels brittle — sort ascending then reverse in caller. To keep the test (`sort(key=...)` ascending → newest first), use:

```python
def record_sort_key(rec):
    return rec["pushed_at"]  # ascending = oldest first
```

and change the test + Task 2 to call `recs.sort(key=record_sort_key, reverse=True)`. **Decision: use the simple key + `reverse=True` everywhere.** Replace Step 2's sort test with:

```python
    def test_sort_key_newest_first(self):
        recs = [fetcher.normalize(r, USER) for r in self.raw]
        recs.sort(key=fetcher.record_sort_key, reverse=True)
        self.assertEqual(recs[0]["name"], "secret-x")
```

and `fetcher.py`:

```python
def record_sort_key(rec):
    return rec["pushed_at"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/sanjayg4/dashboard && python -m unittest tests.test_fetcher -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
cd /home/sanjayg4/dashboard
git add fetcher.py tests/test_fetcher.py tests/fixtures/raw_repos.json
git commit -m "feat: repo normalization + live-link resolution"
```

---

### Task 2: Live fetch + public-only collection

**Files:**
- Modify: `fetcher.py`
- Modify: `tests/test_fetcher.py`

**Interfaces:**
- Consumes: `normalize`, `record_sort_key` from Task 1.
- Produces: `collect(run=_run_gh) -> dict` returning
  `{"user": login, "records": [record,...], "orgs": [org,...], "counts": {"repos": n, "live": m, "orgs": k}}`.
  `run` is an injectable callable `(list[str]) -> str` (stdout) so tests stub gh.
- Produces: `_run_gh(args: list[str]) -> str` — real subprocess runner (`gh` + args, returns stdout, raises on failure).

- [ ] **Step 1: Write the failing test** (append to `tests/test_fetcher.py`)

```python
class TestCollect(unittest.TestCase):
    def setUp(self):
        with open(FIX) as f:
            self.raw = json.load(f)

    def _fake_run(self, args):
        # Route gh calls by endpoint.
        joined = " ".join(args)
        if "user" == args[-1] or args[-1].endswith("/user"):
            return json.dumps({"login": USER})
        if "user/orgs" in joined:
            return json.dumps([{"login": "rai-learning-map"}])
        if "user/repos" in joined:
            return json.dumps([r for r in self.raw if r["owner"]["login"] == USER])
        if "orgs/rai-learning-map/repos" in joined:
            return json.dumps([r for r in self.raw if r["owner"]["login"] == "rai-learning-map"])
        return "[]"

    def test_collect_excludes_private(self):
        out = fetcher.collect(run=self._fake_run)
        names = [r["name"] for r in out["records"]]
        self.assertNotIn("secret-x", names)
        self.assertIn("alpha-site", names)
        self.assertIn("gamma-lib", names)

    def test_collect_counts(self):
        out = fetcher.collect(run=self._fake_run)
        self.assertEqual(out["counts"]["repos"], 3)
        self.assertEqual(out["counts"]["live"], 2)  # alpha (pages) + beta (homepage)
        self.assertEqual(out["user"], USER)

    def test_collect_sorted_newest_first(self):
        out = fetcher.collect(run=self._fake_run)
        self.assertEqual(out["records"][0]["name"], "alpha-site")  # newest public
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/sanjayg4/dashboard && python -m unittest tests.test_fetcher.TestCollect -v`
Expected: FAIL — `AttributeError: module 'fetcher' has no attribute 'collect'`

- [ ] **Step 3: Implement in `fetcher.py`**

```python
def _run_gh(args):
    proc = subprocess.run(
        ["gh"] + args,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("gh {} failed: {}".format(" ".join(args), proc.stderr.strip()))
    return proc.stdout


def _api(run, endpoint):
    # Paginated REST list -> concatenated JSON arrays handled by gh --slurp.
    out = run(["api", "--paginate", "--slurp", endpoint])
    pages = json.loads(out)
    # --slurp wraps paginated arrays in an outer array; flatten.
    flat = []
    for page in pages:
        if isinstance(page, list):
            flat.extend(page)
        else:
            flat.append(page)
    return flat


def collect(run=_run_gh):
    login = json.loads(run(["api", "user"]))["login"]
    orgs = [o["login"] for o in json.loads(run(["api", "user/orgs"]))]

    raw = _api(run, "user/repos?per_page=100&affiliation=owner")
    for org in orgs:
        raw.extend(_api(run, "orgs/{}/repos?per_page=100".format(org)))

    records = [normalize(r, login) for r in raw if not r.get("private")]
    # De-dup by (owner, name) in case of overlap.
    seen, deduped = set(), []
    for r in records:
        key = (r["owner"], r["name"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    deduped.sort(key=record_sort_key, reverse=True)

    live = sum(1 for r in deduped if r["live_url"])
    return {
        "user": login,
        "orgs": orgs,
        "records": deduped,
        "counts": {"repos": len(deduped), "live": live, "orgs": len(orgs)},
    }
```

Note: the test's `_fake_run` returns plain arrays (not slurp-wrapped). Make `_api` robust: if `run` is the injected fake, `--slurp` isn't applied by it — it just returns the array. Handle both by detecting top-level shape:

```python
def _api(run, endpoint):
    out = run(["api", "--paginate", "--slurp", endpoint])
    data = json.loads(out)
    flat = []
    if isinstance(data, list) and data and isinstance(data[0], list):
        for page in data:
            flat.extend(page)
    elif isinstance(data, list):
        flat = data
    else:
        flat = [data]
    return flat
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /home/sanjayg4/dashboard && python -m unittest tests.test_fetcher -v`
Expected: PASS (all fetcher tests)

- [ ] **Step 5: Smoke test against real GitHub**

Run: `cd /home/sanjayg4/dashboard && python -c "import fetcher,json; print(fetcher.collect()['counts'])"`
Expected: prints a dict like `{'repos': 50+, 'live': N, 'orgs': 3}` with no error.

- [ ] **Step 6: Commit**

```bash
cd /home/sanjayg4/dashboard
git add fetcher.py tests/test_fetcher.py
git commit -m "feat: collect public repos across user + orgs"
```

---

### Task 3: Renderer

**Files:**
- Create: `render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: collect() output shape (records + counts + user) from Task 2.
- Produces: `render(data: dict, generated_at: str) -> str` (full HTML document).
- Produces: `time_ago(iso: str, now: datetime) -> str` (e.g. "3d ago", "2mo ago", "today").

- [ ] **Step 1: Write the failing test** `tests/test_render.py`

```python
import json, os, unittest
from datetime import datetime, timezone
import render

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "raw_repos.json")

def sample_data():
    return {
        "user": "sanjaygupta-professional",
        "orgs": ["rai-learning-map"],
        "counts": {"repos": 3, "live": 2, "orgs": 1},
        "records": [
            {"name":"alpha-site","owner":"sanjaygupta-professional","description":"A deployed site","language":"HTML","stars":3,"pushed_at":"2026-06-18T10:00:00Z","repo_url":"https://github.com/sanjaygupta-professional/alpha-site","live_url":"https://sanjaygupta-professional.github.io/alpha-site","is_owner":True},
            {"name":"beta-tool","owner":"sanjaygupta-professional","description":"CLI","language":"Go","stars":0,"pushed_at":"2026-06-10T08:00:00Z","repo_url":"https://github.com/sanjaygupta-professional/beta-tool","live_url":"https://beta.example.com","is_owner":True},
            {"name":"gamma-lib","owner":"rai-learning-map","description":"","language":"","stars":1,"pushed_at":"2026-05-01T08:00:00Z","repo_url":"https://github.com/rai-learning-map/gamma-lib","live_url":None,"is_owner":False},
        ],
    }

class TestRender(unittest.TestCase):
    def setUp(self):
        self.html = render.render(sample_data(), "2026-06-20")

    def test_is_html_document(self):
        self.assertTrue(self.html.lstrip().startswith("<!DOCTYPE html>"))

    def test_hero_has_live_repos_only(self):
        hero = self.html.split("<!-- GROUPS -->")[0]
        self.assertIn("alpha-site", hero)
        self.assertIn("beta-tool", hero)
        self.assertNotIn("gamma-lib", hero)  # no live link -> not in hero

    def test_all_repos_in_groups(self):
        self.assertIn("gamma-lib", self.html)
        self.assertIn("rai-learning-map", self.html)

    def test_counts_rendered(self):
        self.assertIn("3", self.html)
        self.assertIn("live sites", self.html.lower())

    def test_no_purple_or_white_bg(self):
        low = self.html.lower()
        self.assertNotIn("a78bfa", low)
        self.assertNotIn("6c8fff", low)
        self.assertIn("#f5f4ed", low)  # parchment present

    def test_html_escaping(self):
        data = sample_data()
        data["records"][0]["description"] = "x <script>alert(1)</script>"
        html = render.render(data, "2026-06-20")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_embedded_json_no_runtime_fetch(self):
        self.assertNotIn("api.github.com", self.html)
        self.assertNotIn("fetch(", self.html)

class TestTimeAgo(unittest.TestCase):
    def test_today(self):
        now = datetime(2026,6,20,tzinfo=timezone.utc)
        self.assertEqual(render.time_ago("2026-06-20T01:00:00Z", now), "today")
    def test_days(self):
        now = datetime(2026,6,20,tzinfo=timezone.utc)
        self.assertEqual(render.time_ago("2026-06-17T01:00:00Z", now), "3d ago")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/sanjayg4/dashboard && python -m unittest tests.test_render -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'render'`

- [ ] **Step 3: Implement `render.py`**

```python
"""Render dashboard records into a self-contained parchment-styled HTML page."""
import html
import json
from datetime import datetime, timezone

PALETTE = {
    "bg": "#f5f4ed", "bg2": "#faf9f5", "bg3": "#e8e6dc",
    "border": "#e8e6dc", "accent": "#c96442", "text": "#141413",
    "muted": "#5e5d59", "text3": "#87867f",
}


def time_ago(iso, now=None):
    if not iso:
        return ""
    now = now or datetime.now(timezone.utc)
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (now - dt).days
    if days <= 0:
        return "today"
    if days < 30:
        return "{}d ago".format(days)
    if days < 365:
        return "{}mo ago".format(days // 30)
    return "{}y ago".format(days // 365)


def _esc(s):
    return html.escape(s or "")


def _lang_dot(lang):
    if not lang:
        return ""
    return '<span class="lang"><span class="dot"></span>{}</span>'.format(_esc(lang))


def _card(rec, now):
    live = ""
    if rec["live_url"]:
        live = '<a class="badge" href="{}" target="_blank" rel="noopener">live ↗</a>'.format(_esc(rec["live_url"]))
    desc = '<p class="desc">{}</p>'.format(_esc(rec["description"])) if rec["description"] else ""
    meta_bits = [b for b in [
        _lang_dot(rec["language"]),
        ('<span>★ {}</span>'.format(rec["stars"]) if rec["stars"] else ""),
        ('<span>{}</span>'.format(time_ago(rec["pushed_at"], now)) if rec["pushed_at"] else ""),
    ] if b]
    return (
        '<div class="card" data-search="{search}">'
        '<div class="card-top"><a class="repo" href="{repo}" target="_blank" rel="noopener">{name}</a>{live}</div>'
        '{desc}<div class="meta">{meta}</div></div>'
    ).format(
        search=_esc((rec["name"] + " " + rec["description"] + " " + rec["owner"]).lower()),
        repo=_esc(rec["repo_url"]), name=_esc(rec["name"]),
        live=live, desc=desc, meta="".join(meta_bits),
    )


def _hero(records, now):
    live = [r for r in records if r["live_url"]]
    if not live:
        return ""
    cards = "".join(
        '<a class="hero-card" href="{url}" target="_blank" rel="noopener" data-search="{search}">'
        '<span class="hero-name">{name}</span>'
        '<span class="hero-repo">{owner}/{name}</span>'
        '<span class="hero-desc">{desc}</span></a>'.format(
            url=_esc(r["live_url"]), name=_esc(r["name"]), owner=_esc(r["owner"]),
            desc=_esc(r["description"]),
            search=_esc((r["name"] + " " + r["description"] + " " + r["owner"]).lower()),
        ) for r in live
    )
    return '<section class="hero"><h2>Live Sites</h2><div class="hero-grid">{}</div></section>'.format(cards)


def _groups(data, now):
    by_owner = {}
    for r in data["records"]:
        by_owner.setdefault(r["owner"], []).append(r)
    user = data["user"]
    order = ([user] if user in by_owner else []) + sorted(o for o in by_owner if o != user)
    out = []
    for owner in order:
        recs = by_owner[owner]
        title = "You ({})".format(owner) if owner == user else owner
        cards = "".join(_card(r, now) for r in recs)
        out.append(
            '<details class="group" open><summary>{title} <span class="count">{n}</span></summary>'
            '<div class="grid">{cards}</div></details>'.format(
                title=_esc(title), n=len(recs), cards=cards)
        )
    return "".join(out)


def render(data, generated_at, now=None):
    now = now or datetime.now(timezone.utc)
    c = data["counts"]
    p = PALETTE
    hero = _hero(data["records"], now)
    groups = _groups(data, now)
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub Dashboard — {user}</title>
<style>
:root {{ --bg:{bg}; --bg2:{bg2}; --bg3:{bg3}; --border:{border}; --accent:{accent}; --text:{text}; --muted:{muted}; --text3:{text3}; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.6 system-ui,-apple-system,sans-serif; }}
.wrap {{ max-width:1080px; margin:0 auto; padding:48px 24px 80px; }}
h1,h2,summary {{ font-family:Georgia,'Anthropic Serif',serif; font-weight:500; }}
h1 {{ font-size:2rem; margin:0 0 4px; color:var(--text); }}
h2 {{ color:var(--accent); font-size:1.3rem; margin:40px 0 16px; }}
.sub {{ color:var(--muted); margin:0 0 24px; }}
#search {{ width:100%; padding:12px 16px; font-size:15px; border:1px solid var(--border); border-radius:10px; background:var(--bg2); color:var(--text); margin:8px 0 8px; }}
.hero-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:14px; }}
.hero-card {{ display:flex; flex-direction:column; gap:4px; padding:18px; background:var(--bg2); border:1px solid var(--border); border-radius:12px; text-decoration:none; box-shadow:rgba(0,0,0,0.05) 0 4px 24px; transition:box-shadow .15s; }}
.hero-card:hover {{ box-shadow:0 0 0 1px var(--accent); }}
.hero-name {{ font-family:Georgia,serif; font-size:1.15rem; color:var(--accent); }}
.hero-repo {{ font-size:.75rem; color:var(--text3); }}
.hero-desc {{ font-size:.85rem; color:var(--muted); }}
.group {{ margin:14px 0; border-top:1px solid var(--border); padding-top:8px; }}
summary {{ cursor:pointer; font-size:1.1rem; padding:8px 0; }}
.count {{ color:var(--text3); font-size:.8rem; font-family:system-ui; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; margin-top:10px; }}
.card {{ padding:14px; background:var(--bg2); border:1px solid var(--border); border-radius:10px; }}
.card-top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
.repo {{ font-weight:600; color:var(--text); text-decoration:none; }}
.repo:hover {{ color:var(--accent); }}
.badge {{ font-size:.7rem; color:var(--bg2); background:var(--accent); padding:2px 8px; border-radius:20px; text-decoration:none; white-space:nowrap; }}
.desc {{ color:var(--muted); font-size:.85rem; margin:6px 0; }}
.meta {{ display:flex; gap:12px; color:var(--text3); font-size:.75rem; flex-wrap:wrap; }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--accent); margin-right:4px; }}
.hidden {{ display:none !important; }}
footer {{ margin-top:48px; color:var(--text3); font-size:.8rem; }}
a {{ color:var(--accent); }}
</style></head>
<body><div class="wrap">
<h1>GitHub Dashboard</h1>
<p class="sub">{repos} repos · {live} live sites · {orgs} orgs · updated {gen}</p>
<input id="search" type="search" placeholder="Search repos, descriptions, owners…" autocomplete="off">
{hero}
<!-- GROUPS -->
<h2>All Repositories</h2>
{groups}
<footer>Window into <a href="https://github.com/{user}" target="_blank" rel="noopener">@{user}</a>'s GitHub. Auto-generated; no tracking.</footer>
</div>
<script>
const q=document.getElementById('search');
q.addEventListener('input',()=>{{
  const t=q.value.trim().toLowerCase();
  document.querySelectorAll('[data-search]').forEach(el=>{{
    el.classList.toggle('hidden', t && !el.getAttribute('data-search').includes(t));
  }});
  document.querySelectorAll('.group').forEach(g=>{{
    const any=[...g.querySelectorAll('.card')].some(c=>!c.classList.contains('hidden'));
    g.classList.toggle('hidden', t && !any);
  }});
}});
</script>
</body></html>""".format(
        user=_esc(data["user"]), bg=p["bg"], bg2=p["bg2"], bg3=p["bg3"],
        border=p["border"], accent=p["accent"], text=p["text"], muted=p["muted"],
        text3=p["text3"], repos=c["repos"], live=c["live"], orgs=c["orgs"],
        gen=_esc(generated_at), hero=hero, groups=groups,
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /home/sanjayg4/dashboard && python -m unittest tests.test_render -v`
Expected: PASS (all render tests)

- [ ] **Step 5: Commit**

```bash
cd /home/sanjayg4/dashboard
git add render.py tests/test_render.py
git commit -m "feat: parchment HTML renderer with hero + groups + search"
```

---

### Task 4: CLI entry (build.py)

**Files:**
- Create: `build.py`

**Interfaces:**
- Consumes: `fetcher.collect`, `render.render`.
- Produces: CLI — `python build.py` writes `index.html`; `python build.py --dry-run` prints JSON; `--output PATH` overrides target.

- [ ] **Step 1: Write `build.py`**

```python
#!/usr/bin/env python3
"""Build the GitHub dashboard: fetch repos, render index.html."""
import argparse
import json
import sys
from datetime import datetime, timezone

import fetcher
import render


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build GitHub dashboard")
    ap.add_argument("--dry-run", action="store_true", help="print JSON, write nothing")
    ap.add_argument("--output", default="index.html", help="output HTML path")
    args = ap.parse_args(argv)

    try:
        data = fetcher.collect()
    except RuntimeError as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(data, indent=2))
        return 0

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    out = render.render(data, stamp, now=now)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(out)
    print("Wrote {} ({} repos, {} live)".format(
        args.output, data["counts"]["repos"], data["counts"]["live"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run smoke test**

Run: `cd /home/sanjayg4/dashboard && python build.py --dry-run | python -c "import sys,json; d=json.load(sys.stdin); print('repos',d['counts']['repos'],'live',d['counts']['live'])"`
Expected: prints real counts, no error, no file written.

- [ ] **Step 3: Real build**

Run: `cd /home/sanjayg4/dashboard && python build.py && head -c 200 index.html`
Expected: `Wrote index.html (...)` then HTML doctype. Open in browser; verify search filters and group toggles work, hero shows only live-linked repos.

- [ ] **Step 4: Full test suite**

Run: `cd /home/sanjayg4/dashboard && python -m unittest discover -s tests -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/sanjayg4/dashboard
git add build.py index.html
git commit -m "feat: build.py CLI + first generated index.html"
```

---

### Task 5: Refresh workflow + README

**Files:**
- Create: `.github/workflows/build.yml`
- Create: `README.md`
- Create: `.gitignore`

**Interfaces:** none (CI + docs).

- [ ] **Step 1: Write `.github/workflows/build.yml`**

```yaml
name: Build dashboard
on:
  schedule:
    - cron: "17 6 * * *"   # daily 06:17 UTC
  workflow_dispatch: {}
  push:
    branches: [main]
    paths-ignore: ["index.html"]   # avoid self-trigger loop
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run tests
        run: python -m unittest discover -s tests -v
      - name: Build
        env:
          GH_TOKEN: ${{ secrets.GH_DASHBOARD_TOKEN }}
        run: python build.py
      - name: Commit if changed
        run: |
          if ! git diff --quiet index.html; then
            git config user.name "dashboard-bot"
            git config user.email "actions@github.com"
            git add index.html
            git commit -m "chore: refresh dashboard [skip ci]"
            git push
          else
            echo "No changes."
          fi
```

Note: `gh` is preinstalled on `ubuntu-latest`; `GH_TOKEN` env makes `gh api` use the PAT.

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
```

- [ ] **Step 3: Write `README.md`**

```markdown
# GitHub Dashboard

One page indexing every public repo (mine + my orgs) and its live link.
Live: https://sanjaygupta-professional.github.io/dashboard

## How it works
`build.py` calls the GitHub API via `gh`, normalizes repos (`fetcher.py`),
and renders a self-contained `index.html` (`render.py`). The page embeds its
data as JSON and makes no runtime API calls — safe to host publicly. Public
repos only. A GitHub Action rebuilds it daily and on demand.

## Local build
    python build.py            # writes index.html
    python build.py --dry-run  # prints JSON, writes nothing
    python -m unittest discover -s tests

## REQUIRED one-time setup — Personal Access Token
The Action needs to read your *other* repos/orgs, which the default
`GITHUB_TOKEN` cannot. Create a PAT and store it as a secret:

1. https://github.com/settings/tokens → **Generate new token (classic)**.
2. Scopes: check **`repo`** and **`read:org`**. Expiry: your choice.
3. Generate, copy the token.
4. In THIS repo: **Settings → Secrets and variables → Actions → New repository secret**.
5. Name: `GH_DASHBOARD_TOKEN`. Value: the token. Save.
6. Enable Pages: **Settings → Pages → Source: Deploy from a branch → `main` / root**.

Then trigger **Actions → Build dashboard → Run workflow** to verify.
```

- [ ] **Step 4: Commit**

```bash
cd /home/sanjayg4/dashboard
git add .github/workflows/build.yml README.md .gitignore
git commit -m "ci: daily refresh workflow + README with PAT setup"
```

---

### Task 6: Create remote repo, enable Pages, publish

**Files:** none (deployment).

- [ ] **Step 1: Create the public repo + push** (Claude runs)

```bash
cd /home/sanjayg4/dashboard
gh repo create sanjaygupta-professional/dashboard --public --source=. --remote=origin --push
```

Expected: repo created, `main` pushed.

- [ ] **Step 2: Enable GitHub Pages from main/root** (Claude runs)

```bash
gh api -X POST repos/sanjaygupta-professional/dashboard/pages \
  -f "source[branch]=main" -f "source[path]=/" 2>&1 || \
gh api -X PUT repos/sanjaygupta-professional/dashboard/pages \
  -f "source[branch]=main" -f "source[path]=/"
```

Expected: Pages enabled (201/204). Live URL: `https://sanjaygupta-professional.github.io/dashboard`.

- [ ] **Step 3: HUMAN step — add the PAT secret**

Tell the user to follow README steps 1–5 to create `GH_DASHBOARD_TOKEN`. The
scheduled/dispatch Action build will fail to see other repos until this exists,
but the initial `index.html` (built locally in Task 4 and pushed) is already live.

- [ ] **Step 4: Verify live page**

Run: `curl -sSI https://sanjaygupta-professional.github.io/dashboard/ | head -1`
Expected: `HTTP/2 200` (allow a few minutes for first Pages deploy).

- [ ] **Step 5: Final commit/tag (optional)**

```bash
cd /home/sanjayg4/dashboard
git tag v1 && git push --tags
```

---

## Self-Review

**Spec coverage:**
- All public repos owned + org → Task 2 `collect`. ✓
- Live link via Pages/homepage → Task 1 `normalize`. ✓
- Public-only on public page → Task 2 private filter + Task 3 (no private data passed). ✓
- Hero live-sites + grouped + search → Task 3. ✓
- No runtime API calls → Task 3 (embedded JSON) + test. ✓
- Parchment design → Task 3 palette + anti-purple test. ✓
- Auto-refresh Action + PAT → Task 5. ✓
- Host at sanjaygupta-professional/dashboard + Pages → Task 6. ✓
- Tests: dry-run JSON, count assert, render snapshot → Tasks 2–4. ✓

**Placeholders:** none — all code complete.

**Type consistency:** record keys (`name, owner, description, language, stars, pushed_at, repo_url, live_url, is_owner`) identical across normalize → collect → render → tests. `collect()` returns `{user, orgs, records, counts{repos,live,orgs}}` consumed consistently by `render` and `build.py`. ✓
