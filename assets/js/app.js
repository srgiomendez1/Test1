/* UI rendering for the World Cup 2026 quiniela tracker (Spanish). */
(function () {
  "use strict";

  const REFRESH_MS = 30 * 1000;
  const DAYS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

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

  let state = { bets: null, results: null, teams: {}, ratings: {}, view: "posiciones", player: null, countLive: true };

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
      `<div class="pot">💰 Bolsa: <strong>${fmtMXN(POT)}</strong></div>
       <div class="splits">
         <span class="sp"><span class="med">🥇</span> <b class="spmoney">${fmtMXN(POT * 0.60)}</b></span>
         <span class="sp"><span class="med">🥈</span> <b class="spmoney">${fmtMXN(POT * 0.25)}</b></span>
         <span class="sp"><span class="med">🥉</span> <b class="spmoney">${fmtMXN(POT * 0.15)}</b></span>
       </div>
       <div class="prizenote">Empates: se reparten el premio del lugar en partes iguales.</div>`));

    const ctrl = el("label", "live-toggle",
      `<input type="checkbox" ${state.countLive ? "checked" : ""}> Incluir partidos en vivo (puntos provisionales)`);
    ctrl.querySelector("input").addEventListener("change", (e) => {
      state.countLive = e.target.checked; render();
    });
    wrap.appendChild(ctrl);

    const table = el("table", "standings");
    table.innerHTML = `<thead><tr>
        <th>#</th><th>Jugador</th><th>Pts</th>
        <th title="Premio según posición actual">Premio</th>
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
        <td class="prize">${prize}</td>`;
      tr.addEventListener("click", () => { state.player = r.player; switchView("jugador"); });
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    wrap.appendChild(table);
    wrap.appendChild(el("p", "hint", "Toca un jugador para ver su detalle. Acertar ganador/empate: +1 · Marcador exacto: +2 (3 en total)."));
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
    state.player = state.player || state.bets.players[0];
    const sel = el("select", "pselect",
      state.bets.players.map((p) => `<option ${p === state.player ? "selected" : ""}>${p}</option>`).join(""));
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

    // --- Knockout bracket (round by round) ---
    wrap.appendChild(el("h2", "sechdr", "Eliminatorias"));
    const allKo = Object.values(state.results.matches).filter((m) => m.round && (!m.group || m.group.indexOf("Group") !== 0));
    const bracket = el("div", "bracket");
    KO_ROUNDS.forEach(([en, es]) => {
      const ms = allKo.filter((m) => m.round === en)
        .sort((a, b) => (Date.parse(a.kickoff_utc) || 0) - (Date.parse(b.kickoff_utc) || 0));
      if (!ms.length) return;
      const col = el("div", "round");
      col.appendChild(el("h3", "rhdr", es));
      ms.forEach((m) => {
        const score = m.score ? `${m.score[0]}–${m.score[1]}` : "vs";
        const tie = el("div", "tie");
        tie.innerHTML = `
          <div class="tiehead"><span class="tdate">${fmtDay(m.date)} · ${fmtKickoffTime(m)}</span>${statusBadge(m)}</div>
          <div class="tierow">${koTeamHTML(m.home)}<span class="tscore ${m.status}">${score}</span>${koTeamHTML(m.away)}</div>`;
        col.appendChild(tie);
      });
      bracket.appendChild(col);
    });
    wrap.appendChild(bracket);
    return wrap;
  }

  /* ---------- Cuotas (estimated odds) ---------- */

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
    if (state.view === "posiciones") main.appendChild(renderPosiciones());
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
      state.bets = d.bets; state.results = d.results; state.teams = d.teams; state.ratings = d.ratings || {};
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
