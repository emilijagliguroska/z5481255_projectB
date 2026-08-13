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
