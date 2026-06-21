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
    return rec["pushed_at"]


def _run_gh(args):
    proc = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("gh {} failed: {}".format(" ".join(args), proc.stderr.strip()))
    return proc.stdout


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


def collect(run=_run_gh):
    login = json.loads(run(["api", "user"]))["login"]
    orgs = [o["login"] for o in json.loads(run(["api", "user/orgs"]))]

    raw = _api(run, "user/repos?per_page=100&affiliation=owner")
    for org in orgs:
        raw.extend(_api(run, "orgs/{}/repos?per_page=100".format(org)))

    records = [normalize(r, login) for r in raw if not r.get("private")]
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
