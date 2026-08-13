"""Station 3 (extension) - fuse sentiment into the funds.

Tilt or factor: combine the lagged sector sentiment signal with the portfolio
weights, look-ahead safe, then test whether it adds value. An honest negative
result, explained, is good work.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def apply_sentiment(
    weights: pd.DataFrame,
    sentiment: pd.DataFrame,
    ticker_sector: dict | pd.Series,
    tilt: float = 0.10,
) -> pd.DataFrame:
    """Tilt portfolio weights toward the sectors with the most positive lagged
    sentiment (a sector-level sentiment tilt).

    The fusion operates at the sector level only: every ticker in a sector
    receives the same sector multiplier, computed from the sentiment index
    lagged by one trading day (see src/sentiment.py). Crypto tickers have no
    sector and no news, so their multiplier is 1 (the tilt touches only the
    equity leg of a combined fund). The adjusted weights are renormalised to
    sum to 1 on each date, so the fund stays fully invested.

    Rule per date d::

        z_s   = (sentiment[d, s] - mean_s(sentiment[d, :])) / std_s(sentiment[d, :])
        m_i   = 1 + tilt * z_sector(i)
        w'_i  = w_i * m_i        then  w' = w' / sum(w')

    Parameters
    ----------
    weights : wide DataFrame (date x ticker) of applied fund weights.
    sentiment : long DataFrame (date, sector, sentiment) — the lagged index.
    ticker_sector : mapping from ticker to sector (equity tickers only).
    tilt : strength of the tilt per unit of cross-sectional z-score.

    Returns
    -------
    Adjusted weights DataFrame (same index and columns as *weights*).
    """
    # --- wide sentiment per date, cross-sectional z-score across sectors ---
    sent_wide = sentiment.pivot(index="date", columns="sector", values="sentiment")
    mean_s = sent_wide.mean(axis=1)
    std_s = sent_wide.std(axis=1).replace(0.0, np.nan)
    z = sent_wide.sub(mean_s, axis=0).div(std_s, axis=0)
    z = z.reindex(weights.index).fillna(0.0)

    # --- per-ticker multiplier (sector-level) ---
    mult = pd.DataFrame(1.0, index=weights.index, columns=weights.columns)
    for ticker in weights.columns:
        sector = ticker_sector.get(ticker)
        if sector is not None and sector in z.columns:
            mult[ticker] = 1.0 + tilt * z[sector]

    adj = weights.mul(mult)
    total = adj.sum(axis=1).replace(0.0, np.nan)
    adj = adj.div(total, axis=0).fillna(0.0)
    return adj
