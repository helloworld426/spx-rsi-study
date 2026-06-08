"""Price data loading with a local CSV cache."""
from __future__ import annotations

import os

import pandas as pd

from config import StudyConfig


def load_prices(cfg: StudyConfig, refresh: bool = False) -> pd.DataFrame:
    """Return a DataFrame indexed by date with at least a 'Close' column.

    Downloads daily OHLC from yfinance and caches it to ``cfg.cache_csv``. Pass
    ``refresh=True`` to force a re-download (e.g. to pick up new bars).
    """
    if not refresh and os.path.exists(cfg.cache_csv):
        df = pd.read_csv(cfg.cache_csv, index_col=0, parse_dates=True)
        if len(df) > 0:
            return df

    import yfinance as yf

    # Download the full available history; the dataset window (dataset_start /
    # dataset_end) is applied downstream in the backtest so the cache can be
    # reused across studies with different windows.
    raw = yf.download(
        cfg.ticker,
        start=cfg.download_start,
        end=None,
        auto_adjust=False,
        progress=False,
    )
    if raw.empty:
        raise RuntimeError(f"No data returned for {cfg.ticker}")

    # yfinance returns a MultiIndex column frame for a single ticker; flatten it.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw[["Open", "High", "Low", "Close"]].copy()
    df.index.name = "Date"
    df.to_csv(cfg.cache_csv)
    return df
