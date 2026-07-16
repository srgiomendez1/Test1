#!/usr/bin/env python3
"""Fetch OddsPapi data from the GitHub Action (server-side; no CORS / no
Cloudflare-to-Cloudflare block) and write data/odds.json.

Phase 6 = FULL SCHEMA DUMP. Confirmed working:
  tournamentId=16 ("World Cup", the real 2026 tournament on this provider)
  fixtures: France vs England (3rd place, id1000001653452539, Jul 18)
            Spain vs Argentina (Final, id1000001653452537, Jul 19)
  /odds?fixtureId=X -> {..., bookmakerOdds: {<bookmaker>: {markets: {<marketId>:
    {outcomes: {<outcomeId>: {players: {"0": {price, ...}}}}}}}}}
This dumps the FULL (untruncated) odds payload for both fixtures plus a compact
summary (bookmakers x markets x outcome prices) so we can pick a normalized
market (1X2 / match-winner) and a bookmaker (or an average) for the real UI.

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
TOURNAMENT_ID = 16  # confirmed: the real (men's senior) 2026 World Cup on this provider


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


def summarize(fixture_odds):
    """bookmaker -> marketId -> [{outcomeId, price}] (first player only)."""
    out = {}
    for bk, bdata in (fixture_odds.get("bookmakerOdds") or {}).items():
        markets = {}
        for mkt_id, mkt in (bdata.get("markets") or {}).items():
            outs = []
            for out_id, out_data in (mkt.get("outcomes") or {}).items():
                players = out_data.get("players") or {}
                p0 = players.get("0") or {}
                outs.append({"outcomeId": out_id, "price": p0.get("price")})
            markets[mkt_id] = outs
        out[bk] = markets
    return out


def main():
    if not KEY:
        print("ERROR: ODDSPAPI_KEY secret not set on the repo.", file=sys.stderr)
        sys.exit(1)

    def call(path, **params):
        st, body = get(path, **params)
        print(f"[call] {path} {params} -> HTTP {st}", file=sys.stderr)
        time.sleep(2.5)
        return st, body

    today = dt.datetime.now(dt.timezone.utc).date()
    frm, to = today.isoformat(), (today + dt.timedelta(days=9)).isoformat()

    st, body = call("/fixtures", sportId=10, tournamentId=TOURNAMENT_ID, **{"from": frm, "to": to})
    fixtures = json.loads(body) if st == 200 else []
    print(f"[info] {len(fixtures)} fixtures for tournamentId={TOURNAMENT_ID}", file=sys.stderr)

    dump = {"_debug": True, "tournament_id": TOURNAMENT_ID, "fixtures": [], "odds_raw": {}, "summary": {}}
    for fx in fixtures:
        fid = fx.get("fixtureId")
        dump["fixtures"].append({
            "fixtureId": fid, "home": fx.get("participant1Name"), "away": fx.get("participant2Name"),
            "startTime": fx.get("startTime"), "round": fx.get("tournamentName"),
        })
        st, body = call("/odds", fixtureId=fid)
        if st != 200:
            continue
        odds = json.loads(body)
        dump["odds_raw"][fid] = odds  # FULL untruncated payload
        summ = summarize(odds)
        dump["summary"][fid] = summ
        print(f"[summary] fixture {fid} bookmakers: {list(summ.keys())}", file=sys.stderr)
        for bk, mkts in summ.items():
            print(f"  [{bk}] markets: {list(mkts.keys())}", file=sys.stderr)

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT} (full schema dump, {len(fixtures)} fixtures).", file=sys.stderr)


if __name__ == "__main__":
    main()
