"""Backtest engine: signal detection, forward returns, and baseline statistics.

Everything here is driven by a StudyConfig, so the same code reproduces the
SPX 70->50 study or any other RSI cross study.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import StudyConfig
from indicators import wilder_rsi


@dataclass
class BacktestResult:
    cfg: StudyConfig
    prices: pd.DataFrame          # full history, with 'Close' and 'RSI'
    dataset: pd.DataFrame         # prices restricted to >= dataset_start
    signals: pd.DataFrame         # index=signal date; cols: price, horizons, maxdd
    signal_stats: dict            # horizon -> {avg, median, hit, n}; '_maxdd' too
    baseline_stats: dict          # horizon -> {avg, median, hit, std, n}; '_maxdd'
    zscores: dict                 # horizon -> z
    forward_paths: dict           # signal date (Timestamp) -> np.ndarray cum returns

    @property
    def horizons(self) -> dict[str, int]:
        return self.cfg.horizons


def _forward_return(prices: np.ndarray, i: int, h: int) -> float:
    j = i + h
    if j >= len(prices):
        return np.nan
    return prices[j] / prices[i] - 1.0


def _max_drawdown(prices: np.ndarray, i: int, n: int) -> float:
    """Peak-to-trough max drawdown over the forward window prices[i .. i+n].

    The running peak is seeded at the entry price, so a signal that only ever
    rises has a drawdown of 0. Unlike the forward-return columns, this uses
    whatever forward data is available: a signal whose full n-day window hasn't
    elapsed yet still gets a drawdown over the partial path (matching the source
    study, which reports a max drawdown for the most recent signal even when its
    12M return is still blank). Returns NaN only when there is no forward data.
    """
    if i + 1 >= len(prices):
        return np.nan
    j = min(i + n, len(prices) - 1)
    window = prices[i : j + 1]
    running_peak = np.maximum.accumulate(window)
    dd = window / running_peak - 1.0
    return float(dd.min())


def _forward_path(prices: np.ndarray, i: int, n: int) -> np.ndarray:
    """Cumulative return path for days 0..n after entry (length n+1, day0 = 0)."""
    j = min(i + n, len(prices) - 1)
    window = prices[i : j + 1]
    return window / prices[i] - 1.0


def run_backtest(cfg: StudyConfig, prices: pd.DataFrame) -> BacktestResult:
    prices = prices.copy()
    prices["RSI"] = wilder_rsi(prices["Close"], cfg.rsi_period)

    # Dataset window (signals + baseline both live here).
    mask = prices.index >= pd.Timestamp(cfg.dataset_start)
    if cfg.dataset_end is not None:
        mask &= prices.index <= pd.Timestamp(cfg.dataset_end)
    dataset = prices.loc[mask]

    close = dataset["Close"].to_numpy(dtype=float)
    rsi = dataset["RSI"].to_numpy(dtype=float)
    dates = dataset.index

    maxdd_days = cfg.horizons[cfg.maxdd_horizon]

    # ---- signal detection ----
    signal_rows = []
    for t in range(cfg.lookback, len(rsi)):
        if np.isnan(rsi[t]) or np.isnan(rsi[t - 1]):
            continue
        crossed_down = rsi[t] < cfg.cross_below and rsi[t - 1] >= cfg.cross_below
        if not crossed_down:
            continue
        prior = rsi[t - cfg.lookback : t]          # T-lookback .. T-1
        if np.nanmax(prior) <= cfg.overbought:
            continue

        row = {"signal_date": dates[t], "spx_price": close[t]}
        for label, h in cfg.horizons.items():
            row[label] = _forward_return(close, t, h)
        row["maxdd"] = _max_drawdown(close, t, maxdd_days)
        signal_rows.append(row)
        # forward path stored separately (keyed by date) below
        row["_idx"] = t

    signals = pd.DataFrame(signal_rows).set_index("signal_date")
    forward_paths = {
        dt: _forward_path(close, int(idx), maxdd_days)
        for dt, idx in zip(signals.index, signals["_idx"])
    }
    signals = signals.drop(columns="_idx")

    # ---- signal aggregate stats ----
    signal_stats: dict = {}
    for label in cfg.horizons:
        col = signals[label].to_numpy(dtype=float)
        col = col[~np.isnan(col)]
        signal_stats[label] = {
            "avg": float(np.mean(col)) if len(col) else np.nan,
            "median": float(np.median(col)) if len(col) else np.nan,
            "hit": float(np.mean(col > 0)) if len(col) else np.nan,
            "n": int(len(col)),
        }
    dd = signals["maxdd"].to_numpy(dtype=float)
    dd = dd[~np.isnan(dd)]
    signal_stats["_maxdd"] = {
        "avg": float(np.mean(dd)) if len(dd) else np.nan,
        "median": float(np.median(dd)) if len(dd) else np.nan,
        "n": int(len(dd)),
    }

    # ---- baseline (all-dataset) stats ----
    baseline_stats: dict = {}
    for label, h in cfg.horizons.items():
        rets = close[h:] / close[:-h] - 1.0 if h < len(close) else np.array([])
        rets = rets[~np.isnan(rets)]
        baseline_stats[label] = {
            "avg": float(np.mean(rets)) if len(rets) else np.nan,
            "median": float(np.median(rets)) if len(rets) else np.nan,
            "hit": float(np.mean(rets > 0)) if len(rets) else np.nan,
            "std": float(np.std(rets, ddof=1)) if len(rets) > 1 else np.nan,
            "n": int(len(rets)),
        }
    base_dd = np.array(
        [_max_drawdown(close, i, maxdd_days) for i in range(len(close))], dtype=float
    )
    base_dd = base_dd[~np.isnan(base_dd)]
    baseline_stats["_maxdd"] = {
        "avg": float(np.mean(base_dd)) if len(base_dd) else np.nan,
        "median": float(np.median(base_dd)) if len(base_dd) else np.nan,
        "n": int(len(base_dd)),
    }

    # ---- z-scores: how far the signal mean sits from the baseline mean,
    # in standard errors of the baseline distribution. ----
    zscores: dict = {}
    for label in cfg.horizons:
        s = signal_stats[label]
        b = baseline_stats[label]
        n = s["n"]
        if n > 0 and not np.isnan(b["std"]) and b["std"] > 0:
            se = b["std"] / np.sqrt(n)
            zscores[label] = (s["avg"] - b["avg"]) / se
        else:
            zscores[label] = np.nan

    return BacktestResult(
        cfg=cfg,
        prices=prices,
        dataset=dataset,
        signals=signals,
        signal_stats=signal_stats,
        baseline_stats=baseline_stats,
        zscores=zscores,
        forward_paths=forward_paths,
    )
