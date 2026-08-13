"""Station 2 - your features: return features and text assembly.

Build your return features here, and assemble the headlines into a daily text
panel. Scoring the text is the Station 3 sentiment model (see src/sentiment.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Station 2 — return features
# ---------------------------------------------------------------------------

def daily_returns(prices: pd.DataFrame, price_col: str = "adjClose") -> pd.DataFrame:
    """Simple daily returns per ticker, computed on *price_col* (default adjClose).

    Returns a wide DataFrame (index = date, columns = ticker, values = daily
    return). pct_change is computed within each ticker, so the first return per
    ticker is NaN. The wide layout is what the portfolio optimiser needs (a
    covariance matrix and weight vectors over the full cross-section).

    Works for both equities and crypto — the caller passes the appropriate
    price panel.
    """
    out = prices.sort_values(["ticker", "date"]).copy()
    out["return"] = out.groupby("ticker")[price_col].pct_change()
    wide = out.pivot(index="date", columns="ticker", values="return").sort_index()
    return wide


# ---------------------------------------------------------------------------
# Station 2 — headline panel assembly
# ---------------------------------------------------------------------------

def assemble_headline_panel(headlines: pd.DataFrame) -> pd.DataFrame:
    """Assemble headlines into a daily panel per ticker and sector.

    Each headline is mapped to its equity trading day — the same date if it
    falls on a trading day, otherwise the *next* trading day.

    Returns a single DataFrame (one row per headline) with columns:
        trading_day, original_date, ticker, sector, title, url, publisher

    NOTE on Friday-after-close headlines: the news data contains only a date,
    not a timestamp (almost all rows are midnight UTC). A Friday headline is
    mapped to the next Monday (trading day), but we cannot distinguish a
    headline published before Friday's close (usable for Monday's trade) from
    one published after close (which would be look-ahead in Part B). This is a
    documented limitation of the data, not a bug in the alignment logic.
    """
    df = headlines.copy()

    # --- timezone normalisation: UTC-aware → tz-naive, second resolution ---
    if df["date"].dt.tz is not None:
        df["date"] = df["date"].dt.tz_convert("UTC").dt.tz_localize(None)
    df["date"] = df["date"].dt.floor("D")

    # --- dedup on (ticker, date, title) — many headlines per ticker-day is
    # normal, so only exact duplicates on all three fields are removed ---
    df = df.drop_duplicates(subset=["ticker", "date", "title"], keep="first")

    # --- build the equity trading calendar from the headline dates themselves ---
    all_weekdays = pd.bdate_range(df["date"].min(), df["date"].max())
    traded_dates = df["date"].unique()
    equity_cal = np.sort(all_weekdays.intersection(traded_dates))

    # --- map each headline to the next trading day ---
    idx = np.searchsorted(equity_cal, df["date"].values, side="left")
    idx = np.clip(idx, 0, len(equity_cal) - 1)
    df["trading_day"] = pd.DatetimeIndex(equity_cal[idx])
    df["trading_day"] = pd.to_datetime(df["trading_day"])

    df = df.rename(columns={"date": "original_date"})

    cols = ["trading_day", "original_date", "ticker", "sector",
            "title", "url", "publisher"]
    return df[cols].reset_index(drop=True)
