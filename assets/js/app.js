/* UI rendering for the World Cup 2026 quiniela tracker (Spanish). */
(function () {
  "use strict";

  const REFRESH_MS = 30 * 1000;
  const DAYS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  // Prize pot (MXN). Common practice: ties split, in equal parts, the COMBINED
  // prize of the places they occupy (places beyond 3rd pay 0). E.g. 3 tied for
  // 3rd → each gets POT*0.15/3 = $300; 2 tied for 1st → each (60%+25%)/2 = $2,550.
  const POT = 6000;
  const PLACE_PCT = { 1: 0.60, 2: 0.25, 3: 0.15 };
  const mxn = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
  const fmtMXN = (n) => mxn.format(Math.round(n));

  // Set r.prize: tied players (same competition rank) occupy places rank..rank+k-1
  // and split the combined prize of those places equally.
  function assignPrizes(rows) {
    let i = 0;
    while (i < rows.length) {
      const rank = rows[i].rank;
      let j = i;
      while (j < rows.length && rows[j].rank === rank) j++;
      const k = j - i; // players tied at this rank
      let sumPct = 0;
      for (let p = rank; p < rank + k; p++) sumPct += PLACE_PCT[p] || 0;
      const each = (POT * sumPct) / k;
      for (let t = i; t < j; t++) rows[t].prize = each;
      i = j;
    }
    return rows;
  }

  // Monte Carlo: P(win) per player + each player's expected cumulative-points
  // trajectory across the remaining matches. Σ probs = 100%.
  let _winCache = { sig: null, val: null };
  function poissonSample(l) {           // Knuth
    if (l <= 0) return 0;
    const L = Math.exp(-l); let k = 0, p = 1;
    do { k++; p *= Math.random(); } while (p > L);
    return k - 1;
  }
  function computeWinProbs() {
    const players = state.bets.players;
    const base = {}; players.forEach((p) => (base[p] = 0));
    const remaining = [];
    let liveGoals = 0;
    for (const [k, preds] of Object.entries(state.bets.predictions)) {
      const m = state.results.matches[k];
      if (!m) continue;
      if (m.status === "finished" && m.score) {
        for (const pl in preds) base[pl] += Scoring.scoreOne(preds[pl], m.score).points;
      } else {
        const { lh, la } = Odds.lambdasFor(m, state.ratings, null);
        let rem = 1, cH = 0, cA = 0;
        if (m.status === "live") {
          const n = parseInt(m.minute, 10);
          const mm = Number.isFinite(n) ? n : (String(m.minute).toUpperCase() === "HT" ? 45 : 0);
          rem = Math.max(0.02, (90 - Math.min(mm, 90)) / 90);
          if (m.score) { cH = m.score[0]; cA = m.score[1]; liveGoals += cH + cA; }
        }
        remaining.push({ ko: m.kickoff_utc ? Date.parse(m.kickoff_utc) : 0, lh: lh * rem, la: la * rem, cH, cA, preds });
      }
    }
    remaining.sort((a, b) => a.ko - b.ko);
    const R = remaining.length;
    const baseSum = Object.values(base).reduce((a, b) => a + b, 0);
    const sig = `${players.length}|${baseSum}|${R}|${liveGoals}`;
    if (_winCache.sig === sig) return _winCache.val;

    const N = 5000, wins = {}, tmp = {};
    const sum = Array.from({ length: R + 1 }, () => ({})); // sum[step][player]
    players.forEach((p) => { wins[p] = 0; for (let s = 0; s <= R; s++) sum[s][p] = 0; });
    for (let n = 0; n < N; n++) {
      for (const p of players) { tmp[p] = base[p]; sum[0][p] += tmp[p]; }
      for (let s = 0; s < R; s++) {
        const rm = remaining[s];
        const sc = [rm.cH + poissonSample(rm.lh), rm.cA + poissonSample(rm.la)];
        for (const pl in rm.preds) tmp[pl] += Scoring.scoreOne(rm.preds[pl], sc).points;
        const st = s + 1;
        for (const p of players) sum[st][p] += tmp[p];
      }
      let mx = -Infinity;
      for (const p of players) if (tmp[p] > mx) mx = tmp[p];
      const w = players.filter((p) => tmp[p] === mx);
      const credit = 1 / w.length;
      for (const p of w) wins[p] += credit;
    }
    const probs = {}, mean = {};
    players.forEach((p) => {
      probs[p] = wins[p] / N;
      mean[p] = []; for (let s = 0; s <= R; s++) mean[p].push(sum[s][p] / N);
    });
    const val = { probs, mean, R };
    _winCache = { sig, val };
    return val;
  }

  // Stable per-player color (alphabetical order → palette).
  const PLAYER_COLORS = ["#e8c66a", "#ff6b6b", "#4dd2ff", "#69db7c", "#ffa94d", "#b197fc",
    "#ff8cc3", "#ffe066", "#74c0fc", "#63e6be", "#f06595", "#adb5bd"];
  function playerColor(name) {
    const ps = state.bets.players.slice().sort((a, b) => a.localeCompare(b, "es"));
    const i = ps.indexOf(name);
    return PLAYER_COLORS[(i < 0 ? 0 : i) % PLAYER_COLORS.length];
  }

  function buildMonteCarloChart(W) {
    const players = state.bets.players, R = W.R;
    const box = el("div", "mcchart");
    let yMin = Infinity, yMax = -Infinity;
    players.forEach((p) => W.mean[p].forEach((v) => { if (v < yMin) yMin = v; if (v > yMax) yMax = v; }));
    yMin = Math.floor(yMin - 1); yMax = Math.ceil(yMax + 1);
    const Wd = 720, H = 360, pad = 36;
    const X = (i) => pad + i * (Wd - 2 * pad) / Math.max(1, R);
    const Y = (v) => H - pad - (v - yMin) / Math.max(1, yMax - yMin) * (H - 2 * pad);
    let svg = `<svg viewBox="0 0 ${Wd} ${H}" class="mcsvg" preserveAspectRatio="xMidYMid meet">`;
    svg += `<line x1="${pad}" y1="${H - pad}" x2="${Wd - pad}" y2="${H - pad}" class="ax"/>`;
    svg += `<line x1="${pad}" y1="${pad}" x2="${pad}" y2="${H - pad}" class="ax"/>`;
    [yMin, Math.round((yMin + yMax) / 2), yMax].forEach((v) =>
      (svg += `<text x="${pad - 6}" y="${Y(v) + 4}" class="axt" text-anchor="end">${v}</text>`));
    svg += `<text x="${pad}" y="${H - 10}" class="axt">Hoy</text>`;
    svg += `<text x="${Wd - pad}" y="${H - 10}" class="axt" text-anchor="end">Fin de grupos</text>`;
    // draw lowest-prob first so leaders are on top
    players.slice().sort((a, b) => W.probs[a] - W.probs[b]).forEach((p) => {
      const pts = W.mean[p].map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
      svg += `<polyline points="${pts}" fill="none" stroke="${playerColor(p)}" stroke-width="2.2" opacity="0.92"/>`;
    });
    svg += `</svg>`;
    box.innerHTML = svg;
    const leg = el("div", "mcleg");
    players.slice().sort((a, b) => W.probs[b] - W.probs[a]).forEach((p) =>
      leg.insertAdjacentHTML("beforeend",
        `<span class="mcli"><span class="mcsw" style="background:${playerColor(p)}"></span>${p} <i>${Math.round(W.probs[p] * 100)}%</i></span>`));
    box.appendChild(leg);
    return box;
  }

  let state = { bets: null, results: null, teams: {}, ratings: {}, view: "eliminatorias", player: null, countLive: true, elo: {} };

  const $ = (sel, root = document) => root.querySelector(sel);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };

  function teamHTML(en) {
    const t = state.teams[en] || { es: en, flag: "🏳️" };
    return `<span class="team"><span class="flag">${t.flag}</span><span class="tname">${t.es}</span></span>`;
  }
  const teamES = (en) => (state.teams[en] || {}).es || en;

  function fmtDay(iso) {
    const d = new Date(iso + "T12:00:00");
    return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
  }
  function fmtKickoffTime(m) {
    const ko = typeof m.kickoff_utc === "number" ? m.kickoff_utc : Date.parse(m.kickoff_utc);
    if (!ko) return m.time || "";
    return new Date(ko).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
  }

  // Compact "Jul01" / "8PM" (MonthDay + 12h, Eastern time) for bracket nodes.
  const ET = "America/New_York";
  function etDateLabel(d) {
    const mon = d.toLocaleDateString("en-US", { timeZone: ET, month: "short" }); // "Jul"
    const day = d.toLocaleDateString("en-US", { timeZone: ET, day: "2-digit" });  // "01"
    return mon + day;
  }
  function etTimeLabel(d) {
    const parts = new Intl.DateTimeFormat("en-US", { timeZone: ET, hour: "numeric", minute: "2-digit", hour12: true }).formatToParts(d);
    let hour = "", minute = "", ap = "";
    parts.forEach((p) => { if (p.type === "hour") hour = p.value; else if (p.type === "minute") minute = p.value; else if (p.type === "dayPeriod") ap = p.value; });
    ap = ap.replace(/[.\s]/g, "").toUpperCase(); // "PM"
    return minute === "00" ? `${hour}${ap}` : `${hour}:${minute}${ap}`;
  }
  function bracketWhen(m) {
    const ko = m.kickoff_utc ? (typeof m.kickoff_utc === "number" ? m.kickoff_utc : Date.parse(m.kickoff_utc)) : 0;
    if (ko) {
      const d = new Date(ko);
      return `<span class="bd-d">${etDateLabel(d)}</span><span class="bd-t">${etTimeLabel(d)}</span>`;
    }
    if (m.date) {
      const d = new Date(m.date + "T12:00:00");
      return `<span class="bd-d">${MONTHS_EN[d.getMonth()]}${String(d.getDate()).padStart(2, "0")}</span>`;
    }
    return "";
  }

  function statusBadge(m) {
    if (m.status === "live") {
      const raw = m.minute != null ? String(m.minute) : "";
      const min = raw ? ` <span class="min">${/^\d+$/.test(raw) ? raw + "'" : raw}</span>` : "";
      return `<span class="badge live">● EN VIVO${min}</span>`;
    }
    if (m.status === "finished") return `<span class="badge done">Final</span>`;
    return `<span class="badge soon">Próximo</span>`;
  }

  function sortedMatchKeys() {
    return Object.keys(state.results.matches)
      .filter((k) => state.bets.predictions[k]) // only matches in the quiniela
      .sort((a, b) => {
        const ma = state.results.matches[a], mb = state.results.matches[b];
        const ka = ma.kickoff_utc ? Date.parse(ma.kickoff_utc) : 0;
        const kb = mb.kickoff_utc ? Date.parse(mb.kickoff_utc) : 0;
        return (ka || 0) - (kb || 0);
      });
  }

  /* ---------- Views ---------- */

  function renderPosiciones() {
    const rows = assignPrizes(Scoring.computeStandings(state.bets, state.results, state.countLive));
    const wrap = el("div");

    wrap.appendChild(el("div", "prizes",
      `<div class="pot">💰 Bolsa: <strong>${fmtMXN(POT)} MXN</strong></div>
       <div class="splits">
         <span class="sp"><span class="med">🥇</span> <b class="spmoney">${fmtMXN(POT * 0.60)}</b></span>
         <span class="sp"><span class="med">🥈</span> <b class="spmoney">${fmtMXN(POT * 0.25)}</b></span>
         <span class="sp"><span class="med">🥉</span> <b class="spmoney">${fmtMXN(POT * 0.15)}</b></span>
       </div>
       <div class="prizenote">Montos en pesos mexicanos (MXN). Empates: se reparten el premio del lugar en partes iguales.</div>`));

    const ctrl = el("label", "live-toggle",
      `<input type="checkbox" ${state.countLive ? "checked" : ""}> Incluir partidos en vivo (puntos provisionales)`);
    ctrl.querySelector("input").addEventListener("change", (e) => {
      state.countLive = e.target.checked; render();
    });
    wrap.appendChild(ctrl);

    const W = computeWinProbs();
    const winp = W.probs;
    const fmtWin = (p) => (p >= 0.005 ? Math.round(p * 100) + "%" : (p > 0 ? "<1%" : "—"));

    const table = el("table", "standings");
    table.innerHTML = `<thead><tr>
        <th>#</th><th>Jugador</th><th>Pts</th>
        <th title="Probabilidad de terminar 1º (simulación de los partidos que faltan)">Gana</th>
        <th title="Premio según posición actual (MXN)">Premio<span class="thmxn"> (MXN)</span></th>
      </tr></thead>`;
    const tb = el("tbody");
    rows.forEach((r, i) => {
      const tr = el("tr", i === 0 ? "leader" : "");
      const prov = r.provisional > 0 ? ` <span class="prov" title="puntos provisionales en vivo">(+${r.provisional})</span>` : "";
      const medal = r.rank <= 3 ? ["🥇", "🥈", "🥉"][r.rank - 1] + " " : "";
      const prize = r.prize > 0 ? `<span class="money">${fmtMXN(r.prize)}</span>` : "—";
      tr.innerHTML = `<td class="rank">${medal}${r.rank}</td>
        <td class="pname">${r.player}</td>
        <td class="pts"><strong>${r.points}</strong>${prov}</td>
        <td class="winp">${fmtWin(winp[r.player] || 0)}</td>
        <td class="prize">${prize}</td>`;
      tr.addEventListener("click", () => { state.player = r.player; switchView("jugador"); });
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    wrap.appendChild(table);
    wrap.appendChild(el("p", "hint", "Toca un jugador para ver su detalle. <b>Gana</b> = prob. de terminar 1º (simulación Monte Carlo de los juegos restantes con el modelo de odds; suma 100%). Puntos: acertar ganador/empate +1 · marcador exacto +2."));

    if (W.R >= 1) {
      wrap.appendChild(el("h3", "sechdr", "Proyección Monte Carlo"));
      wrap.appendChild(el("p", "hint", "Puntos esperados de cada jugador hasta el cierre de la fase de grupos (promedio de 5,000 simulaciones)."));
      wrap.appendChild(buildMonteCarloChart(W));
    }
    return wrap;
  }

  function predChip(pred, actual, withName, name) {
    const s = Scoring.scoreOne(pred, actual);
    const cls = actual ? (s.exact ? "p2" : s.points === 1 ? "p1" : "p0") : "pna";
    const val = pred && pred[0] != null ? `${pred[0]}-${pred[1]}` : "—";
    const nm = withName ? `<span class="cn">${name}</span>` : "";
    const pp = actual ? `<span class="cp">${s.points}</span>` : "";
    return `<span class="chip ${cls}">${nm}<span class="cv">${val}</span>${pp}</span>`;
  }

  function renderPartidos() {
    const wrap = el("div");
    const groups = ["Todos", ...Array.from(new Set(sortedMatchKeys()
      .map((k) => state.results.matches[k].group))).sort()];
    const bar = el("div", "filters");
    bar.innerHTML = `<select id="fgroup">${groups.map((g) => `<option>${g}</option>`).join("")}</select>
      <label class="chk"><input type="checkbox" id="fdone"> Incluir finalizados</label>`;
    wrap.appendChild(bar);

    const list = el("div", "matches");
    wrap.appendChild(list);

    function paint() {
      const g = $("#fgroup", bar).value;
      const showDone = $("#fdone", bar).checked; // default off: only En Vivo + Próximos
      list.innerHTML = "";
      let lastDay = null;
      let shown = 0;
      sortedMatchKeys().forEach((k) => {
        const m = state.results.matches[k];
        if (g !== "Todos" && m.group !== g) return;
        if (!showDone && m.status === "finished") return;
        if (m.date !== lastDay) {
          lastDay = m.date;
          list.appendChild(el("h3", "dayhdr", fmtDay(m.date)));
        }
        shown++;
        const preds = state.bets.predictions[k] || {};
        const score = m.score ? `${m.score[0]} - ${m.score[1]}` : "vs";
        const card = el("div", "match");
        card.innerHTML = `
          <div class="mhead">
            <span class="mgroup">${m.group || ""}</span>
            <span class="mtime">${fmtKickoffTime(m)}</span>
            ${statusBadge(m)}
          </div>
          <div class="mscore">
            <div class="side home">${teamHTML(m.home)}</div>
            <div class="score ${m.status}">${score}</div>
            <div class="side away">${teamHTML(m.away)}</div>
          </div>`;
        const chips = el("div", "preds");
        Object.keys(preds).sort((a, b) => a.localeCompare(b, "es")).forEach((p) => {
          chips.insertAdjacentHTML("beforeend", predChip(preds[p], m.score, true, p));
        });
        card.appendChild(chips);
        list.appendChild(card);
      });
      if (!shown) list.appendChild(el("p", "hint", "No hay partidos para este filtro."));
    }
    bar.addEventListener("change", paint);
    paint();
    return wrap;
  }

  function renderJugador() {
    const wrap = el("div");
    const players = state.bets.players.slice().sort((a, b) => a.localeCompare(b, "es"));
    state.player = state.player || players[0];
    const sel = el("select", "pselect",
      players.map((p) => `<option ${p === state.player ? "selected" : ""}>${p}</option>`).join(""));
    sel.addEventListener("change", (e) => { state.player = e.target.value; render(); });
    wrap.appendChild(sel);

    const rows = Scoring.computeStandings(state.bets, state.results, state.countLive);
    const me = rows.find((r) => r.player === state.player) || { points: 0, exact: 0, outcome: 0, played: 0, rank: "-" };
    wrap.appendChild(el("div", "summary",
      `<span class="bignum">${me.points}</span> pts ·
       Pos. <strong>${me.rank}</strong> ·
       ${me.exact} exactos · ${me.outcome} resultados`));

    const list = el("div", "matches");
    let lastDay = null;
    sortedMatchKeys().forEach((k) => {
      const m = state.results.matches[k];
      const pred = (state.bets.predictions[k] || {})[state.player];
      if (m.date !== lastDay) { lastDay = m.date; list.appendChild(el("h3", "dayhdr", fmtDay(m.date))); }
      const row = el("div", "jrow");
      const score = m.score ? `${m.score[0]}-${m.score[1]}` : "—";
      row.innerHTML = `
        <div class="jmatch">${teamHTML(m.home)} <span class="jvs">${score}</span> ${teamHTML(m.away)}</div>
        <div class="jpred">${predChip(pred, m.score, false)}</div>`;
      list.appendChild(row);
    });
    wrap.appendChild(list);
    return wrap;
  }

  /* ---------- Grupos + Bracket ---------- */

  // Compute group tables from finished group-stage matches (3-1-0 points).
  function computeGroupTables() {
    const groups = {};
    for (const m of Object.values(state.results.matches)) {
      const g = m.group;
      if (!g || g.indexOf("Group") !== 0) continue;
      groups[g] = groups[g] || {};
      for (const t of [m.home, m.away]) {
        groups[g][t] = groups[g][t] || { team: t, pj: 0, g: 0, e: 0, p: 0, gf: 0, ga: 0, pts: 0 };
      }
      if (m.status === "finished" && m.score) {
        const [hs, as] = m.score, H = groups[g][m.home], A = groups[g][m.away];
        H.pj++; A.pj++; H.gf += hs; H.ga += as; A.gf += as; A.ga += hs;
        if (hs > as) { H.g++; A.p++; H.pts += 3; }
        else if (hs < as) { A.g++; H.p++; A.pts += 3; }
        else { H.e++; A.e++; H.pts++; A.pts++; }
      }
    }
    const out = {};
    Object.keys(groups).sort().forEach((g) => {
      out[g] = Object.values(groups[g]).sort((a, b) =>
        b.pts - a.pts || (b.gf - b.ga) - (a.gf - a.ga) || b.gf - a.gf ||
        a.team.localeCompare(b.team, "es"));
    });
    return out;
  }

  // A knockout slot is a real team (flag + name) or a placeholder code (e.g. "2A").
  function koTeamHTML(name) {
    if (state.teams[name]) return teamHTML(name);
    return `<span class="team ph"><span class="phcode">${name || "?"}</span></span>`;
  }

  const KO_ROUNDS = [
    ["Round of 32", "Dieciseisavos de final"],
    ["Round of 16", "Octavos de final"],
    ["Quarter-final", "Cuartos de final"],
    ["Semi-final", "Semifinales"],
    ["Match for third place", "Tercer lugar"],
    ["Final", "Final"],
  ];
  const KO_ES = Object.fromEntries(KO_ROUNDS);
  const roundES = (r) => KO_ES[r] || r || "";

  // FIFA 2026 knockout tree: match num -> the two feeder match nums. Fixed
  // structure (teams fill in as rounds are played). Left half feeds Semi 101,
  // right half feeds Semi 102; the Final is 104, third place 103.
  const KO_TREE = {
    89: [74, 77], 90: [73, 75], 91: [76, 78], 92: [79, 80],
    93: [83, 84], 94: [81, 82], 95: [86, 88], 96: [85, 87],
    97: [89, 90], 98: [93, 94], 99: [91, 92], 100: [95, 96],
    101: [97, 98], 102: [99, 100], 104: [101, 102],
  };
  const KO_COL_ES = ["16", "8", "4", "SF"]; // R32→SF column headers (compact)

  function renderGrupos() {
    const wrap = el("div");

    // --- Group standings ---
    wrap.appendChild(el("h2", "sechdr", "Fase de Grupos"));
    wrap.appendChild(el("p", "hint", "Clasifican los 2 primeros de cada grupo (y los 8 mejores terceros). 3 pts victoria · 1 empate."));
    const grid = el("div", "groupgrid");
    const tables = computeGroupTables();
    Object.keys(tables).forEach((g) => {
      const box = el("div", "grouptable");
      box.appendChild(el("h3", "ghdr", g.replace("Group", "Grupo")));
      const t = el("table", "gtbl");
      t.innerHTML = `<thead><tr><th>#</th><th>Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>DG</th><th>Pts</th></tr></thead>`;
      const tb = el("tbody");
      tables[g].forEach((r, idx) => {
        const cls = idx < 2 ? "q1" : idx === 2 ? "q3" : "";
        const dg = r.gf - r.ga;
        const tr = el("tr", cls);
        tr.innerHTML = `<td class="rank">${idx + 1}</td>
          <td class="gteam">${koTeamHTML(r.team)}</td>
          <td>${r.pj}</td><td>${r.g}</td><td>${r.e}</td><td>${r.p}</td>
          <td>${dg > 0 ? "+" + dg : dg}</td><td class="gpts">${r.pts}</td>`;
        tb.appendChild(tr);
      });
      t.appendChild(tb);
      box.appendChild(t);
      grid.appendChild(box);
    });
    wrap.appendChild(grid);

    // --- Knockout bracket (horizontal, rounds → Campeón) ---
    appendKnockout(wrap, tables, { header: true });
    return wrap;
  }

  // Dedicated "Eliminatorias" view: the knockout bracket with live scores.
  function renderEliminatorias() {
    const wrap = el("div");
    wrap.appendChild(el("h2", "sechdr", "Eliminatorias"));
    wrap.appendChild(el("p", "hint", "Marcadores en vivo conforme se juegan · Horarios en hora del Este (ET) · 16 = Dieciseisavos · 8 = Octavos · 4 = Cuartos · SF = Semifinal · F = Final."));
    appendKnockout(wrap, computeGroupTables(), { header: false });
    return wrap;
  }

  // Builds the MIRRORED knockout bracket into `wrap`: left half flows left→right
  // and right half right→left toward a center column (Final + 🏆 + 3er lugar), so
  // it's clear which match winners meet next. `tables` = group standings (only
  // used to label any still-undecided slot). Scores/live status come from each
  // match and update as games are played.
  function appendKnockout(wrap, tables, opts) {
    if (opts && opts.header) {
      wrap.appendChild(el("h2", "sechdr", "Eliminatorias"));
    }

    // Index every knockout match by its FIFA number (needed to advance winners).
    const byNum = {};
    Object.values(state.results.matches).forEach((m) => { if (m.num != null) byNum[m.num] = m; });

    // Winner side of a finished match (0=home, 1=away) via score then penalties.
    const decideWinner = (m) => {
      if (!(m && m.status === "finished" && m.score)) return null;
      if (m.score[0] !== m.score[1]) return m.score[0] > m.score[1] ? 0 : 1;
      if (m.pens) return m.pens[0] > m.pens[1] ? 0 : 1;
      return null;
    };

    const gt = tables; // group tables (Group X -> sorted rows)
    // Resolve a slot code to a real team, AUTO-ADVANCING winners: "W74" -> winner
    // of match 74, "L101" -> loser of match 101 (recursively), so a team appears
    // in the next round the moment its match is decided (no wait on the feed).
    const teamOfSlot = (code, seen) => {
      if (!code) return null;
      if (state.teams[code]) return code;              // already a real team
      const wl = /^([WL])(\d+)$/.exec(code);
      if (wl) {
        const num = +wl[2];
        if (seen && seen.has(num)) return null;         // guard against cycles
        const m = byNum[num];
        const w = decideWinner(m);
        if (w == null) return null;                     // not decided yet
        const s = new Set(seen); s.add(num);
        const winnerCode = w === 0 ? m.home : m.away;
        const loserCode = w === 0 ? m.away : m.home;
        return teamOfSlot(wl[1] === "W" ? winnerCode : loserCode, s);
      }
      return null;
    };
    const resolveSlot = (code) => {
      if (state.teams[code]) return { name: code, proj: false };
      const advanced = teamOfSlot(code, new Set());     // W/L codes -> advanced team
      if (advanced) return { name: advanced, proj: false };
      const m = /^([12])([A-L])$/.exec(code || "");
      if (m) {
        const arr = gt["Group " + m[2]];
        if (arr && arr[+m[1] - 1]) return { name: arr[+m[1] - 1].team, proj: true };
      }
      return { name: null, code: code };
    };
    // Flags only (no country names). Short placeholder when the slot isn't
    // decided yet ("3º", "1A"); W/L codes (winner/loser of a match) show "—".
    const slotShort = (code) => {
      if (/^3/.test(code || "")) return "3º";
      const m = /^([12])([A-L])$/.exec(code || "");
      return m ? code : "—";
    };

    // pen = penalty-shootout count for this side (shown as "(4)"), or null.
    const brTeam = (code, score, pen, win) => {
      const r = resolveSlot(code);
      let inner;
      if (r.name && state.teams[r.name]) {
        const t = state.teams[r.name];
        inner = `<span class="flag ${r.proj ? "proj" : ""}" title="${t.es}">${t.flag}</span>`;
      } else {
        inner = `<span class="bn ph">${slotShort(code)}</span>`;
      }
      const penHTML = pen != null ? `<span class="bpen">(${pen})</span>` : "";
      return `<div class="bteam ${win ? "bw" : ""}">${inner}<span class="bsc">${score != null ? score : ""}${penHTML}</span></div>`;
    };
    const bnode = (m) => {
      const w = decideWinner(m);
      const w0 = w === 0, w1 = w === 1;
      const p0 = m.pens ? m.pens[0] : null, p1 = m.pens ? m.pens[1] : null;
      const n = el("div", "bmatch" + (m.status === "live" ? " blive" : ""));
      const ds = bracketWhen(m);
      n.innerHTML = `<div class="bdate">${ds}</div>` +
        brTeam(m.home, m.score ? m.score[0] : null, p0, w0) + brTeam(m.away, m.score ? m.score[1] : null, p1, w1);
      return n;
    };

    // One half of the draw, as columns [R32, R16, QF, SF] in vertical (DFS) order.
    const sideColumns = (rootNum) => {
      const levels = { 0: [], 1: [], 2: [], 3: [] };
      const rec = (num, depth) => {
        const kids = KO_TREE[num];
        if (kids) { rec(kids[0], depth - 1); rec(kids[1], depth - 1); }
        levels[depth].push(num);
      };
      rec(rootNum, 3);
      return [levels[0], levels[1], levels[2], levels[3]];
    };
    const leftCols = sideColumns(101);  // R32,R16,QF,SF feeding Semi 101
    const rightCols = sideColumns(102); // R32,R16,QF,SF feeding Semi 102

    const makeCol = (nums, roundIdx, side) => {
      const col = el("div", `bround ${side}`);
      col.innerHTML = `<div class="brh">${KO_COL_ES[roundIdx]}</div>`;
      const body = el("div", "bbody");
      nums.forEach((n) => { if (byNum[n]) body.appendChild(bnode(byNum[n])); });
      col.appendChild(body);
      return col;
    };

    const bracket = el("div", "bracket2 mirror");
    // Left half: R32 → SF (left to right)
    leftCols.forEach((nums, i) => bracket.appendChild(makeCol(nums, i, "left")));

    // Center: 🏆 + Final + Campeón + 3er lugar
    const final = byNum[104];
    let champ = null;
    const fw = decideWinner(final);
    if (fw != null) champ = teamOfSlot(fw === 0 ? final.home : final.away, new Set());
    const center = el("div", "bround center-col");
    center.innerHTML = `<div class="btrophy">🏆</div><div class="brh">F</div>`;
    if (final) center.appendChild(bnode(final));
    const champBox = el("div", "bchamp");
    champBox.innerHTML = champ
      ? (state.teams[champ] ? `<span class="flag">${state.teams[champ].flag}</span> ${state.teams[champ].es}` : champ)
      : "Campeón";
    center.appendChild(champBox);
    const tp = byNum[103];
    if (tp) {
      center.appendChild(el("div", "b3rdlabel", "🥉 Tercer lugar"));
      center.appendChild(bnode(tp));
    }
    bracket.appendChild(center);

    // Right half: SF → R32 (center to right; columns reversed, content mirrored)
    [3, 2, 1, 0].forEach((i) => bracket.appendChild(makeCol(rightCols[i], i, "right")));

    wrap.appendChild(bracket);
  }

  /* ---------- Cuotas (estimated odds) ---------- */

  /* ---------- Title Pie: P(champion) via full-tournament Monte Carlo ---------- */
  let _titleCache = { sig: null, probs: null };
  const ELO_K = 0.0022; // Elo points -> goal-supremacy rating scale (tuned for a consensus spread)
  function buildTitleProbs() {
    // Title Pie uses an Elo power ranking (not the bookmaker-fit match ratings).
    const elo = state.elo || {};
    const en = Object.keys(elo);
    let ratings;
    if (en.length) {
      const mean = en.reduce((s, n) => s + elo[n], 0) / en.length;
      ratings = {}; en.forEach((n) => (ratings[n] = (elo[n] - mean) * ELO_K));
    } else {
      ratings = state.ratings || {}; // fallback if the Elo file is missing
    }
    const ms = Object.values(state.results.matches);
    const sampleScore = (h, a) => {
      const { lh, la } = Odds.lambdasFor({ home: h, away: a }, ratings);
      return [poissonSample(lh), poissonSample(la)];
    };
    const koWinner = (a, b) => {
      const s = sampleScore(a, b);
      if (s[0] > s[1]) return a; if (s[1] > s[0]) return b;
      const ra = ratings[a] || 0, rb = ratings[b] || 0;       // penalties: rating-weighted
      return Math.random() < 1 / (1 + Math.exp(-(ra - rb))) ? a : b;
    };
    const ap = (st, h, a, s) => {
      const [hs, as] = s;
      st[h].gf += hs; st[h].gd += hs - as; st[a].gf += as; st[a].gd += as - hs;
      if (hs > as) st[h].pts += 3; else if (hs < as) st[a].pts += 3; else { st[h].pts++; st[a].pts++; }
    };
    const cmp = (a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf || a.t.localeCompare(b.t);

    const groupTeams = {}, base = {}, rem = [], KO32 = [];
    let finishedG = 0;
    for (const m of ms) {
      if (m.group && m.group.indexOf("Group") === 0) {
        const g = m.group;
        (groupTeams[g] = groupTeams[g] || new Set()).add(m.home); groupTeams[g].add(m.away);
        base[m.home] = base[m.home] || { g, pts: 0, gd: 0, gf: 0 };
        base[m.away] = base[m.away] || { g, pts: 0, gd: 0, gf: 0 };
        if (m.status === "finished" && m.score) { ap(base, m.home, m.away, m.score); finishedG++; }
        else rem.push([m.home, m.away]);
      } else if (m.round === "Round of 32") KO32.push([m.home, m.away]);
    }
    // Index KO matches by number so the sim can HONOR already-played results
    // (eliminated teams stay eliminated → 0% champion).
    const byNum = {};
    let finishedKO = 0;
    for (const m of ms) {
      if (m.num != null) byNum[m.num] = m;
      if (m.num != null && m.num >= 73 && m.status === "finished" && m.score) finishedKO++;
    }
    const koWinnerActual = (m) => {
      if (!(m && m.status === "finished" && m.score)) return null;
      if (m.score[0] !== m.score[1]) return m.score[0] > m.score[1] ? m.home : m.away;
      if (m.pens) return m.pens[0] > m.pens[1] ? m.home : m.away;
      return null;
    };
    const sig = `${finishedG}|${KO32.length}|${finishedKO}|${state.bets.players.length}`;
    if (_titleCache.sig === sig) return _titleCache.probs;
    if (!KO32.length) { _titleCache = { sig, probs: {} }; return {}; }

    const resolve = (code, W, Ru, tbg, used) => {
      let m;
      if ((m = /^1([A-L])$/.exec(code))) return W[m[1]];
      if ((m = /^2([A-L])$/.exec(code))) return Ru[m[1]];
      if (/^3/.test(code)) {
        const gs = code.slice(1).split("/");
        for (const g of gs) if (tbg[g] && !used.has(g)) { used.add(g); return tbg[g]; }
        for (const g in tbg) if (!used.has(g)) { used.add(g); return tbg[g]; }
      }
      return code; // already a real team (knockout under way)
    };

    const N = 2500, champ = {};
    for (let n = 0; n < N; n++) {
      const st = {}; for (const k in base) st[k] = { ...base[k] };
      for (const [h, a] of rem) ap(st, h, a, sampleScore(h, a));
      const W = {}, Ru = {}, thirds = [];
      for (const g in groupTeams) {
        const arr = [...groupTeams[g]].map((t) => ({ t, ...(st[t] || { pts: 0, gd: 0, gf: 0 }) }));
        arr.sort(cmp);
        const gl = g.slice(6);
        W[gl] = arr[0].t; Ru[gl] = arr[1].t;
        thirds.push({ t: arr[2].t, g: gl, pts: arr[2].pts, gd: arr[2].gd, gf: arr[2].gf });
      }
      thirds.sort(cmp);
      const tbg = {}; thirds.slice(0, 8).forEach((x) => (tbg[x.g] = x.t));
      const used = new Set();
      // Walk the real bracket tree: a finished match returns its actual winner
      // (so losers can never advance); undecided matches are simulated.
      const advance = (num) => {
        const actual = koWinnerActual(byNum[num]);
        if (actual) return actual;
        const kids = KO_TREE[num];
        let a, b;
        if (kids) { a = advance(kids[0]); b = advance(kids[1]); }
        else { const m = byNum[num]; a = resolve(m.home, W, Ru, tbg, used); b = resolve(m.away, W, Ru, tbg, used); }
        return koWinner(a, b);
      };
      const c = advance(104);
      if (c) champ[c] = (champ[c] || 0) + 1;
    }
    const probs = {}; for (const t in champ) probs[t] = champ[t] / N;
    _titleCache = { sig, probs };
    return probs;
  }

  function buildTitlePie(probs) {
    const box = el("div", "titlepie");
    const entries = Object.entries(probs).sort((a, b) => b[1] - a[1]);
    const n = entries.length || 1;
    const cx = 180, cy = 180, r = 160;
    const color = (i) => `hsl(${Math.round(i * 360 / n)} 70% 55%)`;
    let ang = -Math.PI / 2, svg = `<svg viewBox="0 0 360 360" class="pie">`;
    entries.forEach(([t, v], i) => {
      const a0 = ang, a1 = ang + v * 2 * Math.PI; ang = a1;
      const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
      const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
      const large = (a1 - a0) > Math.PI ? 1 : 0;
      svg += `<path d="M${cx} ${cy} L${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 ${large} 1 ${x1.toFixed(1)} ${y1.toFixed(1)} Z" fill="${color(i)}" stroke="#1b0705" stroke-width="0.6"/>`;
    });
    svg += `</svg>`;
    box.innerHTML = svg;
    const leg = el("div", "pieleg");
    let otros = 0;
    entries.forEach(([t, v], i) => {
      if (v < 0.01) { otros += v; return; }
      const tm = state.teams[t];
      leg.insertAdjacentHTML("beforeend",
        `<span class="pli"><span class="psw" style="background:${color(i)}"></span>${tm ? tm.flag + " " + tm.es : t} <i>${Math.round(v * 100)}%</i></span>`);
    });
    if (otros > 0.005) leg.insertAdjacentHTML("beforeend", `<span class="pli"><span class="psw" style="background:#6b6b6b"></span>Otros <i>${Math.round(otros * 100)}%</i></span>`);
    box.appendChild(leg);
    return box;
  }

  const ODDS_MARGIN = 0.07; // small overround so numbers read like a sportsbook

  function renderOdds() {
    const wrap = el("div");

    // How-to-read panel (top)
    wrap.appendChild(el("div", "oddshelp",
      `<p class="ohb">⚠️ <strong>Cuotas estimadas — NO son de casa de apuestas.</strong></p>
       <p>Cómo leerlas (cuota decimal estilo momio europeo): si apuestas $100 a una cuota de
       <b>2.00</b>, recibes $200 (ganancia $100). Cuanto <b>más baja</b> la cuota, más probable según el modelo.
       El <b>%</b> es la probabilidad estimada.</p>
       <ul class="ohl">
         <li><b>1X2</b> — resultado: gana <b>Local</b>, <b>Empate</b> o gana <b>Visitante</b>.</li>
         <li><b>Total 2.5</b> — <b>Más</b> = 3+ goles en el partido; <b>Menos</b> = 2 o menos.</li>
         <li><b>Marcador más probable</b> — los 3 marcadores con mayor probabilidad.</li>
       </ul>`));

    // Title Pie — probability of being crowned champion (full-tournament sim).
    const title = buildTitleProbs();
    if (Object.keys(title).length) {
      wrap.appendChild(el("h3", "sechdr", "🏆 Title Pie — Probabilidad de ser campeón"));
      wrap.appendChild(el("p", "hint", "Simulación del torneo completo (grupos restantes → eliminatorias) usando un <b>power ranking estilo Elo</b> + resultados actuales. Suma 100%."));
      wrap.appendChild(buildTitlePie(title));
    }

    const form = Odds.teamStrengths(Object.values(state.results.matches));
    const dec = (p) => Odds.dec(p, ODDS_MARGIN), pct = (p) => Math.round(p * 100);

    // Live + upcoming matches with two known teams, soonest first.
    const keys = Object.keys(state.results.matches).filter((k) => {
      const m = state.results.matches[k];
      return (m.status === "live" || m.status === "scheduled") &&
        state.teams[m.home] && state.teams[m.away];
    }).sort((a, b) =>
      (Date.parse(state.results.matches[a].kickoff_utc) || 0) -
      (Date.parse(state.results.matches[b].kickoff_utc) || 0));

    if (!keys.length) {
      wrap.appendChild(el("p", "hint", "No hay partidos en vivo o próximos con equipos definidos."));
      return wrap;
    }

    const list = el("div", "oddslist");
    let lastDay = null;
    keys.forEach((k) => {
      const m = state.results.matches[k];
      const { lh, la } = Odds.lambdasFor(m, state.ratings, form);

      let remFrac = 1, curH = 0, curA = 0;
      if (m.status === "live") {
        const n = parseInt(m.minute, 10);
        const mm = Number.isFinite(n) ? n : (String(m.minute).toUpperCase() === "HT" ? 45 : 0);
        remFrac = Math.max(0.02, (90 - Math.min(mm, 90)) / 90);
        if (m.score) { curH = m.score[0]; curA = m.score[1]; }
      }
      const od = Odds.matchOdds({ lh, la, curH, curA, remFrac });

      if (m.date !== lastDay) { lastDay = m.date; list.appendChild(el("h3", "dayhdr", fmtDay(m.date))); }

      const chip = (label, p) =>
        `<span class="ochip">${label ? `<span class="ol">${label}</span>` : ""}<b>${dec(p).toFixed(2)}</b><i>${pct(p)}%</i></span>`;
      const card = el("div", "oddscard");
      card.innerHTML = `
        <div class="mhead">
          <span class="mgroup">${m.group ? m.group.replace("Group", "Grupo") : roundES(m.round)}</span>
          <span class="mtime">${fmtKickoffTime(m)}</span>${statusBadge(m)}
        </div>
        <div class="oteams">${koTeamHTML(m.home)}<span class="ovs">${m.score ? m.score[0] + "–" + m.score[1] : "vs"}</span>${koTeamHTML(m.away)}</div>
        <div class="omkt"><div class="omh">Resultado (1X2)</div>
          <div class="orow">${chip("Local", od.p1)}${chip("Empate", od.pX)}${chip("Visit.", od.p2)}</div></div>
        <div class="omkt"><div class="omh">Total de goles 2.5</div>
          <div class="orow">${chip("Más", od.over)}${chip("Menos", od.under)}</div></div>
        <div class="omkt"><div class="omh">Marcador más probable</div>
          <div class="orow">${od.scores.map((s) => `<span class="ochip"><b>${s.s}</b><i>${pct(s.p)}%</i></span>`).join("")}</div></div>`;
      list.appendChild(card);
    });
    wrap.appendChild(list);

    // Model description (bottom)
    wrap.appendChild(el("div", "oddsmodel",
      `<h3>Modelo in-house</h3>
       <p>Estas cuotas las genera un <b>modelo propio (in-house)</b>, no provienen de una casa de
       apuestas. Cada equipo tiene un <i>rating</i> de fuerza calibrado a partir de cuotas de
       referencia del Mundial; con la diferencia de ratings (más una ventaja de localía) estimamos
       los goles esperados de cada lado y aplicamos un modelo de <b>Poisson</b> para obtener las
       probabilidades de 1X2, Más/Menos 2.5 y los marcadores más probables. En partidos en vivo se
       ajusta por el minuto y el marcador actual. Se añade un pequeño margen para que las cuotas se
       lean como las de un libro. <b>Solo para diversión del grupo.</b></p>`));
    return wrap;
  }

  /* ---------- Shell ---------- */

  function switchView(v) { state.view = v; render(); window.scrollTo(0, 0); }

  function render() {
    const main = $("#content");
    main.innerHTML = "";
    if (state.view === "eliminatorias") main.appendChild(renderEliminatorias());
    else if (state.view === "posiciones") main.appendChild(renderPosiciones());
    else if (state.view === "partidos") main.appendChild(renderPartidos());
    else if (state.view === "grupos") main.appendChild(renderGrupos());
    else if (state.view === "odds") main.appendChild(renderOdds());
    else main.appendChild(renderJugador());

    document.querySelectorAll(".tab").forEach((t) =>
      t.classList.toggle("active", t.dataset.view === state.view));

    const gen = state.results.generated_at ? new Date(state.results.generated_at) : new Date();
    $("#updated").textContent = "Actualizado: " + gen.toLocaleString("es-MX",
      { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  async function refresh() {
    try {
      const d = await DataLayer.load();
      state.bets = d.bets; state.results = d.results; state.teams = d.teams; state.ratings = d.ratings || {}; state.elo = d.elo || {};
      render(); // paint committed data immediately (fast, same-origin only)
    } catch (e) {
      console.error(e);
      $("#content").innerHTML = `<p class="error">No se pudieron cargar los datos: ${e.message}</p>`;
      return;
    }
    // Then overlay live scores in the background and re-render if anything changed.
    try {
      if (state.results && await DataLayer.applyLive(state.results)) render();
    } catch (e) { console.warn("live overlay failed:", e); }
  }

  function init() {
    document.querySelectorAll(".tab").forEach((t) =>
      t.addEventListener("click", () => switchView(t.dataset.view)));
    refresh();
    setInterval(refresh, REFRESH_MS);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
