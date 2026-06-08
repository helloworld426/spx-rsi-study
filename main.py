"""Run the SPX RSI study and write the dashboard HTML.

Usage:
    .venv/Scripts/python.exe main.py            # build dashboard.html
    .venv/Scripts/python.exe main.py --refresh  # re-download price data first
    .venv/Scripts/python.exe main.py --open      # build and open in browser
"""
from __future__ import annotations

import argparse
import os
import webbrowser

from backtest import run_backtest
from config import DEFAULT_CONFIG
from dashboard import build_html
from data import load_prices


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download price data")
    ap.add_argument("--open", action="store_true", help="open the dashboard when done")
    args = ap.parse_args()

    cfg = DEFAULT_CONFIG
    print(f"Loading {cfg.ticker} prices ...")
    prices = load_prices(cfg, refresh=args.refresh)
    print(f"  {len(prices)} bars, {prices.index[0].date()} -> {prices.index[-1].date()}")

    print("Running backtest ...")
    res = run_backtest(cfg, prices)
    print(f"  {len(res.signals)} signals; "
          f"12M avg {res.signal_stats['12M']['avg']*100:+.1f}% "
          f"vs baseline {res.baseline_stats['12M']['avg']*100:+.1f}%")

    print("Building dashboard ...")
    html = build_html(res)
    with open(cfg.out_html, "w", encoding="utf-8") as f:
        f.write(html)
    path = os.path.abspath(cfg.out_html)
    print(f"  wrote {path} ({len(html)/1024:.0f} KB)")

    if args.open:
        webbrowser.open("file://" + path.replace("\\", "/"))


if __name__ == "__main__":
    main()
