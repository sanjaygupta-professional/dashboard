"""Render dashboard records into a self-contained parchment-styled HTML page."""
import html
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


def _search_attr(rec):
    return _esc((rec["name"] + " " + rec["description"] + " " + rec["owner"]).lower())


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
        search=_search_attr(rec), repo=_esc(rec["repo_url"]), name=_esc(rec["name"]),
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
            desc=_esc(r["description"]), search=_search_attr(r),
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
#search {{ width:100%; padding:12px 16px; font-size:15px; border:1px solid var(--border); border-radius:10px; background:var(--bg2); color:var(--text); margin:8px 0; }}
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
