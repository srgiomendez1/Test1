#!/usr/bin/env python3
"""Fetch OddsPapi data from the GitHub Action (server-side; no CORS / no
Cloudflare-to-Cloudflare block) and write data/odds.json.

Phase 1 = DISCOVERY: OddsPapi's exact endpoints for the World Cup aren't known
yet, so this probes a handful of likely paths and logs their status + a sample.
Read the Action logs to find the right endpoint, then we lock this down to a
single call that writes the real odds.

The API key comes from the ODDSPAPI_KEY GitHub *secret* (env var), never the repo.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get("ODDSPAPI_KEY", "").strip()
BASE = "https://api.oddspapi.io/v4"
OUT = "data/odds.json"


def get(path, **params):
    params["apiKey"] = KEY
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; LosReyesQuiniela/1.0)",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def main():
    if not KEY:
        print("ERROR: ODDSPAPI_KEY secret not set on the repo.", file=sys.stderr)
        sys.exit(1)

    log = []

    def probe(path, **params):
        st, body = get(path, **params)
        print(f"[probe] {path} {params} -> HTTP {st}", file=sys.stderr)
        print(f"        sample: {body[:500]}", file=sys.stderr)
        log.append({"path": path, "params": params, "status": st, "sample": body[:2000]})
        return st, body

    # Known to work:
    probe("/sports")
    # Discover soccer (sportId 10) structure — competitions/leagues/events/odds:
    for p in ["/competitions", "/leagues", "/tournaments", "/categories",
              "/events", "/fixtures", "/odds", "/matches"]:
        probe(p, sportId=10)
    # Outrights / "World Cup winner" likely under soccer-specials (sportId 44):
    probe("/competitions", sportId=44)
    probe("/events", sportId=44)

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"_discovery": True, "probes": log}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT} (discovery dump, {len(log)} probes).", file=sys.stderr)


if __name__ == "__main__":
    main()
