"""
Weekly term-premium run - command-line front end.

Typical Monday run (Windows PowerShell or cmd, from this folder):

    python run_weekly.py --cd inputs\Brokered_CDs.xlsx --sofr inputs\SOFR.xlsx ^
                         --fhlb inputs\FHLB.xlsx --fsb inputs\FSB_Issuances.xlsx

Outputs results_<date>.xlsx and prints the committee summary. Add --commit to
append this week's premiums to history.csv (the trend source for next week).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import term_premium as tp


def main() -> int:
    ap = argparse.ArgumentParser(description="Weekly brokered-CD term premium run")
    ap.add_argument("--cd", required=True, help="Brokered CD panel workbook (.xlsx/.csv)")
    ap.add_argument("--sofr", required=True, help="SOFR workbook (.xlsx/.csv)")
    ap.add_argument("--fhlb", required=True, help="FHLB advance workbook (.xlsx/.csv)")
    ap.add_argument("--fsb", default=None, help="FSB issuance workbook; omit if no prints")
    ap.add_argument("--history", default="history.csv", help="Weekly market-TP history CSV")
    ap.add_argument("--approved", default=",".join(map(str, tp.DEFAULT_APPROVED)),
                    help="Approved TP schedule in bp, 8 comma-separated values (1M..5Y)")
    ap.add_argument("--band", type=float, default=tp.DEFAULT_BAND_BP, help="Zone of indifference, bp")
    ap.add_argument("--lookback", type=int, default=tp.DEFAULT_LOOKBACK, help="Trend lookback, weeks")
    ap.add_argument("--out", default=None, help="Results workbook path (default results_<date>.xlsx)")
    ap.add_argument("--commit", action="store_true", help="Append this week's premiums to the history CSV")
    args = ap.parse_args()

    approved = [float(x) for x in args.approved.split(",")]
    if len(approved) != tp.NT:
        ap.error(f"--approved needs {tp.NT} values (1M,3M,6M,1Y,2Y,3Y,4Y,5Y)")

    cd_date, panel = tp.load_cd(Path(args.cd))
    sofr_date, sofr = tp.load_wide(Path(args.sofr))
    fhlb_date, fhlb = tp.load_wide(Path(args.fhlb))
    fsb_date, fsb = tp.load_fsb(Path(args.fsb) if args.fsb else None)
    history = tp.load_history(Path(args.history))
    C = tp.compute(panel, fsb, sofr, approved, history, args.band, args.lookback)

    out = Path(args.out) if args.out else Path(f"results_{cd_date.isoformat()}.xlsx")
    tp.write_results(out, C, sofr, fhlb, fsb, approved, cd_date,
                     {"cd": cd_date, "fsb": fsb_date, "sofr": sofr_date, "fhlb": fhlb_date})

    print(f"\nWeek of {cd_date}  ({len(panel)} issuers; zone +/-{args.band:g}bp; "
          f"{args.lookback}-week trend incl. this week)")
    if fsb_date and fsb_date != cd_date:
        print(f"  NOTE: FSB print dated {fsb_date} vs panel {cd_date} - observation-date drift.")
    hdr = f"  {'Term':<5}{'TP bp':>8}{'Trend':>8}{'Prod':>7}{'T-P':>8}{'L-P':>8}   Status"
    print(hdr + "\n  " + "-" * (len(hdr) - 2))
    fmt = lambda v: "-" if v is None else f"{v:g}"
    sfm = lambda v: "-" if v is None else f"{v:+g}"
    for i in range(tp.NT):
        print(f"  {tp.TERM_LABELS[i]:<5}{fmt(C['mtp'][i]):>8}{fmt(C['trail_inc'][i]):>8}"
              f"{fmt(approved[i]):>7}{sfm(C['d_trend'][i]):>8}{sfm(C['d_app'][i]):>8}   {C['status'][i]}")
    acts = [tp.TERM_LABELS[i] for i in range(tp.NT) if C["status"][i] == "Discuss"]
    watches = [tp.TERM_LABELS[i] for i in range(tp.NT) if C["status"][i] == "Watch"]
    if acts:
        print(f"\n  RECOMMEND COMMITTEE REVIEW: {', '.join(acts)} - trend outside the zone of indifference.")
    elif watches:
        print(f"\n  HOLD - all trends inside the zone; on watch (single-week breach): {', '.join(watches)}.")
    else:
        print("\n  HOLD - all trends and weekly prints inside the zone of indifference.")
    print(f"  Results workbook: {out}")

    if args.commit:
        history = [h for h in history if h[0] != cd_date] + [(cd_date, C["mtp"])]
        history.sort(key=lambda r: r[0])
        tp.save_history(Path(args.history), history)
        print(f"  Committed week {cd_date} to {args.history}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
