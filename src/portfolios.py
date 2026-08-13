"""Station 3 - your funds: optimal portfolios + out-of-sample backtest.

Build at least a combined equity-plus-crypto fund with two optimisation methods.
Backtest rules: walk-forward, no look-ahead, weights from past data only,
annualise with 252 (equity) or 365 (crypto). See the brief, Part B.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scipy.optimize import minimize

# Method name -> human-readable fund label
METHOD_LABELS = {
    "min_variance": "Min-Variance",
    "max_sharpe": "Max-Sharpe",
    "risk_parity": "Risk Parity",
    "equal_weight": "Equal Weight",
}


def performance_metrics(
    daily_returns: pd.Series,
    periods_per_year: int = 252,
    risk_free: float = 0.0,
) -> dict:
    """Annualised return, annualised volatility, Sharpe, and max drawdown.

    Return is annualised geometrically, volatility with the square-root rule,
    and the Sharpe ratio uses the stated risk-free rate (default zero, as
    declared in the report). Max drawdown is measured on the growth-of-$1
    curve.

    Parameters
    ----------
    daily_returns : Series of daily portfolio returns.
    periods_per_year : 252 for equity/combined calendars, 365 for crypto-only.
    risk_free : annual risk-free rate assumed for the Sharpe ratio.
    """
    r = daily_returns.dropna()
    out: dict = {
        "annualised_return": np.nan,
        "annualised_volatility": np.nan,
        "sharpe": np.nan,
        "max_drawdown": np.nan,
        "growth_of_1": np.nan,
        "n_obs": int(len(r)),
        "periods_per_year": int(periods_per_year),
    }
    if len(r) < 2:
        return out

    n = len(r)
    ann_return = (1.0 + r).prod() ** (periods_per_year / n) - 1.0
    ann_vol = float(r.std(ddof=1) * np.sqrt(periods_per_year))
    growth = float((1.0 + r).prod() - 1.0)
    cum = (1.0 + r).cumprod()
    running_max = cum.cummax()
    drawdown = cum / running_max - 1.0
    max_dd = float(drawdown.min())
    sharpe = (ann_return - risk_free) / ann_vol if ann_vol > 0 else np.nan

    return {
        "annualised_return": float(ann_return),
        "annualised_volatility": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "growth_of_1": growth,
        "n_obs": int(n),
        "periods_per_year": int(periods_per_year),
    }


# ---------------------------------------------------------------------------
# Weight solvers
# ---------------------------------------------------------------------------

def _shrink_cov(cov: np.ndarray, delta: float = 0.05) -> np.ndarray:
    """Ledoit-Wolf-style shrinkage of the sample covariance.

    Daily-return covariances are noisy and often near-singular; a small
    shrinkage toward a scalar identity keeps SLSQP from stalling and the
    resulting weights stable across rebalances.
    """
    n = cov.shape[0]
    target = np.mean(np.diag(cov)) * np.eye(n)
    return (1.0 - delta) * cov + delta * target


def _solve(obj, n: int, maxiter: int = 500) -> np.ndarray:
    """Long-only, fully-invested weights minimising *obj*."""
    w0 = np.full(n, 1.0 / n)
    cons = {"type": "eq", "fun": lambda w: w.sum() - 1.0}
    bounds = [(0.0, 1.0)] * n
    res = minimize(obj, w0, method="SLSQP", bounds=bounds, constraints=cons,
                   options={"maxiter": maxiter, "ftol": 1e-10})
    w = np.asarray(res.x, dtype=float)
    if not np.all(np.isfinite(w)) or not np.isclose(w.sum(), 1.0, atol=1e-4):
        w = np.full(n, 1.0 / n)
    w = np.clip(w, 0.0, None)
    w = w / w.sum()
    return w


def _min_variance_weights(cov: np.ndarray) -> np.ndarray:
    cov = _shrink_cov(cov)
    return _solve(lambda w: float(w @ cov @ w), len(cov))


def _max_sharpe_weights(cov: np.ndarray, mu: np.ndarray) -> np.ndarray:
    cov = _shrink_cov(cov)

    def obj(w):
        var = float(w @ cov @ w)
        if var <= 0.0:
            return 1e6
        return -float(w @ mu) / np.sqrt(var)

    return _solve(obj, len(cov))


def _risk_parity_weights(cov: np.ndarray) -> np.ndarray:
    cov = _shrink_cov(cov)
    n = len(cov)

    def obj(w):
        var = float(w @ cov @ w)
        if var <= 0.0:
            return 1e6
        rc = w * (cov @ w) / var
        return float(np.sum((rc - 1.0 / n) ** 2))

    return _solve(obj, n)


def _estimate_weights(window: pd.DataFrame, method: str) -> pd.Series:
    """Estimate target weights from a window of daily returns (past data only)."""
    tickers = window.columns
    n = len(tickers)
    if method == "equal_weight":
        return pd.Series(1.0 / n, index=tickers)

    cov = window.cov().to_numpy()
    if method == "min_variance":
        w = _min_variance_weights(cov)
    elif method == "risk_parity":
        w = _risk_parity_weights(cov)
    elif method == "max_sharpe":
        mu = window.mean().to_numpy()
        w = _max_sharpe_weights(cov, mu)
    else:
        raise ValueError(f"unknown method: {method!r}")
    return pd.Series(w, index=tickers)


# ---------------------------------------------------------------------------
# Walk-forward backtest
# ---------------------------------------------------------------------------

def oos_backtest(
    returns: pd.DataFrame,
    method: str = "min_variance",
    initial_window: int = 252,
    rebalance_every: int = 21,
    estimation_window: int | None = None,
    periods_per_year: int = 252,
    risk_free: float = 0.0,
) -> dict:
    """Walk-forward out-of-sample backtest with no look-ahead.

    Weights are formed only from past data: at each rebalance date r the target
    weights are estimated from the trailing *estimation_window* trading days
    (ending at r, inclusive) and applied to the days (r, next_r]. A decision on
    day t therefore uses only information available up to the most recent
    rebalance at or before t-1.

    The out-of-sample period starts the trading day after the first rebalance,
    i.e. after *initial_window* trading days of history. *rebalance_every* is
    the spacing between rebalances in trading days.

    Parameters
    ----------
    returns : wide DataFrame (date x ticker) of daily returns.
    method : "min_variance", "max_sharpe", "risk_parity", or "equal_weight".
    initial_window : trading days of history before the first rebalance.
    rebalance_every : trading days between rebalances (21 = monthly-ish).
    estimation_window : trading days of past data used per estimate (defaults
        to *initial_window*).
    periods_per_year : annualisation factor for the OOS metrics.
    risk_free : annual risk-free rate for the Sharpe ratio.

    Returns
    -------
    dict with keys:
        method, returns (OOS daily Series), weights (date x ticker OOS),
        growth (OOS growth of $1), metrics (performance_metrics dict),
        rebalance_dates, first_live_date
    """
    rets = returns.dropna(how="all").sort_index()
    if estimation_window is None:
        estimation_window = initial_window

    dates = rets.index
    tickers = list(rets.columns)
    n_days = len(dates)

    rb_idx = list(range(initial_window, n_days, rebalance_every))
    if not rb_idx:
        raise ValueError("not enough data for the initial window plus one rebalance")
    rebalance_dates = dates[rb_idx]

    weight_mat = pd.DataFrame(0.0, index=dates, columns=tickers)
    for i, r in enumerate(rebalance_dates):
        pos = dates.get_loc(r)
        if i + 1 < len(rebalance_dates):
            end = dates.get_loc(rebalance_dates[i + 1]) + 1  # inclusive of next rebalance day
        else:
            end = n_days
        start = max(0, pos - estimation_window + 1)
        window = rets.iloc[start:pos + 1]

        win = window.dropna(axis=1, thresh=max(2, int(estimation_window * 0.5)))
        win = win.dropna(axis=0)
        if win.empty or len(win.columns) < 2:
            w = pd.Series(1.0 / len(tickers), index=tickers)
        else:
            w = _estimate_weights(win, method).reindex(tickers, fill_value=0.0)

        weight_mat.iloc[pos + 1:end, :] = w.to_numpy()

    # Out-of-sample: the trading day after the first rebalance (index-based, so
    # it is always a real trading day).
    oos_start = rb_idx[0] + 1
    first_live = dates[oos_start]
    oos_weights = weight_mat.iloc[oos_start:, :]
    oos_rets = oos_weights.mul(rets).sum(axis=1).reindex(oos_weights.index)

    growth = (1.0 + oos_rets).cumprod()
    metrics = performance_metrics(oos_rets, periods_per_year=periods_per_year,
                                  risk_free=risk_free)

    return {
        "method": method,
        "returns": oos_rets,
        "weights": oos_weights,
        "growth": growth,
        "metrics": metrics,
        "rebalance_dates": rebalance_dates,
        "first_live_date": first_live,
    }
