# Handover — Term Premium Monitor

Read this first in a fresh session. It captures everything needed to continue
the **brokered-CD term premium** work without re-deriving context. The repo is
cloned fresh each session, so this file is the source of truth.

---

## 1. What this is

An interactive dashboard (+ a parallel Python package) that explains, for
**Flagstar Treasury / ALM**, how brokered CD levels become the FTP **term
premium** — the audience is the treasurer and liquidity manager. It is both a
weekly monitoring tool and a standing methodology reference. Visual-heavy, but
with real market/technical substance.

- **Repo / branch:** `srgiomendez1/Test1`, branch
  `claude/term-premium-cd-dashboard-2zq56f`. (The rest of this repo is an
  unrelated World Cup betting app — our work lives entirely under
  `term-premium/`.) Never push to `main`. Only push to the branch above.
- **Main deliverable:** `term-premium/index.html` — a single self-contained
  file (~345 KB; embeds SheetJS 0.18.5 for .xlsx reading/writing). No network,
  no build step.
- **Published artifact (same URL on every redeploy):**
  `https://claude.ai/code/artifact/0dc3a05e-7188-483a-9419-a643c721c83c`
  To update it: `Artifact` with `file_path` = `term-premium/index.html` in a
  session that published it, or pass that `url` from a new session.
- **Workstation package:** `term-premium/workstation/` — Python mirror of the
  methodology for the user's Windows machine (see §6).

## 2. The methodology (the thing the dashboard teaches)

```
market_TP(t) = max( mean_panel[ CD_offer(t) ], FSB_issuance(t) ) − SOFR(t)
FTP(t)       = SOFR(t) + approved_TP(t)          # production cost-of-funds curve
```

- **Panel = 7 issuers** (fixed, real): Wells Fargo, BNY, Morgan Stanley, Bank of
  America, Raymond James, RBC, Citi. Simple average of available quotes per term.
- **Floor** at FSB's own executed brokered-CD issuances (`max`, lifts never
  lowers). Many weeks have none → floor not in play.
- **Subtract same-term SOFR** (Term SOFR 1–6M; OIS swaps 1Y+). Residual = term
  liquidity + unsecured credit premium, in bp. **FHLB** advances are a *secured
  reference only*, not in the calc.
- **Term grid (8 nodes):** 1M, 3M, 6M, 1Y, 2Y, 3Y, 4Y, 5Y. Interpolated to a
  **monthly 1–60M grid**, piecewise-linear, flat outside node range (matches the
  FTP engine's Interpolation Methodology doc).
- **Governance (this is the important part, and it changed late):** the
  **governing comparison is production vs the rolling 13-week trend of market_TP
  *including the current week***. A tenor is **Discuss** (committee) only when
  that *trend* leaves the **±20bp zone of indifference**; a single-week print
  outside the zone is **Watch**, not an alarm. This is deliberate — the 13-week
  smoothing is the approved way to minimize volatility/reactivity. Wording is
  "zone of indifference" (from the COF memo), not "indifference range".

## 3. Real data currently embedded (week of 2026-07-06)

Defaults in `defaultState()` are the **actual** 7/6 Weekly Workbook values:

- **SOFR:** `[3.66688, 3.72994, 3.83803, 3.974, 3.9667, 3.92555, 3.90588, 3.908]`
- **Approved TP (bp):** `[10, 15, 20, 30, 50, 55, 60, 60]` (short end cut 5bp at
  1M/3M/6M from the original 15/20/25 Rate Summary "FCS" values)
- **FHLB:** `[3.84, 3.94, 4.07, 4.22, 4.24, 4.27, 4.31, 4.34]` (FHLBNY same-day)
- **7 issuer offers** — see `defaultState()`; Wells has no 1M quote.
- **FSB issuances:** none this week (all null).
- **History:** real weekly market TP since 2026-01-12 (Term Premium-SOFR sheet).

**Parity check (dashboard AND Python must both produce this):** 1M premium
**41.6bp**, 13-wk trend vs production **+24.9bp**, latest vs production
**+31.6bp**, status **Discuss** (the short-end schedule cut pushed the 1M trend
gap past ±20bp). LS key is now `ftp-term-premium-v4` so the new schedule loads
over any stored v3 state.

## 4. index.html architecture

- **5 tabs** (SPA, hash-routed): `This Week` (answer card with two-fold hero:
  trend-vs-production then latest-vs-production; premium-vs-schedule bar chart;
  full monthly curve; term-structure trend chart), `How It Works` (5-step
  workflow stepper with a data-provenance/timing card), `Curve Construction`
  (4 Excel importers + editable tables + history + results export), `Why &
  Pressure-Test` (rationale cards + known-gaps list + decision log),
  `Glossary & Sources`.
- **State:** global `S`, persisted to `localStorage["ftp-term-premium-v3"]`.
  `defaultState()` holds the seed data. `load()` has a schema guard that resets
  if the term grid length changed.
- **`compute()`** returns all derived series: `avg`, `floored`, `mtp`,
  `trailInc` (13-wk trend incl. this week), `dApp` (latest vs approved),
  `dTrendApp` (trend vs approved — drives status), `status`, and `M` (monthly
  interpolated curves incl. `M.prod` = production FTP line).
- **Charts (hand-rolled SVG, no libs):** `fullCurveChart` (monthly, all curves +
  premium wash + production line), `premiumChart` (bars vs zone band),
  `tsChart` (term-structure: this week / 13-wk trend / production + prior-week
  spaghetti), `curveChart` (minis in How It Works), `trendChart`.
- **Colors (from the `dataviz` skill's validated palette):** s1 blue = floored
  CD (applied); s1-lt = panel avg; **s8 orange = Production FTP**; **s5 violet =
  FSB issuance diamonds**; s2 aqua = FHLB; muted gray = SOFR. Orange is reserved
  for production; do not reuse it. Light + dark themes both defined via tokens.
- **Excel I/O:** four importers (`cd`, `fsb`, `sofr`, `fhlb`), each keyed on a
  **Date** column. Accepts .xlsx (SheetJS), .csv, or paste-from-Excel. Parser is
  cross-platform hardened: UTF-8 BOM, CRLF/CR, semicolon-delimited, decimal-comma,
  Excel date serials, `M/D/YYYY` + ISO, percent strings + percent-formatted cells.
  Exports: per-dataset .xlsx + a publishable results workbook.

## 5. Design skills to reload in a new session

The user explicitly wanted three of their **claude.ai** skills applied — Minto,
Few, IBCS. Find them via `ListSkills` (load the tool through `ToolSearch`):
`pyramid-principle`, `data-visualization`, `ibcs-reporting`. **Note:** these are
claude.ai skills and are NOT invokable via the local `Skill` tool (that errors
"Unknown skill"); apply their principles directly. For the dashboard visuals,
DO invoke the bundled `Skill` `dataviz` (chart rules + palette + validator) and
`artifact-design` before writing chart/HTML code.

## 6. Workstation package (`term-premium/workstation/`)

Python mirror, openpyxl-only, runs identically on Windows/Mac/Linux.

- `term_premium.py` — parsing + `compute()` + results-workbook writer. Mirrors
  the dashboard's math exactly.
- `run_weekly.py` — CLI: `python run_weekly.py --cd ... --sofr ... --fhlb ...
  [--fsb ...] [--commit]`. Prints committee summary, writes `results_<date>.xlsx`.
- `history.csv` — real weekly history (trend source). `inputs/` — the 7/6
  workbooks for the parity check. `templates/` — blank 7/13 upload workbooks.
  `dashboard/index.html` — offline copy of the dashboard. `README.md` — Windows
  setup. `requirements.txt` — openpyxl.
- Verified: `run_weekly.py` on `inputs/` reproduces §3 exactly.

## 7. How to verify changes

- **Dashboard (headless render + screenshot):** work in the scratchpad dir.
  `npm install playwright-core` (once), launch Chromium with
  `executablePath:'/opt/pw-browsers/chromium'`, wrap the file as
  `<!doctype html><html><head><meta charset="utf-8"></head><body>` + file +
  `</body></html>`, load `file://…`, screenshot, and assert `pageerror`/console
  are clean. This is how every prior change was checked — do it before shipping.
- **Palette:** the `dataviz` skill ships `scripts/validate_palette.js`; run it on
  any new categorical hues (never eyeball CVD safety).
- **Python:** run `run_weekly.py` against `workstation/inputs/` and confirm the
  §3 parity numbers.
- **To read the two source docs again:** they are user uploads (Google Drive /
  session uploads), not in the repo — `COF Curve Construction.docx` and
  `WeeklyWorkbook_070626.xlsm`. Re-request or re-fetch if needed. The workbook's
  sheets: `Rate Summary`, `Rate PDF`, `Collateral`, `FHLB RATES`,
  `Brokered CD Rates`, `Term Premium-SOFR` (history), `BANK CD QUOTES`.

## 8. Open items / caveats to keep in mind

1. **6M average discrepancy:** the workbook's "CURRENT" cell shows 4.100 at 6M,
   but the true mean of its own 7 quotes is 4.093 → dashboard reads 25.5bp vs
   workbook 26.2bp at 6M. Worth checking the workbook's 6M formula.
2. **Two advised schedules exist:** Rate Summary "FCS" (15/20/25 at 1M/3M/6M,
   which the dashboard uses) vs Rate PDF engine (10/15/20). Confirm which is the
   committee's comparator; the approved row is editable on Curve Construction.
3. **1M trend gap = +19.9bp**, a hair *inside* ±20. User once referenced ~21bp —
   a 12-week window, or 13 weeks *excluding* the current print (+18.9), gives a
   different number. Lookback is adjustable in the UI.
4. **Observation-date drift:** panel struck Monday, FSB prints mid-week, SOFR
   moves between. Documented as a known limitation (date chips + provenance
   card). Possible future mitigation: subtract SOFR *as of the print date* when
   testing whether the floor binds.
5. Other pressure-test items already written into the Why tab: quote conventions
   (APY vs BEY), callable vs bullet paper, executable vs posted, thin long end,
   panel survivorship, floor asymmetry, weekly-vs-monthly cadence, the separate
   CD contingent-liquidity credit (FTP − 10bp).

## 9. Commit conventions for this session

- Branch `claude/term-premium-cd-dashboard-2zq56f`, `git push -u origin` it.
- Commit trailers used throughout:
  `Co-Authored-By: Claude <noreply@anthropic.com>` and a `Claude-Session:` line.
- Do **not** put the model id anywhere in commits/PRs/code — chat only.
- No PR has been opened; the user has not asked for one. Ask before creating.

## 10. Change history (newest last)

1. Initial single-page dashboard (answer-first banner, tiles, curve, premium,
   trend small-multiples).
2. Restructured into 5 tabs; four Excel importers + SheetJS; results workbook;
   FSB recolored; date chips + drift warning.
3. Loaded real 7/6 Weekly Workbook data; term grid → 1M…5Y; added the orange
   **Production FTP** line; How It Works became a 1→2→3→4→5 workflow; issuer
   panel = the real 7 names.
4. Two-fold takeaway keyed to the **13-week trend vs production** (Discuss only
   on trend breach; single-week = Watch); replaced 8 mini-charts with one
   **term-structure** chart; cross-platform import parsing.
5. This Week now leads with the premium-vs-schedule chart (tiles removed, text
   kept as caption); added the Python **workstation** package.
6. Hid the Why & Pressure-Test tab (section still in DOM, unreachable — keeps
   `renderDecisions()` alive); cut production TP 5bp at 1M/3M/6M
   (→10/15/20); rewrote the How It Works intro around the COF identity and
   moved the Data provenance card to the foot of that tab; widened the reading
   column (`.wrap` 1320px, prose 100–108ch).

**Next thing the user may ask:** they said "we are almost done." Likely
follow-ups are polish, an ALMC slide/export, or wiring the workstation into
their real weekly cadence. Nothing is broken or half-finished as of change 5.
