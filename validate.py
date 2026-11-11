"""Validate the engine output against the published results table.

Run:  .venv/Scripts/python.exe validate.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import dataclasses

from backtest import run_backtest
from config import DEFAULT_CONFIG
from data import load_prices

# The reference table is the 2026-06-05 snapshot of the live study, so validation
# always runs against that pinned end date regardless of the deploy default.
SNAPSHOT_END = "2026-06-05"

HORIZONS = ["1W", "2W", "1M", "2M", "3M", "6M", "9M", "12M"]

# Published aggregate stats (percent), scraped from the study's Study Summary
# and Results Table footer.
REF_SIGNAL_AVG = [0.9, 0.5, 0.6, 1.1, 3.0, 7.4, 9.2, 13.7]
REF_SIGNAL_MED = [1.1, 0.9, 1.7, 2.2, 5.8, 7.7, 9.3, 13.8]
REF_SIGNAL_HIT = [71.9, 62.5, 68.8, 68.8, 71.9, 78.1, 75.0, 87.1]
REF_SIGNAL_Z = [1.78, 0.31, -0.17, -0.33, 0.60, 1.51, 0.98, 1.57]
REF_BASE_AVG = [0.2, 0.4, 0.7, 1.5, 2.2, 4.5, 6.8, 9.2]
REF_BASE_MED = [0.3, 0.6, 1.1, 1.9, 2.7, 5.1, 7.7, 10.4]
REF_BASE_HIT = [56.8, 58.9, 61.4, 64.0, 66.2, 70.1, 72.7, 73.8]
REF_SIGNAL_MAXDD_AVG = -13.1
REF_BASE_MAXDD_AVG = -13.7


def _fmt(x, ref, tol, unit=""):
    ok = (not np.isnan(x)) and abs(x - ref) <= tol
    mark = "OK " if ok else "XX "
    return f"{mark}got {x:+6.2f}{unit}  ref {ref:+6.2f}{unit}  d={x-ref:+.2f}", ok


def main() -> None:
    cfg = dataclasses.replace(DEFAULT_CONFIG, dataset_end=SNAPSHOT_END)
    prices = load_prices(cfg)
    res = run_backtest(cfg, prices)

    ref = pd.read_csv("reference_table.csv", parse_dates=["signal_date"]).set_index(
        "signal_date"
    )

    fails = 0

    # ---- 1. signal set matches (dates + price) ----
    got_dates = list(res.signals.index)
    ref_dates = list(ref.index)
    print(f"Signals: got {len(got_dates)}, ref {len(ref_dates)}")
    if got_dates != ref_dates:
        fails += 1
        only_got = set(got_dates) - set(ref_dates)
        only_ref = set(ref_dates) - set(got_dates)
        print("  XX date mismatch")
        if only_got:
            print("    extra:", [str(d.date()) for d in sorted(only_got)])
        if only_ref:
            print("    missing:", [str(d.date()) for d in sorted(only_ref)])
    else:
        print("  OK all 33 signal dates match")

    # ---- 2. per-row forward returns ----
    print("\nPer-signal forward returns (tolerance 0.15pp):")
    row_cells = 0
    row_bad = 0
    for dt in ref.index:
        if dt not in res.signals.index:
            continue
        for col in HORIZONS:
            rv = ref.loc[dt, col]
            if pd.isna(rv):
                continue
            gv = res.signals.loc[dt, col] * 100.0
            row_cells += 1
            if abs(gv - rv) > 0.15:
                row_bad += 1
                print(f"  XX {dt.date()} {col}: got {gv:+.1f} ref {rv:+.1f}")
        # maxdd
        rmd = ref.loc[dt, "12M_maxdd"]
        if not pd.isna(rmd):
            gmd = res.signals.loc[dt, "maxdd"] * 100.0
            row_cells += 1
            if abs(gmd - rmd) > 0.2:
                row_bad += 1
                print(f"  XX {dt.date()} MAXDD: got {gmd:+.1f} ref {rmd:+.1f}")
    print(f"  {row_cells - row_bad}/{row_cells} cells within tolerance")
    fails += row_bad > 0

    # ---- 3. aggregate stats ----
    print("\nAggregate stats:")
    for name, getter, refs, tol, unit in [
        ("Signal avg", lambda h: res.signal_stats[h]["avg"] * 100, REF_SIGNAL_AVG, 0.15, "%"),
        ("Signal med", lambda h: res.signal_stats[h]["median"] * 100, REF_SIGNAL_MED, 0.15, "%"),
        ("Signal hit", lambda h: res.signal_stats[h]["hit"] * 100, REF_SIGNAL_HIT, 0.2, "%"),
        ("Signal Z  ", lambda h: res.zscores[h], REF_SIGNAL_Z, 0.06, ""),
        ("Base avg  ", lambda h: res.baseline_stats[h]["avg"] * 100, REF_BASE_AVG, 0.15, "%"),
        ("Base med  ", lambda h: res.baseline_stats[h]["median"] * 100, REF_BASE_MED, 0.15, "%"),
        ("Base hit  ", lambda h: res.baseline_stats[h]["hit"] * 100, REF_BASE_HIT, 0.2, "%"),
    ]:
        line_ok = True
        cells = []
        for i, h in enumerate(HORIZONS):
            v = getter(h)
            ok = (not np.isnan(v)) and abs(v - refs[i]) <= tol
            line_ok &= ok
            cells.append(f"{h}:{'OK' if ok else 'XX'}({v - refs[i]:+.2f})")
        print(f"  {'OK' if line_ok else 'XX'} {name}: " + " ".join(cells))
        fails += not line_ok

    # maxdd aggregates
    smd, ok1 = _fmt(res.signal_stats["_maxdd"]["avg"] * 100, REF_SIGNAL_MAXDD_AVG, 0.15, "%")
    bmd, ok2 = _fmt(res.baseline_stats["_maxdd"]["avg"] * 100, REF_BASE_MAXDD_AVG, 0.2, "%")
    print(f"  Signal maxdd avg: {smd}")
    print(f"  Base   maxdd avg: {bmd}")
    fails += (not ok1) + (not ok2)

    print("\n" + ("ALL CHECKS PASSED" if fails == 0 else f"{fails} CHECK GROUP(S) FAILED"))


if __name__ == "__main__":
    main()
