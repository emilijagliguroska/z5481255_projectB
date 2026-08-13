# AGENTS.md -- Part B -- UNSW StableTrade

## 1. Project Overview

- Part B of the project builds Stations 3 and 4 of the Data Factory Floor (DFF) 
using the Data Foundation from Part A: fund construction, out-of-sample backtesting,
sentiment modelling, structured/unstructured fusion, and the Streamlit app.
- UNSW StableTrade is a minimum-volatility / risk-parity fund concept for risk-averse 
investors seeking equity + crypto exposure with a documented volatility floor and 
drawdown control.
- Project folder: `fins2026/z5481255_projectB/`. All work stays inside it.
- Run the full pipeline: `python scripts/run_part_b.py` from the project root. 
- Run the app: `streamlit run streamlit_app.py`.

Station 3 -- Funds, Backtests & Sentiment:

- A combined equity-plus-crypto fund using at least two optimisation methods 
(e.g. maximum-Sharpe/mean-variance tangency, minimum-variance, risk parity,
equal-weight). Each (asset family, method) pair is one investable fund with its 
own fact sheet -- e.g. "Combined Minimum-Variance."
- A walk-forward, out-of-sample backtest with no look-ahead bias, weights based only 
on past data, and monthly or less frequent rebalancing. The out-of-sample period starts
after the initial estimation window, not the first date in the data.
- A fact sheet for each fund: growth of $1, annualised return, volatility, Sharpe ratio, 
maximum drawdown, and current holdings (target weights from the latest rebalance).
- A VADER (or other) sentiment model scoring assembled headlines and aggregating them into 
a standalone, equal-weighted, lagged sector sentiment index over time.
- Basic sentiment fusion into the equity funds (e.g. a tilt or factor), with a before-vs-after comparison.

Station 4 -- Implementation:

- A Streamlit app supporting the investor journey: compare funds, open a fund's fact sheet, 
set an allocation across funds, read the sentiment analytics.
- The app reads only precomputed `results/` artifacts -- no nltk import or backtest 
recomputation at runtime.
- Deployed from a public GitHub repo at hand-in (private while building); live URL and 
public repo link are both submitted.

## 2. Project Scope

Part B covers fund construction, sentiment modelling, structured/unstructured fusion, and app deployment.

- Station 3: walk-forward out-of-sample backtesting across multiple (asset family, 
method) funds and fund fact sheets, VADER sentiment scoring, lagged sector sentiment index, 
sentiment tilt fusion into equity funds, before-vs-after comparison.
- Station 4: the four-part app journey (compare, fact sheet, allocate, sentiment), 
deployment prep (the assistant can prepare the repo and run `check_handin.py`, but I must use 
my own login to deploy to GitHub/Streamlit).
- Data cleaning, integrity auditing, and descriptive exhibits are Part A's work and are 
reused here, not rebuilt.
- Innovation is rewarded across the whole project, not only in the sentiment 
extension -- for example a wider array of funds/optimisation methods, extending VADER's lexicon, 
a custom figure/design system, a turnover or transaction-cost model, or a genuinely valuable 
app feature. Any such extension must be proposed and approved before implementation (see Section 6).

## 3. Rules

- No look-ahead, anywhere in the pipeline
- Fund weights at each rebalance date use only data available strictly before that date.
- The out-of-sample period starts after the initial estimation window, not on the first date 
in the data -- the first live backtest date and window length must be stated explicitly.
- Sentiment must be lagged at least one trading day relative to the trading day it is 
aligned to: day t's decision uses only sentiment from day t-1 or earlier. A Saturday or 
Monday headline aligned to Monday is first usable for Tuesday's trade. The lag is applied 
once, inside `sector_sentiment_index()` -- no other file applies or duplicates it.

Funds and backtesting:

- At least two optimisation methods for the combined equity+crypto fund; each (asset family, 
method) pair is one fund with its own fact sheet.
- Rebalance monthly or less often (no shorter than ~21 trading days) -- state the exact 
rule used (e.g. first/last trading day of the month, every 21 trading days, quarterly).
- Assume a zero risk-free rate for the Sharpe ratio unless a proxy is explicitly sourced and stated.
- Assume zero transaction costs unless a cost model is added as a stated innovation.
- Any methodology choice not specified by the brief (a covariance estimator, a solver, 
a shrinkage method, a window type) must be proposed with reasoning and approved before 
implementation -- not decided independently and reported afterward.

Sentiment:

- No-headline days use carry-forward at both ticker-day and sector-day levels, after 
reindexing to the full equity trading calendar and before the lag shift. This is chosen because 
sector-level gaps rarely exceed a few trading days even in thin sectors (Materials, Utilities, 
RealEstate), while raw ticker-level gaps can last weeks -- sector-level carry-forward avoids 
that tail risk without a decay mechanism.
- Sentiment tilt in `fusion.py` operates only at sector level, mapped to every ticker in that 
sector -- never at individual ticker level.
- Sentiment applies only to equity data. Crypto has no news coverage and is untouched by 
sentiment tilt (multiplier of 1).
- Raw headline text is never stripped of casing or punctuation before scoring -- VADER relies 
on both. Text-handling choices must be explicitly justified, not silently implemented.

Data (carried forward from Part A, reused not rebuilt):

- Compute crypto returns first on crypto's own 365-day calendar, then left-merge them 
onto the equity trading calendar -- non-equity-trading days are dropped from the merged panel. 
Never merge price levels first and then calculate differences. Any deviation (e.g. folding 
weekend returns into the next equity day) is a methodology change that must be proposed and 
approved before implementation.
- Crypto sample is capped at `date <= 2023-12-31` -- excludes the 10 stray 2024-01-01 rows.
- Normalise timezones before joining news and price data -- news dates are tz-aware (UTC), 
price dates are tz-naive.
- News dedup key is exactly `(ticker, date, title)`. Equity/crypto dedup key is `(ticker, date)`.
- Annualise equity using 252 trading days per year and crypto using 365.

App:

- The app must load only precomputed `results/` CSVs at runtime -- no nltk/VADER import, 
no re-run of the backtest or sentiment scoring inside `streamlit_app.py`. It must run on a 
basic machine within Streamlit Community Cloud's free tier.
- Never commit raw data; only precomputed artifacts under `results/` are committed.

Never modify: `src/data_access.py`, `scripts/check_handin.py`, anything under `context/`, `ai/README.md`, `.gitignore`.

## 4. Verification Constraints (apply to every output)

Before anything goes into the report, code, or app, confirm:

- Every citation points to a real source I have personally opened. If I cannot find it, 
I delete it -- I do not keep references I have not seen.
- Every number traces to the data or a computation I can re-run. No number is included 
because "the AI said so."
- Every factual claim about a company, dataset, or method must be supportable. If not, 
I cut it or clearly mark it as uncertain.
- Code must do what I think it does -- I have run it and checked the actual output, not 
just read the code and assumed it is correct.

The assistant must enforce this:

- Never invent citations, statistics, or sources.
- Flag any claim it cannot verify instead of stating it confidently.
- Show the working for any number it produces -- the computation, not just the result.
- Remind me to check its output before I use it, especially for anything going into the 
report, fact sheets, or figures.

## 5. Coding Conventions

- Integrity checks (`etl.py`): reused unchanged from Part A -- dedup, missing-date audit, 
and per-ticker rolling 63-day standard deviation outlier screen (`|return| / rolling_std > 5`, 
flagged and documented, never deleted). The only Part B-specific addition is the crypto date cap.
- Returns (`features.py`): `daily_returns()` returns wide format (date x ticker) -- `portfolios.py` 
needs this directly for covariance and weight-vector calculations. `assemble_headline_panel()` 
stays in long format, as in Part A, since `sentiment.py` needs individual headline text.
- Sentiment (`sentiment.py`): `score_headlines()` returns raw, unlagged VADER scores at 
headline/ticker-day granularity. `sector_sentiment_index()` performs the equal-weight sector 
average, reindexes to the full equity trading calendar, applies carry-forward, then shifts by 
one trading day as the final step -- this is the single point in the pipeline where lag and fill 
policy are applied.
- Fusion (`fusion.py`): takes the lagged sector index as-is with no further lag. Sector-level 
tilt applied uniformly to every ticker in that sector; weights renormalised to sum to 1 per date 
after the tilt. Report before-vs-after performance using the same fact-sheet metrics as the base funds.
- Portfolios (`portfolios.py`): walk-forward, out-of-sample only -- weights at each rebalance 
date use a rolling estimation window ending strictly before that date and apply through the day 
before the next rebalance. State the first live backtest date and window length explicitly in 
code comments and the report.
- Figure standards: every figure must include a title, caption, labelled axes with units, and 
the sample period on the chart (computed dynamically from the data, never hardcoded). I cannot 
view images -- the assistant must not call a figure "verified" based on generation success or 
numeric checks alone; it must be flagged for my own visual review.
- Use the repo interpreter: `..\..\.venv\Scripts\python.exe` from inside `fins2026/`, or 
`.\.venv\Scripts\python.exe` from the repo root.
- Never commit raw `.parquet` files.


## Code layout 
- `src/` = reusable library code only (no top-level side effects):
  `etl.py` (panels), `features.py` (returns), `sentiment.py` (VADER index),
  `portfolios.py` (solvers + `oos_backtest` + `performance_metrics`),
  `fusion.py` (tilt).
- `scripts/run_part_b.py` = the single end-to-end pipeline. It writes:
  - `results/data/fund_returns.csv`, `results/data/fund_weights.csv`,
    `results/data/sector_sentiment_index.csv`
  - `results/tables/performance_metrics.csv`, `results/tables/fusion_comparison.csv`
  - `results/figures/*.png` (growth-of-$1, drawdown, weights over time,
    Sharpe bar plot, sentiment index, fusion before/after)
- `streamlit_app.py` loads the precomputed CSVs from `results/` with
  `st.cache_data`.
- Returns (`features.py`): `daily_returns()` returns wide format (date x
  ticker) — `portfolios.py` needs this shape for covariance and weights.
  `assemble_headline_panel()` stays long format since `sentiment.py` needs
  individual headline text.

## 6. Workflow and Approval
- I work in stages: the assistant proposes a plan in plain language before any code is written, and implementation happens one file at a time.
- The assistant must stop and wait for an explicit "yes, proceed" or "approved" from me before writing code, running the pipeline, or making further tool calls -- a clarifying answer, an explanation of a permission prompt, or any other response from me is not approval unless I say so explicitly.
- Any methodology decision not fully specified by the brief (a threshold, a covariance method, a merge mechanism, a solver choice, an innovation extension) must be surfaced to me as an explicit decision with reasoning, before it is implemented -- not folded into a later summary as an already-settled fact.
- I log all prompts, AI output, and my corrections in `ai/prompt_log_template.md`.
- I check all sources and citations the assistant provides against the actual brief/data files myself before accepting them, per Section 4.
- When the assistant fixes a bug mid-implementation, it must show me the exact before/after code diff and explain the effect on any already-generated output -- not just report that it was "fixed."
- The assistant cannot view images. It must never describe a figure as verified based on numeric checks alone -- it must explicitly list every figure generated and flag that I need to open and check each one myself before it counts as complete.
- `check_handin.py` passing confirms file structure and required outputs exist -- it does not confirm the underlying analysis or numbers are correct. Passing this check is not a substitute for me reviewing the actual content.
- Final deployment (GitHub push to public repo, Streamlit Community Cloud login and deploy) is my own step -- the assistant may prepare the repo and run `check_handin.py`, but does not have and should not attempt to use my credentials.

## 7. Required Output Files
Data (`results/data/`):
| File | Purpose |
|------|---------|
| `fund_returns.csv` | Out-of-sample daily returns per fund |
| `fund_weights.csv` | Out-of-sample daily weights per fund and ticker |
| `sector_sentiment_index.csv` | Lagged, equal-weighted daily sentiment per sector |

Tables (`results/tables/`):
| File | Purpose |
|------|---------|
| `performance_metrics.csv` | Return, volatility, Sharpe, max drawdown, current holdings per fund |
| `fusion_comparison.csv` | Before-vs-after performance of sentiment-tilted equity funds |

Figures (`results/figures/`): title, caption, labelled axes with units, and sample period required on every figure. Exact filenames and count to be confirmed against `PROJECT_BRIEF.md`'s required exhibit list.

## 8. Report
- Structure: (1) funds and backtest design, (2) out-of-sample results and fund fact sheets, (3) the sentiment index, (4) extensions and innovations, (5) the app and investor journey, (6) critical reflection with three concrete recommendations.
- Max ~10 pages / ~5,000 words of written narrative, excluding appendix and references; required exhibits may go in an appendix.
- Must describe the target user and customer journey.
- Author in Word (`report/report.docx` is the editable source; Markdown drafts are fine as planning aids), submit as `report/report.pdf`.
- Deliverables: the report, full code, the live app URL and public repo link, and the AI workflow pack.


## How to verify work

- Full pipeline (offline): `..\..\.venv\Scripts\python.exe scripts/run_part_b.py`
  with `$env:FINS_DATA_ZIP="C:\Users\zorka\Downloads\project_data.zip"`.
- Unit/smoke tests: `..\..\.venv\Scripts\python.exe -m pytest tests -q`
- Lint: `..\..\.venv\Scripts\python.exe -m ruff check src scripts tests`
- Hand-in gate: `..\..\.venv\Scripts\python.exe scripts/check_handin.py` — fix
  every `[FAIL]`; `[WARN]` items are reminders.
- App smoke check: `streamlit run streamlit_app.py` (bare `python
  streamlit_app.py` only checks it imports and exits cleanly).
- A backtest run is only "done" when every per-date weight row sums to 1.0 and
  `fund_returns.csv` covers only the out-of-sample window.
