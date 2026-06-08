# SPX RSI 70→50 Study — backtest + dashboard replica

A from-scratch replication of the Daily Chartbook study
**"SPX RSI Goes From Overbought to < 50 in 3 Days"**
(<https://studies.dailychartbook.com/spx-rsi-above-70-to-below-50-in-3d/>).

It reproduces both the **backtest** (signal detection, forward returns, baseline
statistics) and the **dashboard** (a self-contained static HTML file that mirrors
the original layout). The engine is parameterized via `config.py`, so the same
code can run other RSI cross studies.

## The study

* **Asset:** SPX (`^GSPC`), daily closes, dataset window 1944-06-30 → 2026-06-05.
* **Indicator:** Wilder 14-day RSI.
* **Trigger:** on day *t*, RSI closes **< 50** having closed **≥ 50** the prior day,
  **and** RSI was **> 70** on at least one of the prior 3 trading days (T-1/T-2/T-3).
* **Forward returns:** 1W, 2W, 1M, 2M, 3M, 6M, 9M, 12M (trading-day offsets
  5/10/21/42/63/126/189/252) plus a 12-month max-drawdown column.
* **Baseline:** the same windows computed over *every* day in the dataset
  ("all-dataset"), used for the comparison line, hit-rate baseline, and z-scores.
* **Z-score:** `(signal_mean − baseline_mean) / (baseline_std / √n)`.

This produces **33 signals** that match the published table exactly.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
.venv\Scripts\python.exe main.py            # build dashboard.html
.venv\Scripts\python.exe main.py --open     # build and open in browser
.venv\Scripts\python.exe main.py --refresh  # re-download price data first
```

`dashboard.html` is fully self-contained (Plotly.js is inlined) — double-click to
open it offline.

## Validate against the source

```powershell
.venv\Scripts\python.exe validate.py
```

Checks the computed output against `reference_table.csv` (the 33 rows + aggregate
stats scraped from the live study). All signal dates, the 287 per-row forward
returns, and every aggregate (avg / median / hit rate / z-score / baseline /
max drawdown) match within tolerance — `ALL CHECKS PASSED`.

## Files

| File | Purpose |
|------|---------|
| `config.py` | `StudyConfig` — all study parameters (ticker, RSI period, thresholds, horizons, dates). |
| `data.py` | Download daily OHLC from yfinance, cached to `spx_data.csv`. |
| `indicators.py` | Wilder RSI. |
| `backtest.py` | Signal detection, forward returns, max drawdown, baseline stats, z-scores. |
| `dashboard.py` | Renders the self-contained HTML dashboard with Plotly. |
| `main.py` | Entry point: load → backtest → build HTML. |
| `validate.py` | Compares engine output to `reference_table.csv`. |
| `reference_table.csv` | Ground-truth results scraped from the live study. |

## Dashboard sections

Header chips · title · summary cards (signal count, avg max drawdown, trigger
criteria, AI summary) · forward-return & hit-rate cards (Avg/Median toggle) ·
signal map · forward-returns bar · hit-rates bar · signal-performance paths
(Median/Avg toggle) · return distribution box plots · study-summary table ·
full results table with conditional coloring.

## Notes

* `dataset_end` is pinned to the study's snapshot date (2026-06-05) so the
  replication is deterministic regardless of when the data is pulled. Set it to
  `None` in `config.py` to run against the latest available bar.
* Educational reproduction. Past performance is not indicative of future results;
  backtested results are hypothetical and exclude costs, slippage, and taxes.
