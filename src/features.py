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
# Station 2 — weekend-gap analysis  (Innovation 7)
# ---------------------------------------------------------------------------

def weekend_gap_analysis(
    crypto_wide: pd.DataFrame,
    equity_cal: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Quantify what fraction of each crypto ticker's cumulative return occurs
    on days when equities are closed (weekends and equity holidays).

    Crypto daily returns are computed on crypto's own 365-day calendar, so this
    splits each ticker's return stream into equity-overlap days (the date is in
    the equity trading calendar) and crypto-only days. Rows without an observed
    return (the first day of the sample per ticker, plus any missing trading
    days) are excluded from the cumulative products — a day with no observation
    contributes nothing.

    Parameters
    ----------
    crypto_wide : DataFrame
        Wide crypto returns (index = crypto calendar date, columns = tickers),
        as built by :func:`daily_returns` on the clean crypto panel.
    equity_cal : DatetimeIndex
        The full equity trading calendar (from ``etl.equity_trading_calendar``).

    Returns
    -------
    DataFrame with one row per ticker and columns:
        ticker, crypto_only_days, equity_overlap_days,
        crypto_only_cum_return, equity_overlap_cum_return,
        full_period_cum_return, weekend_return_pct
    """
    eq_set = set(equity_cal)
    long = (
        crypto_wide.reset_index()
        .melt(id_vars="date", var_name="ticker", value_name="return")
        .dropna(subset=["return"])
    )

    rows: list[dict] = []
    for ticker, grp in long.groupby("ticker"):
        grp = grp.sort_values("date")
        is_eq = grp["date"].isin(eq_set)

        # cumulative return = product of (1 + r) - 1 over the relevant days
        eq_cum = (1.0 + grp.loc[is_eq, "return"]).prod() - 1.0
        co_cum = (1.0 + grp.loc[~is_eq, "return"]).prod() - 1.0
        full_cum = (1.0 + grp["return"]).prod() - 1.0

        # weekend_return_pct: share of total cumulative return on non-equity days
        wknd_pct = (co_cum / full_cum * 100.0) if full_cum != 0 else np.nan

        rows.append({
            "ticker": ticker,
            "crypto_only_days": int((~is_eq).sum()),
            "equity_overlap_days": int(is_eq.sum()),
            "crypto_only_cum_return": co_cum,
            "equity_overlap_cum_return": eq_cum,
            "full_period_cum_return": full_cum,
            "weekend_return_pct": wknd_pct,
        })

    return pd.DataFrame(rows)


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
