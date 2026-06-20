/*
 * Estimated odds engine (free, client-side). NOT bookmaker odds — a Poisson
 * model built from each team's tournament form (goals for/against, shrunk toward
 * the tournament mean) plus, for group matches, the group's own predicted
 * scorelines. Designed so real odds can override later via data/odds-source.json.
 */
(function (global) {
  "use strict";

  const MAXG = 8;        // goals grid per team
  const HOME_ADV = 0.25; // listed-home edge, in goals
  const PRIOR_K = 1.5;   // pseudo-matches of shrinkage toward the mean

  function poisson(k, lambda) {
    let p = Math.exp(-lambda);
    for (let i = 1; i <= k; i++) p *= lambda / i;
    return p;
  }

  // Per-team attack/defense from finished group-stage matches (kept for reference;
  // the live model below uses bundled ratings calibrated to bookmaker odds).
  function teamStrengths(matches) {
    const t = {};
    let goals = 0, teamMatches = 0;
    for (const m of matches) {
      if (!m.group || m.group.indexOf("Group") !== 0) continue;
      if (m.status !== "finished" || !m.score) continue;
      const [h, a] = m.score;
      (t[m.home] = t[m.home] || { gf: 0, ga: 0, pj: 0 });
      (t[m.away] = t[m.away] || { gf: 0, ga: 0, pj: 0 });
      t[m.home].gf += h; t[m.home].ga += a; t[m.home].pj++;
      t[m.away].gf += a; t[m.away].ga += h; t[m.away].pj++;
      goals += h + a; teamMatches += 2;
    }
    const mu = teamMatches ? goals / teamMatches : 1.3;
    const teams = {};
    for (const [name, s] of Object.entries(t)) {
      const af = (s.gf + PRIOR_K * mu) / (s.pj + PRIOR_K);
      const ad = (s.ga + PRIOR_K * mu) / (s.pj + PRIOR_K);
      teams[name] = { atk: af / mu, def: ad / mu, pj: s.pj };
    }
    return { mu, teams };
  }

  // Expected goals (λ) from bundled team ratings (goal-supremacy units, fitted to
  // bookmaker 1X2 odds). `ratings` is name->number; unknown teams default to 0.
  // Optional `form` (from teamStrengths) nudges ratings by recent tournament form.
  function lambdasFor(match, ratings, form) {
    ratings = ratings || {};
    let rh = ratings[match.home] || 0, ra = ratings[match.away] || 0;
    if (form && form.teams) {
      const fh = form.teams[match.home], fa = form.teams[match.away];
      if (fh && fh.pj) rh += 0.15 * Math.log((fh.atk || 1) / (fh.def || 1));
      if (fa && fa.pj) ra += 0.15 * Math.log((fa.atk || 1) / (fa.def || 1));
    }
    const sup = (rh - ra) + HOME_ADV;
    const T = Math.max(2.2, Math.min(3.6, 2.5 + 0.12 * Math.abs(sup)));
    return { lh: Math.max(0.12, (T + sup) / 2), la: Math.max(0.12, (T - sup) / 2) };
  }

  // Markets from λ. For live games pass remFrac (remaining time fraction) and the
  // current score (curH/curA); odds then describe the FINAL outcome.
  function matchOdds(o) {
    const lh = o.lh != null ? o.lh : o.lambdaH;
    const la = o.la != null ? o.la : o.lambdaA;
    const rem = o.remFrac == null ? 1 : Math.max(0, Math.min(1, o.remFrac));
    const curH = o.curH || 0, curA = o.curA || 0;
    const eh = lh * rem, ea = la * rem;
    let p1 = 0, pX = 0, p2 = 0, over = 0, under = 0;
    const scoreMap = {};
    for (let i = 0; i <= MAXG; i++) {
      const pi = poisson(i, eh);
      for (let j = 0; j <= MAXG; j++) {
        const p = pi * poisson(j, ea);
        const fh = curH + i, fa = curA + j;
        if (fh > fa) p1 += p; else if (fh < fa) p2 += p; else pX += p;
        if (fh + fa >= 3) over += p; else under += p;
        const key = fh + "-" + fa;
        scoreMap[key] = (scoreMap[key] || 0) + p;
      }
    }
    const scores = Object.entries(scoreMap)
      .sort((a, b) => b[1] - a[1]).slice(0, 3).map(([s, p]) => ({ s, p }));
    return { p1, pX, p2, over, under, scores };
  }

  // Decimal odds from a probability, with an optional bookmaker margin so the
  // numbers read like a sportsbook (default ~7% overround).
  const dec = (p, margin) => (p > 0 ? Math.max(1.01, (1 / p) / (1 + (margin || 0))) : 99);

  global.Odds = { poisson, teamStrengths, lambdasFor, matchOdds, dec };
})(typeof window !== "undefined" ? window : globalThis);
