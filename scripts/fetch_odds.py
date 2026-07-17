#!/usr/bin/env python3
"""Fetch REAL bookmaker odds from OddsPapi and write a compact data/odds.json.

Runs server-side (GitHub Action) — no CORS / no Cloudflare-to-Cloudflare block.
Confirmed via discovery (read the Action logs of earlier runs if you need the
raw exploration):
  - tournamentId=16 is the real 2026 FIFA World Cup on this provider (its
    'fifa-world-cup' slug tournament reports 0 fixtures for some reason; the
    plain 'world-cup' slug is the one with actual fixtures/odds).
  - Market "101" = 1X2 (outcome 101=home, 102=draw, 103=away) — same IDs across
    every bookmaker on this aggregator.
  - Market "1010" = Over/Under 2.5 goals (1010=over, 1011=under) — same deal.
  - Prefer the 'pinnacle' bookmaker (industry-standard low-margin "sharp" book);
    fall back to an average of a few major books, else skip that match (the
    site's model-based estimate is used instead — this is purely additive).

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
MARKET_1X2 = "101"
MARKET_OU25 = "1010"
PREFERRED_BOOKS = ["pinnacle", "bet365", "williamhill", "betmgm", "caesars", "unibet"]


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


def call(path, **params):
    st, body = get(path, **params)
    print(f"[call] {path} {params} -> HTTP {st}", file=sys.stderr)
    time.sleep(2.5)  # this provider rate-limits; stay well under it
    return st, body


def market_prices(bookmaker_data, market_id):
    """{outcomeId: price} for one market, or {} if absent/malformed."""
    mkt = (bookmaker_data.get("markets") or {}).get(market_id) or {}
    out = {}
    for out_id, out_data in (mkt.get("outcomes") or {}).items():
        p0 = (out_data.get("players") or {}).get("0") or {}
        price = p0.get("price")
        if isinstance(price, (int, float)) and price > 1:
            out[out_id] = price
    return out


def pick_book(fixture_odds):
    """Prefer a known low-margin book; else average across whichever of the
    preferred list are present; else None (caller skips this fixture)."""
    books = fixture_odds.get("bookmakerOdds") or {}
    if "pinnacle" in books:
        return "pinnacle", books["pinnacle"]

    present = [b for b in PREFERRED_BOOKS if b in books]
    if not present:
        return None, None

    avg = {"markets": {MARKET_1X2: {"outcomes": {}}, MARKET_OU25: {"outcomes": {}}}}
    for market_id in (MARKET_1X2, MARKET_OU25):
        sums, counts = {}, {}
        for b in present:
            for out_id, price in market_prices(books[b], market_id).items():
                sums[out_id] = sums.get(out_id, 0) + price
                counts[out_id] = counts.get(out_id, 0) + 1
        for out_id, total in sums.items():
            mean_price = total / counts[out_id]
            avg["markets"][market_id]["outcomes"][out_id] = {"players": {"0": {"price": mean_price}}}
    return f"average({len(present)} books)", avg


def implied_pct(price):
    return round(100 / price) if price and price > 1 else None


def extract_match_odds(fixture_odds):
    book_label, book_data = pick_book(fixture_odds)
    if not book_data:
        return None, None

    m1x2 = market_prices(book_data, MARKET_1X2)
    mou = market_prices(book_data, MARKET_OU25)
    if not (m1x2.get("101") and m1x2.get("102") and m1x2.get("103")):
        return None, None  # need a complete 1X2 to be useful

    result = {
        "dec1": m1x2["101"], "decX": m1x2["102"], "dec2": m1x2["103"],
        "pct1": implied_pct(m1x2["101"]), "pctX": implied_pct(m1x2["102"]), "pct2": implied_pct(m1x2["103"]),
    }
    if mou.get("1010") and mou.get("1011"):
        result.update({
            "decOver": mou["1010"], "decUnder": mou["1011"],
            "pctOver": implied_pct(mou["1010"]), "pctUnder": implied_pct(mou["1011"]),
        })
    return book_label, result


def main():
    if not KEY:
        print("ERROR: ODDSPAPI_KEY secret not set on the repo.", file=sys.stderr)
        sys.exit(1)

    today = dt.datetime.now(dt.timezone.utc).date()
    frm, to = today.isoformat(), (today + dt.timedelta(days=9)).isoformat()

    st, body = call("/fixtures", sportId=10, tournamentId=TOURNAMENT_ID, **{"from": frm, "to": to})
    fixtures = json.loads(body) if st == 200 else []
    print(f"[info] {len(fixtures)} fixtures for tournamentId={TOURNAMENT_ID}", file=sys.stderr)

    matches = {}
    for fx in fixtures:
        fid = fx.get("fixtureId")
        home, away = fx.get("participant1Name"), fx.get("participant2Name")
        if not (fid and home and away):
            continue
        st, body = call("/odds", fixtureId=fid)
        if st != 200:
            continue
        try:
            fixture_odds = json.loads(body)
        except Exception as e:  # noqa: BLE001
            print(f"[error] parsing odds for {fid}: {e}", file=sys.stderr)
            continue

        book_label, odds = extract_match_odds(fixture_odds)
        if not odds:
            print(f"[skip] no usable 1X2 for {home} vs {away}", file=sys.stderr)
            continue

        key = f"{home.strip().lower()}|{away.strip().lower()}"
        matches[key] = {
            "home": home, "away": away, "bookmaker": book_label,
            "kickoff_utc": fx.get("startTime"), **odds,
        }
        print(f"[ok] {home} vs {away} <- {book_label}: 1={odds['dec1']} X={odds['decX']} 2={odds['dec2']}",
              file=sys.stderr)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": "oddspapi",
        "matches": matches,
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT}: {len(matches)} matches with real odds.", file=sys.stderr)


if __name__ == "__main__":
    main()
