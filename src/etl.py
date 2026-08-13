"""Station 1 - your ETL: load and clean the data.

Reuses the Part A foundation (same integrity checks): a missing-date audit, a
duplicate (ticker, date) check, and an extreme-return screen. All rows are
retained and documented, never deleted.

Load raw data through src.data_access (see context/DATA_GUIDE.md). Do not commit
data files.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src import data_access


# ---------------------------------------------------------------------------
# Outlier detection constants
# ---------------------------------------------------------------------------
_ROLLING_WINDOW = 63   # ~3 months of trading days
_Z_THRESHOLD = 5.0     # flag returns beyond 5x the ticker's own trailing vol


def _build_equity_trading_calendar(dates: pd.Series) -> pd.DatetimeIndex:
    """Build the equity trading calendar from the observed price dates.

    Weekdays between the earliest and latest observed date that actually appear
    in the panel (this drops public holidays on which no ticker traded).
    """
    all_days = pd.bdate_range(dates.min(), dates.max())
    traded = dates.unique()
    return all_days.intersection(traded)


def _missing_date_audit(
    df: pd.DataFrame,
    reference_calendar: pd.DatetimeIndex,
    date_col: str = "date",
) -> pd.DataFrame:
    """Find dates in *reference_calendar* where a ticker has no row."""
    tickers = df["ticker"].unique()
    frames = []
    for t in tickers:
        ticker_dates = set(df.loc[df["ticker"] == t, date_col])
        gaps = sorted(set(reference_calendar) - ticker_dates)
        if gaps:
            frames.append(pd.DataFrame({"ticker": t, "missing_date": gaps}))
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["ticker", "missing_date"])


def _flag_outliers(
    returns: pd.DataFrame,
    z_threshold: float = _Z_THRESHOLD,
) -> pd.DataFrame:
    """Per-ticker, flag daily returns whose absolute value exceeds
    *z_threshold* times the ticker's own rolling 63-day standard deviation.

    Returns a DataFrame of flagged rows with columns:
    ticker, date, return, abs_return, rolling_std, z_score
    """
    flagged: list[pd.DataFrame] = []
    grouped = returns.groupby("ticker")
    for ticker, grp in grouped:
        grp = grp.sort_values("date").copy()
        grp["rolling_std"] = (
            grp["return"].rolling(window=_ROLLING_WINDOW, min_periods=20).std()
        )
        grp["abs_return"] = grp["return"].abs()
        grp["z_score"] = grp["abs_return"] / grp["rolling_std"]
        extreme = grp[grp["z_score"] > z_threshold].copy()
        if not extreme.empty:
            flagged.append(extreme)
    if flagged:
        return pd.concat(flagged, ignore_index=True)
    return pd.DataFrame(
        columns=["ticker", "date", "return", "abs_return", "rolling_std", "z_score"]
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_clean_equities() -> dict[str, Any]:
    """Load equity prices and run the Station 1 integrity checks.

    Returns a dict with keys:
        data          – cleaned DataFrame (``return`` column added)
        duplicates    – int, number of exact (ticker, date) duplicates dropped
        missing_dates – DataFrame of (ticker, missing_date) gaps
        outliers      – DataFrame of flagged extreme returns
    """
    df = data_access.load_equity_prices()
    df = df[df["date"] <= "2023-12-31"].copy()

    n_before = len(df)
    df = df.drop_duplicates(subset=["ticker", "date"], keep="first").reset_index(
        drop=True
    )
    duplicates_dropped = n_before - len(df)

    reference_cal = _build_equity_trading_calendar(df["date"])
    missing = _missing_date_audit(df, reference_cal)

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    df["return"] = df.groupby("ticker")["adjClose"].pct_change()

    outliers = _flag_outliers(df)

    return {
        "data": df,
        "duplicates": duplicates_dropped,
        "missing_dates": missing,
        "outliers": outliers,
    }


def load_clean_crypto() -> dict[str, Any]:
    """Load crypto prices (365-day calendar) and run the Station 1 checks.

    The 10 stray 2024-01-01 rows are capped out (sample ends 2023-12-31).

    Returns a dict with the same keys as ``load_clean_equities``.
    """
    df = data_access.load_crypto_prices()
    df = df[df["date"] <= "2023-12-31"].copy()

    n_before = len(df)
    df = df.drop_duplicates(subset=["ticker", "date"], keep="first").reset_index(
        drop=True
    )
    duplicates_dropped = n_before - len(df)

    # Crypto trades every calendar day (365/yr), so the reference calendar is
    # every day in the observed range.
    all_days = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    missing = _missing_date_audit(df, all_days)

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    df["return"] = df.groupby("ticker")["adjClose"].pct_change()

    outliers = _flag_outliers(df)

    return {
        "data": df,
        "duplicates": duplicates_dropped,
        "missing_dates": missing,
        "outliers": outliers,
    }


def equity_trading_calendar(eq_data: pd.DataFrame) -> pd.DatetimeIndex:
    """Return the full equity trading calendar as a sorted DatetimeIndex."""
    return _build_equity_trading_calendar(eq_data["date"])


def merge_crypto_returns_onto_equity(
    crypto_wide: pd.DataFrame,
    equity_cal: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Align crypto returns to the equity trading calendar.

    Crypto trades every day, equities about 252 days a year. Crypto daily
    returns are computed on crypto's own 365-day calendar, then left-merged
    onto the equity trading calendar by date; non-equity-trading days
    (weekends, equity holidays) are dropped from the merged panel. A fund
    acting on equity days therefore sees only the crypto return that occurs
    on that equity day (e.g. Sunday-close to Monday-close for a Monday).

    This drop policy was explicitly confirmed (consistent with Part A and
    CLAUDE.md Section 3).

    Parameters
    ----------
    crypto_wide : DataFrame indexed by crypto calendar date, columns = tickers.
    equity_cal : DatetimeIndex of equity trading days.

    Returns
    -------
    DataFrame indexed by *equity_cal* with the aligned crypto returns (NaN
    where a crypto ticker has no return for that equity trading day).
    """
    return crypto_wide.reindex(equity_cal)
