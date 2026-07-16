#!/usr/bin/env python3
"""Fetch OddsPapi data from the GitHub Action (server-side; no CORS / no
Cloudflare-to-Cloudflare block) and write data/odds.json.

Phase 2 = TOURNAMENT + FIXTURES DISCOVERY. Phase 1 confirmed the working shape:
  /tournaments?sportId=10          -> list of tournaments (find "World Cup")
  /fixtures?sportId=10&tournamentId=X&from=YYYY-MM-DD&to=YYYY-MM-DD  (<=10 days apart)
  /odds?fixtureId=Y                -> odds for one fixture
This probes those with real values so we can see the World Cup's tournamentId,
its remaining fixtures (only the Final + 3rd place remain as of writing), and a
sample odds payload's market shape. Read the Action logs, then lock this down.

The API key comes from the ODDSPAPI_KEY GitHub *secret* (env var), never the repo.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get("ODDSPAPI_KEY", "").strip()
BASE = "https://api.oddspapi.io/v4"
OUT = "data/odds.json"
# The remaining real matches (as of writing): Final (Spain vs Argentina, Jul 19)
# and 3rd place (France vs England, Jul 18). Used to find fixtures by team name
# since the tournamentId filter came back empty on this provider.
WATCH_TEAMS = ["spain", "argentina", "france", "england"]
# trigger: re-run now that the workflow actually commits data/odds.json


def get(path, **params):
    params = {k: v for k, v in params.items() if v is not None}
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
        print(f"        sample: {body[:1500]}", file=sys.stderr)
        log.append({"path": path, "params": params, "status": st, "sample": body[:4000]})
        time.sleep(2.5)  # this provider rate-limits; stay well under it
        return st, body

    # 1) Full tournaments list for soccer -> find the (men's senior) World Cup
    #    tournamentId. This provider has BOTH 'fifa-world-cup' (id 24660, but it
    #    reports 0 upcoming fixtures right now) and a plain 'world-cup' (id 16)
    #    that reports futureFixtures=2 — exactly our 2 remaining real matches
    #    (Final + 3rd place). Prefer whichever non-excluded candidate actually
    #    HAS fixtures; fall back to the exact 'fifa-world-cup' slug.
    st, body = probe("/tournaments", sportId=10)
    tournament_id = None
    fallback_id = None
    if st == 200:
        try:
            tournaments = json.loads(body)
            EXCLUDE = ("women", "qualif", "virtual", "srl", "u20", "u17", "u23", "novelt", "club")
            for t in tournaments:
                slug = (t.get("tournamentSlug") or "").lower()
                name = (t.get("tournamentName") or "").lower()
                if "world-cup" not in slug and "world cup" not in name:
                    continue
                print(f"[found] {t}", file=sys.stderr)
                log.append({"note": "world-cup-candidate", "tournament": t})
                if any(x in slug or x in name for x in EXCLUDE):
                    continue
                if (t.get("futureFixtures") or 0) > 0:
                    tournament_id = t.get("tournamentId")  # has real upcoming matches -> best signal
                if slug == "fifa-world-cup":
                    fallback_id = t.get("tournamentId")
            if tournament_id is None:
                tournament_id = fallback_id
        except Exception as e:  # noqa: BLE001
            print(f"[error] parsing tournaments: {e}", file=sys.stderr)

    # 2) Fixtures for that tournament in a near-term window (today .. +9 days;
    #    the API caps the range at 10 days). Only the Final + 3rd place remain.
    today = dt.datetime.now(dt.timezone.utc).date()
    frm = today.isoformat()
    to = (today + dt.timedelta(days=9)).isoformat()
    fixture_ids = []
    if tournament_id is not None:
        st, body = probe("/fixtures", sportId=10, tournamentId=tournament_id, **{"from": frm, "to": to})
        if st == 200:
            try:
                fixtures = json.loads(body)
                for fx in fixtures:
                    fid = fx.get("fixtureId") or fx.get("id")
                    if fid is not None:
                        fixture_ids.append(fid)
            except Exception as e:  # noqa: BLE001
                print(f"[error] parsing fixtures: {e}", file=sys.stderr)
    else:
        print("[warn] no World Cup tournamentId found in /tournaments", file=sys.stderr)

    # Fallback: the tournamentId filter came back empty (0 fixtures reported by
    # /tournaments too) — list ALL soccer fixtures in the window and pick out
    # World Cup ones by name OR by the specific teams still alive (Spain/Argentina
    # for the Final, France/England for 3rd place), so we can see the real
    # fixtureId/tournamentId pairing and field shape even if the tournament isn't
    # labeled "World Cup" the way we expect.
    if not fixture_ids:
        st, body = probe("/fixtures", sportId=10, **{"from": frm, "to": to})
        if st == 200:
            try:
                fixtures = json.loads(body)
                print(f"[info] {len(fixtures)} total soccer fixtures in window", file=sys.stderr)
                if fixtures:
                    print(f"[shape] first fixture keys: {list(fixtures[0].keys())}", file=sys.stderr)
                    print(f"[shape] first fixture: {fixtures[0]}", file=sys.stderr)
                for fx in fixtures:
                    blob = json.dumps(fx).lower()
                    hits = "world cup" in blob or "world-cup" in blob or \
                        sum(t in blob for t in WATCH_TEAMS) >= 2
                    if hits:
                        print(f"[wc-fixture] {fx}", file=sys.stderr)
                        log.append({"note": "wc-fixture-from-all", "fixture": fx})
                        fid = fx.get("fixtureId") or fx.get("id")
                        if fid is not None:
                            fixture_ids.append(fid)
            except Exception as e:  # noqa: BLE001
                print(f"[error] parsing all fixtures: {e}", file=sys.stderr)

    # 3) Sample odds for up to 2 fixtures (Final / 3rd place) to see the market shape.
    for fid in fixture_ids[:2]:
        probe("/odds", fixtureId=fid)

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"_discovery": True, "tournament_id": tournament_id,
                    "fixture_ids": fixture_ids, "probes": log}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT} (discovery dump, {len(log)} probes, tournamentId={tournament_id}, "
          f"fixtures={fixture_ids}).", file=sys.stderr)


if __name__ == "__main__":
    main()
