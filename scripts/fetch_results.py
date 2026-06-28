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
import re
import sys
import unicodedata
import urllib.request

OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json"
    "/master/2026/worldcup.json"
)
# Free, no-key live in-match source (worldcup26.ir). Overridable via the
# LIVE_SOURCE_URL repository variable; set it to "none"/empty to disable.
DEFAULT_LIVE_URL = "https://worldcup26.ir/get/games"


def normalize_url(u):
    u = (u or "").strip()
    if u.lower() in ("", "none", "off", "false", "disable", "disabled"):
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u  # the repo variable is set without a scheme
    return u


LIVE_SOURCE_URL = normalize_url(os.environ.get("LIVE_SOURCE_URL", DEFAULT_LIVE_URL))
OUT = os.environ.get("RESULTS_OUT", "data/results.json")


# Canonicalize a country name so the openfootball and live feeds line up despite
# spelling/diacritic/word-order differences.
_TEAM_ALIASES = {
    "cote d ivoire": "ivory coast", "cote divoire": "ivory coast",
    "congo dr": "dr congo", "democratic republic of congo": "dr congo",
    "democratic republic of the congo": "dr congo", "dr congo": "dr congo",
    "korea republic": "south korea", "republic of korea": "south korea",
    "czechia": "czech republic",
    "united states": "usa", "united states of america": "usa",
    "bosnia and herzegovina": "bosnia herzegovina",
    "turkiye": "turkey",
}


def norm_team(name):
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return _TEAM_ALIASES.get(s, s)


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
            "num": m.get("num"),  # FIFA match number (drives the knockout bracket tree)
            "date": date,
            "time": m.get("time"),
            "kickoff_utc": kickoff_utc(date, m.get("time")),
            "home": home,
            "away": away,
            "group": m.get("group"),
            "round": m.get("round"),
            "ground": m.get("ground"),
            "score": [ft[0], ft[1]] if ft and len(ft) == 2 else None,
            "status": "finished" if ft and len(ft) == 2 else "scheduled",
            "source": "openfootball",
        }
    return out


def _to_int(v):
    try:
        s = str(v).strip()
        return int(s) if s not in ("", "null", "none", "None") else None
    except (TypeError, ValueError):
        return None


def overlay_live(baseline, live_url):
    """Overlay the worldcup26.ir live feed onto the openfootball baseline.

    Schema (GET /get/games): games[] with home_team_name_en / away_team_name_en,
    home_score / away_score (strings), finished ("TRUE"/"FALSE"), time_elapsed
    ("notstarted" -> minute when live), group, matchday. Defensive: never raises;
    on any failure the openfootball baseline is kept untouched.
    """
    try:
        raw = fetch_json(live_url)
    except Exception as e:  # noqa: BLE001
        print(f"[live] source unavailable, keeping baseline: {e}", file=sys.stderr)
        return 0

    games = raw if isinstance(raw, list) else (
        raw.get("games") or raw.get("matches") or raw.get("data") or []
    )

    # Index baseline matches by the unordered, normalized team pair (also tolerates
    # home/away orientation differences between feeds).
    pair_index = {}
    for key, m in baseline.items():
        pair_index[frozenset((norm_team(m["home"]), norm_team(m["away"])))] = key

    updated, unmatched = 0, []
    for g in games:
        try:
            lh = g.get("home_team_name_en") or g.get("home") or g.get("team1") or ""
            la = g.get("away_team_name_en") or g.get("away") or g.get("team2") or ""
            nlh, nla = norm_team(lh), norm_team(la)
            key = pair_index.get(frozenset((nlh, nla)))
            if not key:
                if lh and la:
                    unmatched.append(f"{lh} vs {la}")
                continue

            entry = baseline[key]
            finished = str(g.get("finished", "")).strip().upper() == "TRUE"
            elapsed = str(g.get("time_elapsed", "")).strip()
            started = finished or (elapsed.lower() not in ("", "notstarted", "null", "none"))
            if not started:
                continue  # don't clobber a scheduled match with a 0-0 placeholder

            hs = _to_int(g.get("home_score", g.get("homeScore")))
            as_ = _to_int(g.get("away_score", g.get("awayScore")))
            if hs is not None and as_ is not None:
                # Match baseline orientation; flip if the live feed lists teams reversed.
                entry["score"] = [hs, as_] if nlh == norm_team(entry["home"]) else [as_, hs]
                entry["source"] = "live"

            if finished:
                entry["status"] = "finished"
            else:
                entry["status"] = "live"
                entry["minute"] = elapsed
            updated += 1
        except Exception as e:  # noqa: BLE001
            print(f"[live] skipped a game: {e}", file=sys.stderr)

    print(f"[live] overlaid {updated} games from live source", file=sys.stderr)
    if unmatched:
        print(f"[live] {len(unmatched)} unmatched (add to _TEAM_ALIASES): "
              + "; ".join(unmatched[:12]), file=sys.stderr)
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
