"""Technical indicators."""
from __future__ import annotations

import pandas as pd


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Classic Wilder RSI.

    Uses Wilder's smoothing (an EMA with alpha = 1/period, seeded so the first
    valid value appears at index `period`). This matches the RSI definition used
    by the dailychartbook study and by most charting platforms.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 (only gains), rs is inf -> rsi 100. pandas handles inf
    # in the division; make it explicit for the all-gains edge case.
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi.name = "RSI"
    return rsi
