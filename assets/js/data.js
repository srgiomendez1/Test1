/*
 * Data loading layer.
 *
 *  - bets.json: generated from the friends' Excel (scripts/convert_bets.py).
 *  - results.json: committed by the GitHub Action (openfootball baseline +
 *    optional live overlay). Refreshed on a schedule.
 *
 * If results.json is missing/unreadable we fall back to fetching the
 * openfootball feed directly in the browser (it sends Access-Control-Allow-
 * Origin: *), so the site keeps working even before the Action runs. We also
 * recompute live/scheduled status client-side from kickoff time so a "finished"
 * flag is never shown for a match that hasn't been scored yet.
 */
(function (global) {
  "use strict";

  const OPENFOOTBALL_URL =
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json";
  // Free, no-key live in-match source. Fetched directly from the browser for
  // ~30s freshness (the server-side Action only refreshes every 5 min — GitHub's
  // cron minimum). Best-effort: if it's unreachable or blocks cross-origin
  // requests (CORS), we silently keep the committed data.
  const LIVE_SOURCE_URL = "https://worldcup26.ir/get/games";

  const TEAM_ALIASES = {
    "cote d ivoire": "ivory coast", "cote divoire": "ivory coast",
    "congo dr": "dr congo", "democratic republic of congo": "dr congo",
    "democratic republic of the congo": "dr congo",
    "korea republic": "south korea", "republic of korea": "south korea",
    "czechia": "czech republic",
    "united states": "usa", "united states of america": "usa",
    "bosnia and herzegovina": "bosnia herzegovina", "turkiye": "turkey",
  };
  function normTeam(name) {
    let s = String(name || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
    s = s.toLowerCase().replace(/&/g, " and ").replace(/[^a-z0-9]+/g, " ").trim();
    return TEAM_ALIASES[s] || s;
  }
  // A match is treated as possibly "live" for this long after kickoff if it
  // still has no final score (covers 90' + stoppage + half-time + buffer).
  const LIVE_WINDOW_MS = 150 * 60 * 1000;

  async function getJSON(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
    return res.json();
  }

  function kickoffUtc(date, timeStr) {
    try {
      const [hm, off] = (timeStr || "").split(" ");
      const [h, m] = hm.split(":").map(Number);
      let offset = 0;
      if (off && off.toUpperCase().startsWith("UTC")) offset = parseInt(off.slice(3) || "0", 10);
      const [y, mo, d] = date.split("-").map(Number);
      return Date.UTC(y, mo - 1, d, h - offset, m);
    } catch (e) {
      return null;
    }
  }

  // Normalize the raw openfootball feed into our results shape (browser fallback).
  function normalizeOpenfootball(feed) {
    const matches = {};
    for (const m of feed.matches || []) {
      const home = m.team1, away = m.team2, date = m.date;
      if (!home || !away || !date) continue;
      const ft = m.score && m.score.ft;
      matches[`${date}|${home}|${away}`] = {
        date, time: m.time, kickoff_utc: kickoffUtc(date, m.time),
        home, away, group: m.group, ground: m.ground,
        score: ft && ft.length === 2 ? [ft[0], ft[1]] : null,
        status: ft && ft.length === 2 ? "finished" : "scheduled",
        source: "openfootball",
      };
    }
    return { generated_at: new Date().toISOString(), matches };
  }

  // Reconcile status with the clock: a no-score match whose kickoff has passed
  // (within the live window) is shown as "live (en vivo)" even without a score.
  function applyClock(results) {
    const now = Date.now();
    for (const m of Object.values(results.matches)) {
      const ko = m.kickoff_utc != null
        ? (typeof m.kickoff_utc === "number" ? m.kickoff_utc : Date.parse(m.kickoff_utc))
        : null;
      if (m.status === "finished") continue;
      if (m.status === "live") continue; // trusted from live source
      if (ko != null && now >= ko && now - ko <= LIVE_WINDOW_MS) {
        m.status = "live";
      } else if (ko != null && now < ko) {
        m.status = "scheduled";
      }
    }
    return results;
  }

  // Best-effort: overlay fresher live scores straight from the live API (mirrors
  // scripts/fetch_results.py). Never throws; on CORS/network failure we keep the
  // committed data. worldcup26.ir schema: home_team_name_en / away_team_name_en,
  // home_score / away_score (strings), finished "TRUE"/"FALSE", time_elapsed.
  async function overlayLiveClient(results) {
    let raw;
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 8000);
      const res = await fetch(LIVE_SOURCE_URL, { cache: "no-store", signal: ctrl.signal });
      clearTimeout(t);
      if (!res.ok) return false;
      raw = await res.json();
    } catch (e) {
      return false; // unreachable, timed out, or blocked by CORS — keep committed results
    }
    const games = Array.isArray(raw) ? raw : (raw.games || raw.matches || raw.data || []);
    const idx = {};
    for (const [key, m] of Object.entries(results.matches)) {
      idx[[normTeam(m.home), normTeam(m.away)].sort().join("|")] = key;
    }
    let n = 0;
    for (const g of games) {
      try {
        const lh = g.home_team_name_en || g.home || g.team1 || "";
        const la = g.away_team_name_en || g.away || g.team2 || "";
        const key = idx[[normTeam(lh), normTeam(la)].sort().join("|")];
        if (!key) continue;
        const m = results.matches[key];
        const finished = String(g.finished || "").toUpperCase() === "TRUE";
        const elapsed = String(g.time_elapsed || "").trim();
        const started = finished || !["", "notstarted", "null", "none"].includes(elapsed.toLowerCase());
        if (!started) continue;
        const hs = parseInt(g.home_score, 10), as = parseInt(g.away_score, 10);
        if (Number.isFinite(hs) && Number.isFinite(as)) {
          m.score = normTeam(lh) === normTeam(m.home) ? [hs, as] : [as, hs];
          m.source = "live";
        }
        if (finished) { m.status = "finished"; }
        else { m.status = "live"; m.minute = elapsed; }
        n++;
      } catch (e) { /* skip a malformed game */ }
    }
    if (n) results.generated_at = new Date().toISOString();
    return n > 0;
  }

  async function load() {
    const bets = await getJSON("data/bets.json");
    let results;
    try {
      results = await getJSON("data/results.json");
      if (!results || !results.matches) throw new Error("empty results.json");
    } catch (e) {
      console.warn("results.json unavailable, falling back to openfootball:", e);
      results = normalizeOpenfootball(await getJSON(OPENFOOTBALL_URL));
    }
    await overlayLiveClient(results); // ~30s live refresh, best-effort
    applyClock(results);

    // Attach team metadata (Spanish name + flag); tolerate a missing file.
    let teams = {};
    try { teams = await getJSON("data/teams-es.json"); } catch (e) { /* ignore */ }

    return { bets, results, teams };
  }

  global.DataLayer = { load };
})(typeof window !== "undefined" ? window : globalThis);
