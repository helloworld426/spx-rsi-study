"""Study configuration — parameterized so the engine can run any RSI-style study,
not just the SPX 70->50 one this project replicates.

The defaults reproduce the dailychartbook study:
  "SPX RSI Goes From Overbought to < 50 in 3 Days"
  https://studies.dailychartbook.com/spx-rsi-above-70-to-below-50-in-3d/
"""
from __future__ import annotations

from dataclasses import dataclass, field


# Forward-return windows, in trading days. Order is preserved everywhere
# (cards, charts, table columns).
DEFAULT_HORIZONS: dict[str, int] = {
    "1W": 5,
    "2W": 10,
    "1M": 21,
    "2M": 42,
    "3M": 63,
    "6M": 126,
    "9M": 189,
    "12M": 252,
}


@dataclass
class StudyConfig:
    # --- identity / presentation ---
    title: str = "SPX RSI Goes From Overbought to < 50 in 3 Days"
    asset: str = "SPX"
    ticker: str = "^GSPC"          # yfinance symbol
    trigger_label: str = "RSI"

    # --- data window ---
    # The published study trims the dataset to start at 1944-06-30. We download
    # more history (for RSI warm-up) but only treat days >= dataset_start as the
    # dataset for signals + baseline statistics.
    download_start: str = "1927-01-01"
    dataset_start: str = "1944-06-30"
    # None => run against the latest available bar (used for the live deployed
    # dashboard). validate.py pins this to the original 2026-06-05 snapshot so
    # the "matches the published study" proof stays reproducible forever.
    dataset_end: str | None = None

    # --- indicator ---
    rsi_period: int = 14

    # --- signal definition ---
    # Trigger fires on day t when:
    #   RSI[t] < cross_below            (crossed under, having been >= the prior day)
    #   RSI[t-1] >= cross_below
    #   max(RSI over the prior `lookback` days, i.e. t-1..t-lookback) > overbought
    overbought: float = 70.0
    cross_below: float = 50.0
    lookback: int = 3

    # --- forward returns ---
    horizons: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_HORIZONS))
    maxdd_horizon: str = "12M"       # which horizon defines the "max drawdown" column

    # --- output ---
    out_html: str = "dashboard.html"
    cache_csv: str = "spx_data.csv"


DEFAULT_CONFIG = StudyConfig()
