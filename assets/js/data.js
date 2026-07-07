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
  // Free, no-key live in-match source. worldcup26.ir does NOT send CORS headers
  // (and refuses direct cross-origin connections), so the browser never hits it
  // directly — that only spams the console with ERR_CONNECTION_RESET. The reliable
  // path is a tiny Cloudflare Worker (worker/worldcup-proxy.js) whose URL is in
  // data/live-source.json (loaded at runtime into LIVE_PROXY). Public CORS proxies
  // are kept only as a flaky last resort. Best-effort: if all fail we keep the
  // committed data. (The server-side scripts/fetch_results.py DOES use the direct
  // URL, where it works fine.)
  const LIVE_TARGET = "https://worldcup26.ir/get/games";
  let LIVE_PROXY = ""; // set from data/live-source.json during load()

  function liveEndpoints() {
    const enc = encodeURIComponent(LIVE_TARGET);
    const list = [];
    if (LIVE_PROXY) list.push(LIVE_PROXY);             // reliable Cloudflare Worker (primary)
    list.push("https://corsproxy.io/?url=" + enc);     // public fallbacks (flaky, last resort)
    list.push("https://api.allorigins.win/raw?url=" + enc);
    return list;
  }

  const TEAM_ALIASES = {
    "cote d ivoire": "ivory coast", "cote divoire": "ivory coast",
    "congo dr": "dr congo", "democratic republic of congo": "dr congo",
    "democratic republic of the congo": "dr congo",
    "korea republic": "south korea", "republic of korea": "south korea",
    "czechia": "czech republic",
    "united states": "usa", "united states of america": "usa",
    "ir iran": "iran", "cabo verde": "cape verde",
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
      const sc = m.score || {};
      const final = sc.et && sc.et.length === 2 ? sc.et : sc.ft; // ET result if it went to extra time
      const pen = sc.p; // penalty shootout result
      matches[`${date}|${home}|${away}`] = {
        num: m.num, // FIFA match number (knockout bracket tree)
        date, time: m.time, kickoff_utc: kickoffUtc(date, m.time),
        home, away, group: m.group, round: m.round, ground: m.ground,
        score: final && final.length === 2 ? [final[0], final[1]] : null,
        pens: pen && pen.length === 2 ? [pen[0], pen[1]] : null,
        status: final && final.length === 2 ? "finished" : "scheduled",
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

  // ESPN's free, no-key scoreboard — reliable live scores (usually CORS-enabled).
  const ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719&limit=300";

  async function fetchJSONTimed(url, ms) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), ms || 8000);
    try {
      const res = await fetch(url, { cache: "no-store", signal: ctrl.signal });
      clearTimeout(t);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { clearTimeout(t); return null; }
  }

  // Normalize ESPN scoreboard -> [{home,away,hs,as,finished,started,minute}].
  function gamesFromEspn(raw) {
    if (!raw || !raw.events) return null;
    const out = [];
    for (const e of raw.events) {
      const comp = e.competitions && e.competitions[0];
      if (!comp) continue;
      const cs = comp.competitors || [];
      const H = cs.find((c) => c.homeAway === "home"), A = cs.find((c) => c.homeAway === "away");
      if (!H || !A) continue;
      const st = (e.status && e.status.type) || {};
      const state = st.state; // pre | in | post
      const finished = state === "post" || st.completed === true;
      const started = finished || state === "in";
      const hs = parseInt(H.score, 10), as = parseInt(A.score, 10);
      out.push({
        home: (H.team && (H.team.displayName || H.team.name)) || "",
        away: (A.team && (A.team.displayName || A.team.name)) || "",
        hs: Number.isFinite(hs) ? hs : null, as: Number.isFinite(as) ? as : null,
        finished, started,
        minute: st.shortDetail || st.detail || "",
      });
    }
    return out;
  }

  // Normalize worldcup26.ir -> same shape.
  function gamesFromWorldcup26(raw) {
    const arr = Array.isArray(raw) ? raw : (raw && (raw.games || raw.matches || raw.data));
    if (!arr) return null;
    return arr.map((g) => {
      const finished = String(g.finished || "").toUpperCase() === "TRUE";
      const elapsed = String(g.time_elapsed || "").trim();
      const hs = parseInt(g.home_score, 10), as = parseInt(g.away_score, 10);
      return {
        home: g.home_team_name_en || g.home || g.team1 || "",
        away: g.away_team_name_en || g.away || g.team2 || "",
        hs: Number.isFinite(hs) ? hs : null, as: Number.isFinite(as) ? as : null,
        finished,
        started: finished || !["", "notstarted", "null", "none"].includes(elapsed.toLowerCase()),
        minute: elapsed,
      };
    });
  }

  function applyGames(results, games) {
    const idx = {};
    for (const [key, m] of Object.entries(results.matches)) {
      idx[[normTeam(m.home), normTeam(m.away)].sort().join("|")] = key;
    }
    let n = 0;
    for (const g of games) {
      try {
        if (!g.started) continue;
        const nlh = normTeam(g.home), nla = normTeam(g.away);
        const key = idx[[nlh, nla].sort().join("|")];
        if (!key) continue;
        const m = results.matches[key];
        if (g.hs != null && g.as != null) {
          m.score = nlh === normTeam(m.home) ? [g.hs, g.as] : [g.as, g.hs];
          m.source = "live";
        }
        if (g.finished) m.status = "finished";
        else { m.status = "live"; if (g.minute) m.minute = g.minute; }
        n++;
      } catch (e) { /* skip a malformed game */ }
    }
    return n;
  }

  // Overlay the openfootball feed (CORS-enabled, authoritative for FINISHED
  // matches incl. penalties, and it resolves knockout slots to real teams) onto
  // whatever we loaded, joining by FIFA match number so it works even when a
  // committed KO match still shows a "W83" code. This keeps the site current even
  // if the scheduled Action that commits results.json is late. Best-effort.
  async function overlayOpenfootball(results) {
    const feed = await fetchJSONTimed(OPENFOOTBALL_URL, 8000);
    if (!feed || !feed.matches) return false;
    const byNum = {};
    for (const m of Object.values(results.matches)) if (m.num != null) byNum[m.num] = m;
    let changed = 0;
    for (const fm of feed.matches) {
      const t = fm.num != null ? byNum[fm.num] : null;
      if (!t) continue;
      // Fill in knockout teams once openfootball has resolved the slot codes.
      if (fm.team1 && fm.team2) {
        if (t.home !== fm.team1) { t.home = fm.team1; changed++; }
        if (t.away !== fm.team2) { t.away = fm.team2; changed++; }
      }
      const sc = fm.score || {};
      const ft = sc.et && sc.et.length === 2 ? sc.et : sc.ft; // ET result if it went to extra time
      const pen = sc.p;
      if (ft && ft.length === 2) {
        if (!t.score || t.score[0] !== ft[0] || t.score[1] !== ft[1]) { t.score = [ft[0], ft[1]]; changed++; }
        if (pen && pen.length === 2 && (!t.pens || t.pens[0] !== pen[0] || t.pens[1] !== pen[1])) { t.pens = [pen[0], pen[1]]; changed++; }
        if (t.status !== "finished") { t.status = "finished"; changed++; }
        t.source = t.source === "live" ? t.source : "openfootball";
      }
    }
    if (changed) results.generated_at = new Date().toISOString();
    return changed > 0;
  }

  // Best-effort live overlay. Tries ESPN first (reliable), then worldcup26 via the
  // configured Worker / public proxies. Never throws; on failure keeps committed data.
  async function overlayLiveClient(results) {
    let games = gamesFromEspn(await fetchJSONTimed(ESPN_URL, 8000));
    if (!games || !games.length) {
      for (const url of liveEndpoints()) {
        let raw = await fetchJSONTimed(url, 8000);
        if (raw && typeof raw.contents === "string") {        // allorigins wrapper
          try { raw = JSON.parse(raw.contents); } catch (e) { raw = null; }
        }
        games = gamesFromWorldcup26(raw);
        if (games && games.length) break;
      }
    }
    if (!games || !games.length) return false;
    const n = applyGames(results, games);
    if (n) results.generated_at = new Date().toISOString();
    return n > 0;
  }

  async function load() {
    const bets = await getJSON("data/bets.json");
    // Pick up the configured live proxy (Cloudflare Worker) if present.
    try {
      const cfg = await getJSON("data/live-source.json");
      LIVE_PROXY = (cfg && cfg.proxy ? String(cfg.proxy) : "").trim();
    } catch (e) { LIVE_PROXY = ""; }
    let results;
    try {
      results = await getJSON("data/results.json");
      if (!results || !results.matches) throw new Error("empty results.json");
    } catch (e) {
      console.warn("results.json unavailable, falling back to openfootball:", e);
      results = normalizeOpenfootball(await getJSON(OPENFOOTBALL_URL));
    }
    applyClock(results);
    // NOTE: the live overlay is intentionally NOT awaited here — it's an
    // external network call and would block first paint on slow phones. The app
    // renders committed data immediately, then calls applyLive() to fill in live
    // scores and re-renders.

    // Attach team metadata (Spanish name + flag); tolerate a missing file.
    let teams = {};
    try { teams = await getJSON("data/teams-es.json"); } catch (e) { /* ignore */ }

    // Bundled team ratings for the odds model (calibrated to bookmaker odds).
    let ratings = {};
    try { ratings = await getJSON("data/team-ratings.json"); } catch (e) { /* ignore */ }
    // Elo power ranking (drives the Title Pie / tournament sim).
    let elo = {};
    try { elo = await getJSON("data/team-elo.json"); } catch (e) { /* ignore */ }

    return { bets, results, teams, ratings, elo };
  }

  // Overlay live scores onto already-loaded results, then re-apply the clock.
  // Returns true if anything changed (so the caller can re-render). Best-effort.
  async function applyLive(results) {
    // openfootball first (finished results + resolved KO teams), then the live
    // in-play sources (ESPN / worldcup26) on top for minute-by-minute scores.
    const off = await overlayOpenfootball(results);
    const live = await overlayLiveClient(results);
    applyClock(results);
    return off || live;
  }

  global.DataLayer = { load, applyLive };
})(typeof window !== "undefined" ? window : globalThis);
