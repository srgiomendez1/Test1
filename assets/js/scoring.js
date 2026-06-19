/*
 * Scoring rules — verified by reproducing the Excel's own per-player totals
 * exactly. The two criteria ADD UP:
 *   - Equipo ganador / empate (correct outcome): +1
 *   - Marcador exacto (exact score):             +2   (also implies the outcome)
 * So:  exact = 3 pts,  correct-outcome-only = 1 pt,  wrong = 0.
 */
(function (global) {
  "use strict";

  function sign(n) {
    return n > 0 ? 1 : n < 0 ? -1 : 0;
  }

  // pred / actual are [home, away]. Returns {points, exact, outcome}.
  function scoreOne(pred, actual) {
    if (!pred || !actual || pred[0] == null || actual[0] == null) {
      return { points: 0, exact: false, outcome: false };
    }
    const [ph, pa] = pred;
    const [ah, aa] = actual;
    if (ph === ah && pa === aa) {
      return { points: 3, exact: true, outcome: true };
    }
    if (sign(ph - pa) === sign(ah - aa)) {
      return { points: 1, exact: false, outcome: true };
    }
    return { points: 0, exact: false, outcome: false };
  }

  // Build leaderboard. `countLive` includes in-progress matches as provisional.
  function computeStandings(bets, results, countLive) {
    const rows = bets.players.map((p) => ({
      player: p, points: 0, exact: 0, outcome: 0,
      played: 0, provisional: 0,
    }));
    const byPlayer = Object.fromEntries(rows.map((r) => [r.player, r]));

    for (const [key, preds] of Object.entries(bets.predictions)) {
      const match = results.matches[key];
      if (!match || !match.score) continue;
      const live = match.status === "live";
      if (live && !countLive) continue;
      const finished = match.status === "finished";
      if (!finished && !live) continue;

      for (const [player, pred] of Object.entries(preds)) {
        const row = byPlayer[player];
        if (!row) continue;
        const s = scoreOne(pred, match.score);
        row.points += s.points;
        if (s.exact) row.exact += 1;
        if (s.outcome && !s.exact) row.outcome += 1;
        row.played += 1;
        if (live) row.provisional += s.points;
      }
    }

    // Display order: by points; exact/outcome only break the visual order, NOT
    // the rank. Ranking is by TOTAL POINTS only — equal points = same place
    // (and they split the prize for those places).
    rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.exact - a.exact ||
        b.outcome - a.outcome ||
        a.player.localeCompare(b.player, "es")
    );
    let rank = 0, prev = null;
    rows.forEach((r, i) => {
      if (r.points !== prev) { rank = i + 1; prev = r.points; } // competition rank: ties share, next skips (1,1,3…)
      r.rank = rank;
    });
    return rows;
  }

  global.Scoring = { scoreOne, computeStandings, sign };
})(typeof window !== "undefined" ? window : globalThis);
