# Term Premium Monitor — workstation package

Weekly brokered-CD term premium process (Flagstar Treasury / ALM), packaged to
run locally on **Windows** (works identically on macOS/Linux). Two independent
ways to run the same methodology:

1. **`dashboard/index.html`** — the interactive dashboard. Fully self-contained
   (charts, Excel reader, everything inline). Double-click to open in Edge or
   Chrome; no install, no network. Data entered there persists per browser via
   localStorage; use its Export/Import buttons to move datasets.
2. **`run_weekly.py`** — the same calculation in Python, for scripted runs and
   parallel verification against the dashboard.

Methodology (mirrors the COF Curve Construction memo):

```
market_TP(t) = max( mean_panel[ CD_offer(t) ], FSB_issuance(t) ) − SOFR(t)
```

Governing comparison: **production (approved TP schedule) vs the rolling
13-week trend of market_TP including the current week**. "Discuss" only when
that trend leaves the ±20bp zone of indifference; a single-week breach alone
is "Watch". FHLB is a secured reference only.

## Python setup (Windows, one time)

Requires Python 3.10+ ([python.org](https://www.python.org/downloads/) — check
"Add python.exe to PATH" during install). Then, in this folder:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

(macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`)

## Weekly run

Fill the four workbooks in `templates\` (Data sheet; each has the 7/6 actuals
on an Example sheet), drop them wherever convenient, then:

```bat
.venv\Scripts\activate
python run_weekly.py --cd inputs\Brokered_CDs_2026-07-06.xlsx --sofr inputs\SOFR_2026-07-06.xlsx --fhlb inputs\FHLB_2026-07-06.xlsx
```

* Add `--fsb inputs\FSB_Issuances.xlsx` when there were issuances that week
  (omit otherwise — the floor is simply skipped).
* Add `--commit` once the week is final to append it to `history.csv`
  (the trend source for the following week).
* `--band`, `--lookback`, `--approved "15,20,25,30,50,55,60,60"` and `--out`
  override defaults.

Output: `results_<date>.xlsx` (Node summary · Monthly curve 1–60M · Meta) plus
a console committee summary. `inputs\` ships with the actual 2026-07-06 data
so you can verify the install reproduces the dashboard: 1M TP 41.6bp, trend
vs production +19.9bp, latest vs production +26.6bp, status Watch.

## Files

| Path | What it is |
|---|---|
| `dashboard/index.html` | Self-contained interactive dashboard |
| `term_premium.py` | Calculation library (parsing, compute, results workbook) |
| `run_weekly.py` | Command-line weekly run |
| `history.csv` | Weekly market-TP history (bp) — real data since 2026-01-12 |
| `inputs/` | Actual 2026-07-06 input workbooks (parity check) |
| `templates/` | Blank 2026-07-13 upload workbooks with instructions |
| `requirements.txt` | Python dependencies (openpyxl only) |

Input format (all four files): a `Data` sheet with a **Date** column; brokered
CDs add an **Issuer** column plus term columns `1M 3M 6M 1Y 2Y 3Y 4Y 5Y`;
SOFR/FHLB are one row per date with the same term columns; FSB issuances are
long format `Date | Term | Rate`, one row per print. Dates as Excel dates,
`M/D/YYYY`, or `YYYY-MM-DD`; rates in percent (4.20), percent strings, or
percent-formatted cells. UTF-8 BOM, CRLF, semicolon-CSV and decimal-comma
variants all parse.
