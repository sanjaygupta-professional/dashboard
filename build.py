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
