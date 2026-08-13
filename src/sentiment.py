"""Station 3 - your sentiment model and index from news headlines.

This is the model step: score each headline, aggregate to a daily per-ticker
score, then to an equal-weight sector index. Headlines are a noisy proxy, so
the signal is lagged by one trading day to avoid look-ahead.
"""
from __future__ import annotations

import functools

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# VADER
# ---------------------------------------------------------------------------

# Extended finance lexicon (approved innovation, recorded in AGENTS.md). 60
# words mined from the assembled headline corpus: frequent in the headlines,
# absent from VADER's 7,502-word lexicon, and directionally meaningful in
# financial headlines. Loughran-McDonald lists are deliberately not used.
# Valences sit on VADER's own -4..+4 scale, calibrated against comparable
# VADER entries. Existing VADER words are never overwritten — only words
# absent from the base lexicon are added.
_EXTENDED_FINANCE_LEXICON: dict[str, float] = {
    # positive
    "beat": 2.2, "beats": 2.2, "rally": 2.0, "rallies": 1.8, "rallied": 1.8,
    "rebound": 1.8, "surge": 2.0, "surges": 1.8, "surged": 1.8,
    "outperform": 1.9, "outperforms": 1.6, "outperformed": 1.6,
    "upgrade": 1.7, "upgrades": 1.5, "upgraded": 1.5,
    "climb": 1.6, "climbs": 1.4, "soar": 2.1, "soars": 1.9, "soared": 1.9,
    "jump": 1.7, "jumps": 1.5, "jumped": 1.5,
    "rise": 1.6, "rises": 1.4, "rising": 1.3,
    "buyback": 1.4, "buybacks": 1.4,
    # negative
    "fall": -1.6, "falls": -1.4, "fell": -1.5, "decline": -1.6,
    "drops": -1.4, "dropped": -1.6, "slump": -2.0, "slumped": -1.8,
    "plunge": -2.3, "plunged": -2.0, "tumble": -1.9, "tumbles": -1.7,
    "tumbled": -1.7, "underperform": -1.7, "underperforms": -1.5,
    "underperformed": -1.5, "downgrade": -1.6, "downgrades": -1.4,
    "downgraded": -1.4, "selloff": -1.9, "layoffs": -1.6,
    "bankruptcy": -2.8, "default": -2.4, "sink": -1.8, "sinks": -1.6,
    "sank": -1.7, "tanked": -2.0, "crashed": -2.2, "crashes": -2.0,
    "muted": -0.8, "subdued": -0.9, "concerns": -1.3,
}


@functools.lru_cache(maxsize=1)
def _get_vader():
    """Return a cached VADER SentimentIntensityAnalyzer, downloading the
    lexicon once if needed (a build step, not part of the deployed app).

    The returned analyzer carries the extended finance lexicon above (applied
    once via ``.lexicon.update`` at build time). This is the only VADER
    construction in the codebase, and its only consumer is score_headlines(),
    so the extension cannot affect any other code path.
    """
    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sid = SentimentIntensityAnalyzer()
    except LookupError:
        import nltk
        nltk.download("vader_lexicon")
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sid = SentimentIntensityAnalyzer()
    sid.lexicon.update(_EXTENDED_FINANCE_LEXICON)
    return sid


def score_headlines(panel: pd.DataFrame) -> pd.DataFrame:
    """Score each assembled headline with VADER.

    VADER uses casing, punctuation, and negation, so the raw title is scored
    untouched — stopwords and non-sentiment words are not stripped. The score
    is VADER's compound score, which ranges from -1 (very negative) to +1
    (very positive).

    The analyzer is plain VADER extended with _EXTENDED_FINANCE_LEXICON
    (60 finance-directional words with VADER-scale valences, mined from this
    headline corpus and absent from the base lexicon). The analyzer is built
    once per run via _get_vader() and reused for every headline.

    Returns a DataFrame (one row per headline) with columns:
        trading_day, ticker, sector, title, score
    """
    sid = _get_vader()
    out = panel.copy()
    out["score"] = out["title"].apply(lambda t: sid.polarity_scores(t)["compound"])
    cols = ["trading_day", "ticker", "sector", "title", "score"]
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Sector sentiment index
# ---------------------------------------------------------------------------

def sector_sentiment_index(
    scores: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    policy: str = "carry_forward",
    lag_days: int = 1,
) -> pd.DataFrame:
    """Build a daily sentiment index per sector (equal-weight across names).

    Construction (see PROJECT_BRIEF.md Station 3):

    1. Ticker-day score = mean VADER score across a ticker's headlines that day
       (equal-weight across headlines).
    2. Sector-day raw score = mean across the tickers in the sector that had
       news that day (equal-weight across tickers).
    3. The raw sector series is reindexed to the full equity trading
       *calendar*. Ticker-days / sector-days with no headlines are handled by
       *policy*:
         - "carry_forward": forward-fill the sector's last score (chosen — the
           thin sectors never have a news gap longer than a few trading days,
           and a stale-but-real score beats inventing a neutral one).
         - "neutral": fill with 0.0 (no information).
         - "drop": leave NaN (holes propagate downstream).
    4. The signal is then lagged by *lag_days* trading days, so day t's value
       uses only headlines aligned to t-1 or earlier. The first row per sector
       is NaN by construction.

    Parameters
    ----------
    scores : DataFrame with columns trading_day, ticker, sector, score.
    calendar : DatetimeIndex — the full equity trading calendar.
    policy : str, one of "carry_forward", "neutral", "drop".
    lag_days : int, trading-day lag (>= 1).

    Returns
    -------
    Long DataFrame (one row per sector and trading day) with columns:
        date, sector, sentiment
    where *date* is the lagged trading day.
    """
    if policy not in {"carry_forward", "neutral", "drop"}:
        raise ValueError(f"unknown no-headline policy: {policy!r}")

    # --- ticker-day score (equal-weight across headlines) ---
    ticker_day = (
        scores.groupby(["trading_day", "ticker", "sector"])["score"]
        .mean()
        .reset_index()
    )

    # --- sector-day raw score (equal-weight across tickers) ---
    sector_day = (
        ticker_day.groupby(["trading_day", "sector"])["score"]
        .mean()
        .reset_index()
    )

    # --- full trading grid (date x sector) ---
    wide = sector_day.pivot(index="trading_day", columns="sector", values="score")
    wide = wide.reindex(calendar)
    wide.index.name = "date"

    # --- no-headline policy ---
    if policy == "carry_forward":
        wide = wide.ffill()
    elif policy == "neutral":
        wide = wide.fillna(0.0)
    # "drop": leave NaN

    # --- lag by trading days ---
    if lag_days is None or lag_days < 1:
        lagged = wide
    else:
        lagged = wide.shift(lag_days)

    long = lagged.reset_index().melt(
        id_vars="date", var_name="sector", value_name="sentiment"
    )
    return long.sort_values(["sector", "date"]).reset_index(drop=True)
