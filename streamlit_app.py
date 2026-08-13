"""UNSW StableTrade - systematic multi-asset funds with news-sentiment analytics.

The deployed app reads precomputed artifacts from results/ (fund returns and
weights, the sector sentiment index, and the metrics tables) so it stays light
and fast on the free Streamlit tier - it never recomputes backtests and never
runs VADER.

Run locally:   streamlit run streamlit_app.py
Deploy:        push this folder to a public GitHub repo, then connect it on
               share.streamlit.io with entrypoint streamlit_app.py (see brief
               App. D). Run scripts/run_part_b.py first to (re)generate results/.
"""
import pathlib

import numpy as np
import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent

st.set_page_config(page_title="UNSW StableTrade", page_icon="📈", layout="wide")

APP_NAME = "UNSW StableTrade"
TAGLINE = "Systematically managed multi-asset funds with a news-sentiment overlay"


@st.cache_data(ttl=86_400, show_spinner="Loading fund data...")
def _load_fund_returns() -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "data" / "fund_returns.csv",
                       parse_dates=["date"])


@st.cache_data(ttl=86_400, show_spinner="Loading fund weights...")
def _load_fund_weights() -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "data" / "fund_weights.csv",
                       parse_dates=["date"])


@st.cache_data(ttl=86_400, show_spinner="Loading sentiment index...")
def _load_sentiment() -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "data" / "sector_sentiment_index.csv",
                       parse_dates=["date"])


@st.cache_data(ttl=86_400, show_spinner="Loading metrics...")
def _load_metrics() -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "tables" / "performance_metrics.csv",
                       parse_dates=["first_live_date"])


@st.cache_data(ttl=86_400)
def _load_fusion_table() -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "tables" / "fusion_comparison.csv")


@st.cache_data(ttl=86_400, show_spinner="Loading weekend-gap stats...")
def _load_weekend_gap() -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "tables" / "weekend_gap_returns.csv")


def _growth_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Wide cumulative-growth-of-$1 frame (date x fund) from long returns."""
    wide = returns.pivot(index="date", columns="fund", values="return").sort_index()
    return (1.0 + wide).cumprod()


def _drawdowns(returns: pd.DataFrame) -> pd.DataFrame:
    wide = returns.pivot(index="date", columns="fund", values="return").sort_index()
    cum = (1.0 + wide).cumprod()
    return cum / cum.cummax() - 1.0


def _format_pct(v: float) -> str:
    return f"{v:+.1%}" if v == v else "n/a"


def _format_metric(v: float) -> str:
    return f"{v:.2f}" if v == v else "n/a"


# Approved stress windows (Innovation 2), all inside the out-of-sample period.
STRESS_EVENTS = [
    ("2022 bear market", "2022-01-03", "2022-12-30"),
    ("FTX collapse", "2022-11-07", "2022-12-31"),
    ("March 2023 banking stress", "2023-03-06", "2023-03-31"),
]


def _event_metrics(returns: pd.DataFrame, start: str, end: str) -> dict:
    """Cumulative return, worst single day and peak-to-trough drawdown of one
    fund's return series inside a calendar window (clipped to the fund's
    out-of-sample range)."""
    sub = returns[(returns["date"] >= pd.Timestamp(start))
                  & (returns["date"] <= pd.Timestamp(end))]
    cum = (1.0 + sub["return"]).prod() - 1.0
    worst = sub["return"].min()
    dd = (1.0 + sub["return"]).cumprod()
    mdd = (dd / dd.cummax() - 1.0).min()
    return {"cum_return": cum, "worst_day": worst, "max_drawdown": mdd}


def _stress_chart(returns: pd.DataFrame):
    """Drawdown chart for one fund with the stress windows shaded."""
    import matplotlib.pyplot as plt

    fund = returns["fund"].iloc[0]
    dd = _drawdowns(returns)[fund]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.plot(dd.index, dd.values, color="steelblue", linewidth=1.2)
    shades = {"2022 bear market": "#ef5350", "FTX collapse": "#ffa726",
              "March 2023 banking stress": "#ab47bc"}
    for label, start, end in STRESS_EVENTS:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end),
                   color=shades[label], alpha=0.14)
    ax.axhline(0.0, color="gray", linewidth=0.8)
    ax.set_title(f"{fund} — drawdown with stress windows shaded")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (negative = peak-to-trough loss)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


funds, facts, allocate, sentiment_tab = st.tabs(
    ["Compare funds", "Fact sheet", "Allocate", "Sentiment"]
)

with st.sidebar:
    st.title(APP_NAME)
    st.caption(TAGLINE)
    st.divider()
    ret = _load_fund_returns()
    _oos_min = ret["date"].min()
    _oos_max = ret["date"].max()
    st.caption(f"Risk-free rate assumed 0%; zero transaction costs; "
               f"out-of-sample period {_oos_min:%Y-%m-%d} to {_oos_max:%Y-%m-%d}.")

# ---------------------------------------------------------------------------
# Tab 1 - Compare funds
# ---------------------------------------------------------------------------
with funds:
    st.header("Compare the funds")
    metrics = _load_metrics()
    returns = _load_fund_returns()

    display_cols = ["fund", "family", "method", "fused", "first_live_date",
                    "annualised_return", "annualised_volatility", "sharpe",
                    "max_drawdown", "growth_of_1"]
    show = metrics[display_cols].copy()
    show["annualised_return"] = show["annualised_return"].map(_format_pct)
    show["annualised_volatility"] = show["annualised_volatility"].map(_format_pct)
    show["max_drawdown"] = show["max_drawdown"].map(_format_pct)
    show["sharpe"] = show["sharpe"].map(_format_metric)
    show["growth_of_1"] = show["growth_of_1"].map(lambda v: f"${v:,.2f}" if v == v else "n/a")
    show = show.rename(columns={
        "fund": "Fund", "family": "Family", "method": "Method", "fused": "Sentiment tilt",
        "first_live_date": "First live date", "annualised_return": "Ann. return",
        "annualised_volatility": "Ann. volatility", "sharpe": "Sharpe",
        "max_drawdown": "Max drawdown", "growth_of_1": "Growth of $1",
    })
    st.dataframe(show, hide_index=True, width="stretch")

    st.subheader("Growth of $1 (out-of-sample)")
    base_funds = [c for c in returns["fund"].unique() if not c.endswith("+ Sentiment")]
    st.line_chart(_growth_matrix(returns)[base_funds], height=380)

    st.caption(
        f"Out-of-sample period {returns['date'].min():%Y-%m-%d} to "
        f"{returns['date'].max():%Y-%m-%d} after a one-year estimation window. "
        f"First live date: combined/equity from "
        f"{returns.loc[returns['fund'].str.startswith('Combined'), 'date'].min():%Y-%m-%d}, "
        f"crypto from "
        f"{returns.loc[returns['fund'].str.startswith('Crypto'), 'date'].min():%Y-%m-%d}. "
        f"Weights are formed from past data only; rebalance rule: every 21 trading "
        f"days for combined/equity funds, every 30 for crypto funds."
    )

# ---------------------------------------------------------------------------
# Tab 2 - Fact sheet
# ---------------------------------------------------------------------------
with facts:
    st.header("Fund fact sheet")
    metrics = _load_metrics()
    returns = _load_fund_returns()
    weights = _load_fund_weights()

    all_funds = sorted(returns["fund"].unique())
    chosen = st.selectbox("Choose a fund", all_funds)

    m = metrics[metrics["fund"] == chosen].iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Annualised return", _format_pct(m["annualised_return"]))
    c2.metric("Annualised volatility", _format_pct(m["annualised_volatility"]))
    c3.metric("Sharpe ratio", _format_metric(m["sharpe"]))
    c4.metric("Max drawdown", _format_pct(m["max_drawdown"]))
    c5.metric("Growth of $1", f"${m['growth_of_1']:,.2f}" if m["growth_of_1"] == m["growth_of_1"] else "n/a")

    fund_ret = returns[returns["fund"] == chosen]
    growth = _growth_matrix(fund_ret)[chosen]
    st.subheader("Growth of $1")
    st.line_chart(growth, height=300)

    st.subheader("Drawdown")
    st.line_chart(_drawdowns(fund_ret)[chosen], height=280)

    st.subheader("Current holdings (target weights from the last rebalance)")
    fund_w = weights[weights["fund"] == chosen]
    last_date = fund_w["date"].max()
    holdings = (
        fund_w[fund_w["date"] == last_date][["ticker", "weight"]]
        .sort_values("weight", ascending=False)
        .reset_index(drop=True)
    )
    holdings["weight"] = holdings["weight"].map(lambda v: f"{v:.2%}")
    st.write(f"Holdings as of {last_date.date()}")
    st.dataframe(holdings, hide_index=True, width="stretch")

    if chosen.startswith("Crypto"):
        st.subheader("Crypto weekend gap — the underlying assets")
        st.caption("Crypto trades 365 days a year; equities do not. This shows "
                   "how much of each coin's cumulative return over the full "
                   "2020-2023 sample accrued on days when equities were closed "
                   "(weekends and equity holidays). Crypto funds hold these "
                   "coins, so their returns include moves equity investors "
                   "never see.")
        gap = _load_weekend_gap()
        gap_disp = gap[["ticker", "weekend_return_pct", "crypto_only_cum_return",
                        "equity_overlap_cum_return", "full_period_cum_return"]].copy()
        gap_disp["weekend_return_pct"] = gap_disp["weekend_return_pct"].map(
            lambda v: f"{v:.1f}%" if v == v else "n/a")
        gap_disp["crypto_only_cum_return"] = gap_disp["crypto_only_cum_return"].map(_format_pct)
        gap_disp["equity_overlap_cum_return"] = (
            gap_disp["equity_overlap_cum_return"].map(_format_pct)
        )
        gap_disp["full_period_cum_return"] = gap_disp["full_period_cum_return"].map(_format_pct)
        st.dataframe(gap_disp.rename(columns={
            "ticker": "Coin",
            "weekend_return_pct": "Share on equity-closed days",
            "crypto_only_cum_return": "Cum. return on equity-closed days",
            "equity_overlap_cum_return": "Cum. return on equity-trading days",
            "full_period_cum_return": "Total cum. return",
        }), hide_index=True, width="stretch")
        median_gap = gap["weekend_return_pct"].median()
        st.caption(
            f"Across the {len(gap)} coins, a median {median_gap:.1f}% of total "
            f"cumulative return came from days when equities were closed — "
            f"exposure equities simply do not carry."
        )

    st.subheader("How bad can it get? — stress view")
    st.caption("Out-of-sample behaviour of this fund inside three stress "
               "windows (clipped to the fund's live range): the 2022 bear "
               "market, the FTX collapse, and the March 2023 banking stress.")
    stress_rows = []
    for label, start, end in STRESS_EVENTS:
        ev = _event_metrics(fund_ret, start, end)
        stress_rows.append({"Event": label, "Window": f"{start} to {end}",
                            "Cumulative return": ev["cum_return"],
                            "Max drawdown": ev["max_drawdown"],
                            "Worst day": ev["worst_day"]})
    stress_tbl = pd.DataFrame(stress_rows)
    stress_disp = stress_tbl.copy()
    stress_disp["Cumulative return"] = stress_disp["Cumulative return"].map(_format_pct)
    stress_disp["Max drawdown"] = stress_disp["Max drawdown"].map(_format_pct)
    stress_disp["Worst day"] = stress_disp["Worst day"].map(_format_pct)
    st.dataframe(stress_disp, hide_index=True, width="stretch")
    worst_event = stress_tbl.loc[stress_tbl["Max drawdown"].idxmin()]
    st.caption(
        f"The deepest drawdown across these windows was "
        f"{worst_event['Max drawdown']:.1%}, during the {worst_event['Event']}."
    )
    st.pyplot(_stress_chart(fund_ret))

# ---------------------------------------------------------------------------
# Tab 3 - Allocate across funds
# ---------------------------------------------------------------------------
with allocate:
    st.header("Build your allocation")
    returns = _load_fund_returns()
    metrics = _load_metrics()

    alloc_funds = sorted(returns["fund"].unique())
    st.caption("Choose how much of your money goes into each fund. The portfolio "
               "grows a notional $1 from the first date all selected funds trade "
               "together.")
    alloc = {f: 0.0 for f in alloc_funds}
    sliders = st.columns(3)
    for i, f in enumerate(alloc_funds):
        with sliders[i % 3]:
            alloc[f] = st.slider(
                f.replace(" + Sentiment", " (S)"), 0.0, 100.0, 0.0, 5.0, key=f"a_{f}"
            )

    total = sum(alloc.values())
    if total <= 0:
        st.info("Move at least one slider above zero to see the portfolio.")
    else:
        alloc = {f: v / total for f, v in alloc.items()}
        wide = returns.pivot(index="date", columns="fund", values="return").sort_index()
        active = [f for f, v in alloc.items() if v > 0]
        aligned = wide[active].dropna(how="any")
        port_ret = sum(aligned[f] * alloc[f] for f in active)
        port_growth = (1.0 + port_ret).cumprod()

        st.subheader(f"Allocation across {len(active)} fund(s)")
        pie = pd.DataFrame({"fund": active,
                            "weight": [alloc[f] for f in active]}).set_index("fund")
        st.bar_chart(pie, horizontal=True)
        c1, c2 = st.columns(2)
        c1.metric("Portfolio growth of $1",
                  f"${port_growth.iloc[-1]:,.2f}")
        c2.metric("First combined trade date", str(port_growth.index[0].date()))
        st.line_chart(port_growth, height=300)

        # contribution of each fund's Sharpe for context
        m = metrics[metrics["fund"].isin(active)][["fund", "sharpe"]]
        st.caption("Selected fund Sharpe ratios: "
                   + ", ".join(f"{r['fund']} {r['sharpe']:.2f}" for _, r in m.iterrows()))

# ---------------------------------------------------------------------------
# Tab 4 - Sentiment
# ---------------------------------------------------------------------------
with sentiment_tab:
    st.header("News-sentiment analytics")
    sentiment = _load_sentiment()
    fusion_tbl = _load_fusion_table()

    st.subheader("Risk warning gauge")
    st.caption("Where each sector's latest index sits relative to its own "
               "history. Band thresholds are the sector's 25th and 75th "
               "percentiles over the full sample: red = below the 25th (more "
               "negative than usual), amber = inside the central range, green "
               "= above the 75th (more positive than usual). The index is "
               "carry-forwarded on no-headline days and lagged one trading "
               "day.")
    gauge_rows = []
    for sector, grp in sentiment.groupby("sector"):
        grp = grp.sort_values("date")
        latest = grp["sentiment"].iloc[-1]
        lo = grp["sentiment"].quantile(0.25)
        hi = grp["sentiment"].quantile(0.75)
        band = ("Below normal" if latest < lo
                else "Above normal" if latest > hi
                else "Normal range")
        gauge_rows.append({
            "sector": sector,
            "latest_date": grp["date"].iloc[-1].date(),
            "latest_index": latest,
            "band": band,
        })
    gauge = pd.DataFrame(gauge_rows)
    band_color = {"Below normal": "red", "Above normal": "green",
                  "Normal range": "orange"}
    for _, r in gauge.sort_values("sector").iterrows():
        st.markdown(
            f"- **{r['sector']}**: latest index `{r['latest_index']:.3f}` "
            f"({r['latest_date']}) — "
            f"<span style='color:{band_color[r['band']]}'>{r['band']}</span>",
            unsafe_allow_html=True)
    st.bar_chart(gauge.set_index("sector")["latest_index"], height=260)

    st.subheader("Equity sector sentiment index")
    st.caption("VADER-compound scores per headline, equal-weighted to a ticker-day "
               "score and then to a sector-day index; no-headline days carry forward "
               "the last sector score; the signal is lagged one trading day so it is "
               "usable only after publication.")
    sectors = sorted(sentiment["sector"].unique())
    chosen_sector = st.selectbox("Sector", sectors)
    sub = sentiment[sentiment["sector"] == chosen_sector].sort_values("date")
    st.line_chart(sub.set_index("date")["sentiment"], height=280)

    st.subheader("Sentiment tilt — before vs after")
    st.dataframe(fusion_tbl, hide_index=True, width="stretch")
    st.image(str(ROOT / "results" / "figures" / "fusion_before_after.png"),
             caption="Growth of $1: base combined fund vs sentiment-tilted fund")
    st.image(str(ROOT / "results" / "figures" / "sentiment_index.png"),
             caption="Sector sentiment indices over time")
