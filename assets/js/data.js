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
    applyClock(results);

    // Attach team metadata (Spanish name + flag); tolerate a missing file.
    let teams = {};
    try { teams = await getJSON("data/teams-es.json"); } catch (e) { /* ignore */ }

    return { bets, results, teams };
  }

  global.DataLayer = { load };
})(typeof window !== "undefined" ? window : globalThis);
