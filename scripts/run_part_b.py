"""Reproduce your Part B results. Run from the project root:

    python scripts/run_part_b.py

Pipeline (Station 3): clean data -> returns -> combined panel -> headline
panel -> VADER sentiment sector index (carry-forward + 1-day lag) -> walk-forward
out-of-sample funds -> sector-level sentiment fusion -> save results/ artifacts
that the Streamlit app reads.
"""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import data_access, etl, features, fusion, portfolios, sentiment  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"
DATA_DIR = ROOT / "results" / "data"
TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

TILT = 0.10  # sentiment tilt strength (per unit cross-sectional z-score)
# Exact rebalance rule (approved, stated in AGENTS.md and the report):
# combined/equity funds rebalance every 21 trading days; crypto funds every
# 30 trading days on the 365-day crypto calendar.
# Initial estimation window (explicitly confirmed, not assumed): one year of
# each family's own calendar — 252 equity days for combined/equity, 365
# crypto days for crypto — before the out-of-sample period starts.
FUND_FAMILIES = {
    "Combined": {"ppy": 252, "initial": 252, "rebalance": 21},
    "Equity": {"ppy": 252, "initial": 252, "rebalance": 21},
    "Crypto": {"ppy": 365, "initial": 365, "rebalance": 30},
}
BASE_METHODS = {
    "Combined": ["min_variance", "max_sharpe", "risk_parity", "equal_weight"],
    "Equity": ["min_variance", "max_sharpe"],
    "Crypto": ["min_variance", "max_sharpe"],
}


def _annotate_sample(ax, dates: pd.Series, loc: str = "upper left") -> None:
    dmin = pd.to_datetime(dates).min()
    dmax = pd.to_datetime(dates).max()
    label = f"Sample: {dmin:%Y-%m-%d} to {dmax:%Y-%m-%d}"
    ax.annotate(label, xy=(0.01, 0.97), xycoords="axes fraction",
                fontsize=8, va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))


def _finish_fig(fig, path: pathlib.Path, caption: str) -> None:
    """Apply the figure standard (title, labelled axes, sample period, and a
    caption below the plot), then save and close. See AGENTS.md/CLAUDE.md."""
    fig.tight_layout(rect=[0, 0.055, 1, 1])
    fig.text(0.5, 0.012, caption, ha="center", va="bottom", fontsize=8,
             style="italic", wrap=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _fund_label(family: str, method: str, fused: bool = False) -> str:
    label = portfolios.METHOD_LABELS[method]
    return f"{family} {label}" + (" + Sentiment" if fused else "")


def _drawdown(returns: pd.Series) -> pd.Series:
    cum = (1.0 + returns).cumprod()
    return cum / cum.cummax() - 1.0


def main() -> None:
    print("=" * 60)
    print("FINS3645 Part B — funds, sentiment, fusion")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load + clean
    # ------------------------------------------------------------------
    print("\n[1/7] Loading and cleaning data...")
    eq = etl.load_clean_equities()
    cr = etl.load_clean_crypto()
    news_raw = data_access.load_news_headlines()
    eq_data, cr_data = eq["data"], cr["data"]
    print(f"  equities: {eq_data.shape[0]} rows, {eq_data['ticker'].nunique()} tickers "
          f"(dups {eq['duplicates']})")
    print(f"  crypto:   {cr_data.shape[0]} rows, {cr_data['ticker'].nunique()} tickers "
          f"(dups {cr['duplicates']})")
    print(f"  headlines: {news_raw.shape[0]} rows")

    # ------------------------------------------------------------------
    # 2. Return panels (wide)
    # ------------------------------------------------------------------
    print("\n[2/7] Building return panels...")
    eq_wide = features.daily_returns(eq_data)
    cr_wide = features.daily_returns(cr_data)
    eq_cal = etl.equity_trading_calendar(eq_data)

    cr_on_eq = etl.merge_crypto_returns_onto_equity(cr_wide, eq_cal)
    combined_wide = eq_wide.join(cr_on_eq)
    print(f"  equity panel:    {eq_wide.shape}")
    print(f"  crypto panel:    {cr_wide.shape}")
    print(f"  combined panel:  {combined_wide.shape}")

    # ------------------------------------------------------------------
    # 3. Headline panel + sentiment sector index
    # ------------------------------------------------------------------
    print("\n[3/7] Scoring headlines and building the sector index...")
    headline_panel = features.assemble_headline_panel(news_raw)
    print(f"  headline panel: {headline_panel.shape[0]} rows")
    scores = sentiment.score_headlines(headline_panel)
    print(f"  scored headlines: {scores.shape[0]} rows")
    sector_index = sentiment.sector_sentiment_index(
        scores, calendar=eq_cal, policy="carry_forward", lag_days=1
    )
    sector_index.to_csv(DATA_DIR / "sector_sentiment_index.csv", index=False)
    print(f"  saved results/data/sector_sentiment_index.csv "
          f"({len(sector_index)} rows)")

    ticker_sector = (
        eq_data[["ticker", "sector"]].drop_duplicates()
        .set_index("ticker")["sector"].to_dict()
    )

    # ------------------------------------------------------------------
    # 4. Walk-forward out-of-sample funds
    # ------------------------------------------------------------------
    print("\n[4/7] Running walk-forward OOS backtests...")
    panels = {
        "Combined": combined_wide,
        "Equity": eq_wide,
        "Crypto": cr_wide,
    }
    backtests: dict[str, dict] = {}
    for family, cfg in FUND_FAMILIES.items():
        for method in BASE_METHODS[family]:
            key = _fund_label(family, method)
            print(f"  {key} ...", end=" ", flush=True)
            bt = portfolios.oos_backtest(
                panels[family],
                method=method,
                initial_window=cfg["initial"],
                rebalance_every=cfg["rebalance"],
                estimation_window=cfg["initial"],
                periods_per_year=cfg["ppy"],
            )
            backtests[key] = bt
            m = bt["metrics"]
            print(f"OOS from {bt['first_live_date'].date()}, "
                  f"ann.ret {m['annualised_return']:+.2%}, "
                  f"Sharpe {m['sharpe']:.2f}, MDD {m['max_drawdown']:.1%}")

    # ------------------------------------------------------------------
    # 5. Sentiment fusion (sector-level tilt on the combined funds)
    # ------------------------------------------------------------------
    print("\n[5/7] Applying the sentiment tilt to the combined funds...")
    fused_keys = []
    for method in ["min_variance", "max_sharpe"]:
        base_key = _fund_label("Combined", method)
        fused_key = _fund_label("Combined", method, fused=True)
        base = backtests[base_key]
        adj_weights = fusion.apply_sentiment(
            base["weights"], sector_index, ticker_sector, tilt=TILT
        )
        fused_rets = adj_weights.mul(combined_wide).sum(axis=1).reindex(
            adj_weights.index
        )
        fused_metrics = portfolios.performance_metrics(
            fused_rets, periods_per_year=252
        )
        backtests[fused_key] = {
            "method": method,
            "returns": fused_rets,
            "weights": adj_weights,
            "growth": (1.0 + fused_rets).cumprod(),
            "metrics": fused_metrics,
            "first_live_date": base["first_live_date"],
        }
        fused_keys.append(fused_key)
        print(f"  {fused_key}: Sharpe {fused_metrics['sharpe']:.2f} "
              f"(base {backtests[base_key]['metrics']['sharpe']:.2f})")

    # ------------------------------------------------------------------
    # 6. Save tables
    # ------------------------------------------------------------------
    print("\n[6/7] Saving tables and data...")

    metric_rows = []
    for key, bt in backtests.items():
        family = key.split(" ")[0]
        fused = key.endswith("+ Sentiment")
        method = bt["method"]
        m = bt["metrics"]
        metric_rows.append({
            "fund": key,
            "family": family,
            "method": method,
            "fused": fused,
            "first_live_date": pd.Timestamp(bt["first_live_date"]).date(),
            "annualised_return": m["annualised_return"],
            "annualised_volatility": m["annualised_volatility"],
            "sharpe": m["sharpe"],
            "max_drawdown": m["max_drawdown"],
            "growth_of_1": m["growth_of_1"],
        })
    perf_table = pd.DataFrame(metric_rows)
    perf_table.to_csv(TABLE_DIR / "performance_metrics.csv", index=False)
    print(f"  saved results/tables/performance_metrics.csv "
          f"({len(perf_table)} funds)")

    fund_returns = pd.concat([
        pd.DataFrame({"date": bt["returns"].index, "fund": key,
                      "return": bt["returns"].to_numpy()})
        for key, bt in backtests.items()
    ], ignore_index=True)
    fund_returns.to_csv(DATA_DIR / "fund_returns.csv", index=False)
    print(f"  saved results/data/fund_returns.csv ({len(fund_returns)} rows)")

    fund_weights = pd.concat([
        pd.DataFrame({
            "date": np.repeat(bt["weights"].index, bt["weights"].shape[1]),
            "fund": key,
            "ticker": np.tile(bt["weights"].columns, len(bt["weights"])),
            "weight": bt["weights"].to_numpy().ravel(),
        })
        for key, bt in backtests.items()
    ], ignore_index=True)
    fund_weights.to_csv(DATA_DIR / "fund_weights.csv", index=False)
    print(f"  saved results/data/fund_weights.csv ({len(fund_weights)} rows)")

    fusion_rows = []
    for fused_key in fused_keys:
        base_key = fused_key.replace(" + Sentiment", "")
        bm = backtests[base_key]["metrics"]
        fm = backtests[fused_key]["metrics"]
        fusion_rows.append({
            "fund": fused_key,
            "base_fund": base_key,
            "tilt": TILT,
            "base_annualised_return": bm["annualised_return"],
            "base_annualised_volatility": bm["annualised_volatility"],
            "base_sharpe": bm["sharpe"],
            "base_max_drawdown": bm["max_drawdown"],
            "fused_annualised_return": fm["annualised_return"],
            "fused_annualised_volatility": fm["annualised_volatility"],
            "fused_sharpe": fm["sharpe"],
            "fused_max_drawdown": fm["max_drawdown"],
            "sharpe_delta": fm["sharpe"] - bm["sharpe"],
        })
    fusion_table = pd.DataFrame(fusion_rows)
    fusion_table.to_csv(TABLE_DIR / "fusion_comparison.csv", index=False)
    print(f"  saved results/tables/fusion_comparison.csv")

    # ------------------------------------------------------------------
    # 7. Figures
    # ------------------------------------------------------------------
    print("\n[7/7] Generating figures...")

    combined_base = [_fund_label("Combined", m) for m in BASE_METHODS["Combined"]]

    # --- Figure 1: growth of $1 across methods (combined funds) ---
    fig, ax = plt.subplots(figsize=(10, 5))
    for key in combined_base:
        ax.plot(backtests[key]["growth"], label=key, linewidth=1.4)
    ax.set_title("Combined Funds — Out-of-Sample Growth of $1")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1 (1 = start of OOS)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    _annotate_sample(ax, backtests[combined_base[0]]["growth"].index)
    _finish_fig(fig, FIG_DIR / "growth_of_1.png",
                "Figure 1. Out-of-sample growth of $1 per combined fund method "
                "(walk-forward, rebalanced every 21 trading days).")
    print("  saved results/figures/growth_of_1.png")

    # --- Figure 2: drawdown for at least one fund ---
    fig, ax = plt.subplots(figsize=(10, 5))
    for key in [_fund_label("Combined", "min_variance"),
                _fund_label("Combined", "max_sharpe")]:
        dd = _drawdown(backtests[key]["returns"])
        ax.plot(dd, label=key, linewidth=1.2)
    ax.set_title("Combined Funds — Out-of-Sample Drawdown")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (negative = peak-to-trough loss)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    _annotate_sample(ax, dd.index)
    _finish_fig(fig, FIG_DIR / "drawdown.png",
                "Figure 2. Out-of-sample peak-to-trough drawdown for the combined "
                "min-variance and max-sharpe funds.")
    print("  saved results/figures/drawdown.png")

    # --- Figure 3: sector weights over time (combined min-var vs max-sharpe) ---
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    for ax, method in zip(axes, ["min_variance", "max_sharpe"]):
        key = _fund_label("Combined", method)
        w = backtests[key]["weights"]
        sector_map = {t: ticker_sector[t] for t in w.columns if t in ticker_sector}
        crypto_cols = [c for c in w.columns if c not in sector_map]
        sector_w = w.rename(columns=sector_map).T.groupby(level=0).sum().T
        sector_w["Crypto"] = w[crypto_cols].sum(axis=1)
        sector_w = sector_w.drop(columns=[c for c in sector_w.columns if c in crypto_cols])
        sector_w.plot.area(ax=ax, stacked=True, alpha=0.75, linewidth=0.0, legend=False)
        ax.set_title(f"{key} — Sector Weights Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Portfolio weight")
        ax.grid(True, alpha=0.3)
        _annotate_sample(ax, w.index, loc="upper right")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, fontsize=8,
               bbox_to_anchor=(0.5, 1.02))
    _finish_fig(fig, FIG_DIR / "weights_over_time.png",
                "Figure 3. Sector weights over time for the combined min-variance and "
                "max-sharpe funds; crypto tickers aggregated into a single Crypto band.")
    print("  saved results/figures/weights_over_time.png")

    # --- Figure 4: Sharpe barplot across funds and methods ---
    base_funds = [k for k in backtests if not k.endswith("+ Sentiment")]
    sharpe_series = pd.Series(
        {k: backtests[k]["metrics"]["sharpe"] for k in base_funds}
    ).sort_values()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(sharpe_series.index, sharpe_series.values, color="steelblue")
    ax.set_title("Out-of-Sample Sharpe Ratios by Fund and Method")
    ax.set_xlabel("Sharpe ratio (annualised, risk-free rate = 0)")
    ax.set_ylabel("Fund")
    ax.grid(True, axis="x", alpha=0.3)
    for i, v in enumerate(sharpe_series.values):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8)
    sample_dates = pd.concat(
        [pd.Series(backtests[k]["returns"].index) for k in base_funds]
    )
    _annotate_sample(ax, sample_dates, loc="upper right")
    _finish_fig(fig, FIG_DIR / "sharpe_barplot.png",
                "Figure 4. Annualised out-of-sample Sharpe ratios (risk-free rate = 0) "
                "across funds and optimisation methods.")
    print("  saved results/figures/sharpe_barplot.png")

    # --- Figure 5: sector sentiment index over time ---
    fig, ax = plt.subplots(figsize=(12, 5))
    for sector, grp in sector_index.groupby("sector"):
        grp = grp.sort_values("date")
        ax.plot(grp["date"], grp["sentiment"], label=sector, linewidth=1.0)
    ax.set_title("Equity Sector Sentiment Index (VADER, carry-forward, 1-day lag)")
    ax.set_xlabel("Trading day")
    ax.set_ylabel("Sentiment index (mean VADER compound)")
    ax.legend(fontsize=8, ncol=5)
    ax.grid(True, alpha=0.3)
    _annotate_sample(ax, sector_index["date"])
    _finish_fig(fig, FIG_DIR / "sentiment_index.png",
                "Figure 5. Equal-weighted sector sentiment index (VADER compound, "
                "carry-forward, one-trading-day lag).")
    print("  saved results/figures/sentiment_index.png")

    # --- Figure 6: fusion before-vs-after (combined min-variance) ---
    base_key = _fund_label("Combined", "min_variance")
    fused_key = _fund_label("Combined", "min_variance", fused=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(backtests[base_key]["growth"], label=base_key, linewidth=1.4)
    ax.plot(backtests[fused_key]["growth"], label=fused_key, linewidth=1.4)
    ax.set_title(f"Fusion — Sentiment Tilt Before vs After (tilt = {TILT})")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1 (1 = start of OOS)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    _annotate_sample(ax, backtests[base_key]["growth"].index)
    _finish_fig(fig, FIG_DIR / "fusion_before_after.png",
                "Figure 6. Sentiment-tilt fusion effect: combined min-variance fund "
                "before vs after the sector-level tilt (tilt = 0.10).")
    print("  saved results/figures/fusion_before_after.png")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Part B complete. Outputs saved to results/")
    print(f"  Data:   {list(DATA_DIR.glob('*.csv'))}")
    print(f"  Tables: {list(TABLE_DIR.glob('*.csv'))}")
    print(f"  Figures: {list(FIG_DIR.glob('*.png'))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
