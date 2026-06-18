#!/usr/bin/env python3
"""Fetch World Cup 2026 results into data/results.json.

Run server-side by the GitHub Action (open internet, so no CORS limits) on a
schedule. Strategy:

  1. Always build a reliable baseline from the openfootball public-domain feed
     (no key, CORS-enabled, updated through the tournament).
  2. If LIVE_SOURCE_URL is set and reachable, overlay in-progress / fresher
     scores on top of the baseline (best-effort; any failure is logged and the
     baseline is kept). This is how we get "as live as possible" without
     coupling the site to one specific free service.

Output is normalized and keyed exactly like data/bets.json
("YYYY-MM-DD|HomeEN|AwayEN") so the browser can join the two directly.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json"
    "/master/2026/worldcup.json"
)
LIVE_SOURCE_URL = os.environ.get("LIVE_SOURCE_URL", "").strip()
OUT = os.environ.get("RESULTS_OUT", "data/results.json")


def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "wc-bet-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def kickoff_utc(date, time_str):
    """'2026-06-11', '13:00 UTC-6' -> ISO 8601 UTC string, or None."""
    try:
        hm, _, off = (time_str or "").partition(" ")
        h, m = (int(x) for x in hm.split(":"))
        offset = 0
        if off.upper().startswith("UTC"):
            offset = int(off[3:] or 0)
        local = dt.datetime.strptime(date, "%Y-%m-%d").replace(hour=h, minute=m)
        utc = local - dt.timedelta(hours=offset)
        return utc.replace(tzinfo=dt.timezone.utc).isoformat()
    except Exception:
        return None


def normalize_openfootball(data):
    """openfootball feed -> {match_key: normalized match}."""
    out = {}
    for m in data.get("matches", []):
        home, away = m.get("team1"), m.get("team2")
        date = m.get("date")
        if not (home and away and date):
            continue
        score = m.get("score") or {}
        ft = score.get("ft")
        key = f"{date}|{home}|{away}"
        out[key] = {
            "date": date,
            "time": m.get("time"),
            "kickoff_utc": kickoff_utc(date, m.get("time")),
            "home": home,
            "away": away,
            "group": m.get("group"),
            "ground": m.get("ground"),
            "score": [ft[0], ft[1]] if ft and len(ft) == 2 else None,
            "status": "finished" if ft and len(ft) == 2 else "scheduled",
            "source": "openfootball",
        }
    return out


def overlay_live(baseline, live_url):
    """Best-effort overlay of a live source. Defensive: never raises.

    Expects a list of games with team names + scores + a status field. The
    exact shape of free live APIs varies; we try common field names and skip
    anything we can't confidently map. Tweak the field guesses here once the
    chosen live source's schema is confirmed.
    """
    try:
        raw = fetch_json(live_url)
    except Exception as e:  # noqa: BLE001
        print(f"[live] source unavailable, keeping baseline: {e}", file=sys.stderr)
        return 0

    games = raw if isinstance(raw, list) else (
        raw.get("games") or raw.get("matches") or raw.get("data") or []
    )
    updated = 0
    # Build a lookup from English home/away -> baseline key (date-agnostic match
    # on team pair, since live feeds may format dates differently).
    pair_index = {}
    for key, m in baseline.items():
        pair_index.setdefault((m["home"], m["away"]), key)

    for g in games:
        try:
            home = (g.get("home") or g.get("team1") or g.get("homeTeam") or "").strip()
            away = (g.get("away") or g.get("team2") or g.get("awayTeam") or "").strip()
            key = pair_index.get((home, away))
            if not key:
                continue
            hs = g.get("home_score", g.get("score_home", g.get("homeScore")))
            as_ = g.get("away_score", g.get("score_away", g.get("awayScore")))
            status = str(g.get("status", "")).lower()
            entry = baseline[key]
            if hs is not None and as_ is not None:
                entry["score"] = [int(hs), int(as_)]
                entry["source"] = "live"
            if any(s in status for s in ("live", "playing", "in_play", "1h", "2h", "ht")):
                entry["status"] = "live"
                entry["minute"] = g.get("minute") or g.get("time")
            elif any(s in status for s in ("finish", "ft", "ended", "full")):
                entry["status"] = "finished"
            updated += 1
        except Exception as e:  # noqa: BLE001
            print(f"[live] skipped a game: {e}", file=sys.stderr)
    print(f"[live] overlaid {updated} games from live source", file=sys.stderr)
    return updated


def main():
    base = fetch_json(OPENFOOTBALL_URL)
    results = normalize_openfootball(base)
    if LIVE_SOURCE_URL:
        overlay_live(results, LIVE_SOURCE_URL)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "matches": results,
    }
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    finished = sum(1 for m in results.values() if m["status"] == "finished")
    print(f"Wrote {OUT}: {len(results)} matches, {finished} finished.")


if __name__ == "__main__":
    main()
