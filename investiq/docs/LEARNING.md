# InvestIQ — A Learning & Interview-Prep Companion

> A deep, descriptive walkthrough of the InvestIQ project: what every piece does,
> **why** it was built that way, and the finance + ML + engineering **concepts**
> underneath it. Written so you can revise for an interview by reading top to bottom.
>
> Each major section has three layers:
> - **What** — the concrete thing in this codebase.
> - **Why** — the design reasoning / trade-off.
> - **Concept** — the transferable idea an interviewer might probe.
>
> Code is referenced as `investiq/<path>` relative to the repo root.

---

## Table of Contents

0. [How to read this document](#0-how-to-read-this-document)
1. [Elevator pitch & mental model](#1-elevator-pitch--mental-model)
2. [Trading vs investing — why the distinction matters](#2-trading-vs-investing)
3. [The reference-architecture story (how this was built)](#3-the-reference-architecture-story)
4. [System architecture & data flow](#4-system-architecture--data-flow)
5. [The data layer: sources, TimescaleDB, schema](#5-the-data-layer)
6. [Feature engineering & factor investing](#6-feature-engineering--factor-investing)
7. [The machine-learning core](#7-the-machine-learning-core)
8. [Scoring & the recommendation engine](#8-scoring--the-recommendation-engine)
9. [Portfolio construction & the broker seam](#9-portfolio-construction--the-broker-seam)
10. [Backtesting](#10-backtesting)
11. [The backend API & scheduler](#11-the-backend-api--scheduler)
12. [The frontend](#12-the-frontend)
13. [Engineering practices: the migration & micro-PR workflow](#13-engineering-practices)
14. [How to run & operate it](#14-how-to-run--operate-it)
15. [Limitations, risks & honest caveats](#15-limitations-risks--honest-caveats)
16. [Concept glossary (quick revision)](#16-concept-glossary)
17. [Interview question bank with answers](#17-interview-question-bank)
18. [Possible extensions / roadmap](#18-possible-extensions)
19. [Appendix: file-by-file map](#19-appendix-file-by-file-map)

---

## 0. How to read this document

If you are revising for an interview, read sections **1–4** for the narrative, then
**6, 7, 8** (the analytical heart), then skim **16–17** (glossary + Q&A). If you are
onboarding to build on the project, read **4, 5, 14** and the **appendix** first.

A recurring theme worth internalising: **InvestIQ is fundamentally a "rank a universe
of assets, every period, by an estimate of future risk-adjusted outperformance, then
act on the ranking" system.** Almost every design choice flows from that one sentence.

---

## 1. Elevator pitch & mental model

**InvestIQ is an AI-assisted mutual-fund + equity *investing advisor* for the Indian
market.** It ingests free end-of-day data for a broad universe (Nifty 50 stocks +
~24 mutual funds + the Nifty 50 benchmark), engineers a 21-dimension "factor vector"
for each security, trains a machine-learning model to estimate the probability that a
security will **beat the benchmark over the next ~6 months**, blends that probability
with classic factor/risk/momentum scores into a single 0–1 **conviction score**, maps
that score to a **BUY / HOLD / SELL** action under a chosen risk profile, and lets you
run a **simulated (paper) portfolio** plus a **historical backtest** — all surfaced
through a clean light-themed web dashboard.

### The one-sentence pipeline

```
free data  →  time-series DB  →  factor features  →  ML outperformance model
          →  composite score  →  BUY/HOLD/SELL  →  paper portfolio + backtest
          →  REST API  →  web dashboard
```

### Why this is a good portfolio/interview project

- It touches **the full stack**: data ingestion, a real database, feature
  engineering, supervised ML with proper validation, a scoring/decision system, a
  simulated execution layer, a REST API, and a modern frontend.
- The finance is **defensible** (factor investing, risk-adjusted metrics) rather than
  get-rich-quick hype.
- The ML is **honest** (modest AUC, walk-forward validation, lookahead-aware backtest)
  — which is exactly what a thoughtful interviewer wants to hear about.
- It demonstrates **engineering discipline**: layered architecture, an additive build
  on top of an existing app, and a clean micro-PR git workflow.

---

## 2. Trading vs investing

This distinction is the project's reason for existing, so be ready to articulate it.

| Dimension | Trading (the reference app) | Investing (InvestIQ) |
|---|---|---|
| Holding period | Seconds–hours (intraday options) | Months–years |
| Decision cadence | Every ~30 seconds (live ticks) | Daily / end-of-day |
| Core signal | Short-term price/volume microstructure, option Greeks | Fundamentals, risk-adjusted returns, factor exposure |
| Data needed | Live websocket tick stream | Free EOD prices + NAVs + fundamentals |
| Risk control | Stop-loss / target / trailing per trade | Diversification, position caps, volatility limits |
| ML target | "Will price move +0.1% in 15 minutes?" | "Will this beat the index over 6 months?" |
| Failure mode | Slippage, latency, fat tails | Style drift, value traps, regime change |

**Why it matters:** because the cadence is daily, InvestIQ does **not** need a live
websocket feed, a tick collector, or a 30-second scanner (all of which the reference
trading app has). That single fact removes ~40% of the original system's complexity and
replaces a real-time streaming architecture with a once-a-day batch job. Recognising
that "the data cadence dictates the architecture" is a strong systems-design point.

---

## 3. The reference-architecture story

InvestIQ was **not** written from a blank page. It reused the *skeleton* of an existing
intraday options paper-trading system (the "AI-trader" reference) and swapped the
domain. The reusable skeleton — and this is the transferable lesson — is:

```
ingest → time-series store → feature engine → ML train/score → ranked output
       → (simulated) execution → REST API → dashboard
```

Roughly **60–70% of any such system is domain-agnostic plumbing.** Only the
domain-specific middle changed:

| Layer | Reference (trading) | InvestIQ (investing) |
|---|---|---|
| DB access pattern | `read_sql / write_df / upsert` | reused almost verbatim |
| Risk profiles | dataclasses (SL/target/lot) | dataclasses (thresholds/weights/caps) |
| Feature engine | 58 technical indicators | 21 factor features |
| ML harness | XGBoost + walk-forward | reused; new labels |
| Scoring | weighted composite | weighted composite (new components) |
| Execution | order manager + broker adapter | paper portfolio + broker seam |
| Backend | Flask + SSE + 30s scanner | Flask + daily scheduler (no SSE) |
| Frontend | Next.js retro-terminal theme | Next.js modern light theme |

**Concept — "skeleton reuse":** when interviewing, frame this as recognising that a
production system's *architecture* is more reusable than its *business logic*. You kept
the proven plumbing and rewrote the thin domain layer, which is faster and lower-risk
than greenfield.

---

## 4. System architecture & data flow

### 4.1 Tech stack

| Layer | Technology | Why |
|---|---|---|
| Database | TimescaleDB (PostgreSQL 17) on Docker, port 5440 | time-series-optimised Postgres; daily bars/NAVs fit its hypertable model |
| ORM / access | SQLAlchemy core + psycopg2 | thin, explicit SQL; no heavy ORM |
| Data sources | `api.mfapi.in`, `yfinance`, (AMFI) | free, no credentials |
| Feature/ML | pandas, NumPy, scikit-learn, XGBoost | industry-standard tabular ML |
| Model persistence | joblib `.pkl` + a `model_registry` table | reproducible, versioned |
| Backend | Flask + flask-cors + APScheduler | small REST API + daily cron |
| Frontend | Next.js 16, React 19, Tailwind v4, Recharts, lucide-react | modern, fast, charts |
| Runtime | Windows + Python venv + Node | dev box |

### 4.2 The layered directory map

```
investiq/
├── config/         settings.py (constants), risk_profiles.py, universe.py
├── utils/          logger.py
├── data/           mfapi_adapter.py, yfinance_adapter.py, ingest.py, mock_data.py
├── database/       db.py (access layer), schema.sql
├── features/       factor_engine.py
├── models/         train_model.py, predict.py
├── strategy/       scorer.py, recommendation_engine.py
├── portfolio/      broker_adapter.py, paper_portfolio.py, rebalancer.py
├── backtest/       backtest_engine.py
├── backend/        app.py (Flask API)
├── scheduler/      daily_refresh.py (APScheduler job)
├── frontend/       Next.js dashboard (app/, components/, lib/)
└── main.py         CLI entry: mock | ingest | train | backtest | recommend | serve
```

**Concept — layered / hexagonal architecture:** each directory is a layer with a single
responsibility, and dependencies point *inward* (frontend → API → strategy/portfolio →
models/features → data → db). You can test or replace any layer without touching the
others. The `broker_adapter` is a deliberate **port/seam** so a real broker can be
slotted in behind the same interface.

### 4.3 End-to-end data flow (the daily lifecycle)

1. **Ingest** (`data/ingest.py`): pull recent prices/NAVs/fundamentals → upsert into DB.
2. **Featurise** (`features/factor_engine.py`): recompute the 21-factor vectors from the
   raw series → store in `features`.
3. **Predict** (`models/predict.py`): the trained model assigns P(outperform) to each
   security's latest feature row.
4. **Score** (`strategy/scorer.py`): blend ML prob with cross-sectional factor/risk/
   momentum percentiles → `final_score`.
5. **Recommend** (`strategy/recommendation_engine.py`): apply risk-profile thresholds +
   gates → BUY/HOLD/SELL → store in `recommendations`.
6. **Act** (`portfolio/rebalancer.py`): optionally rebalance the paper portfolio toward
   the top recommendations.
7. **Serve** (`backend/app.py`): expose everything over REST; the dashboard renders it.

Steps 1–5 are wrapped by the **APScheduler daily job** (`scheduler/daily_refresh.py`),
which runs at 18:30 (after Indian market close + EOD NAV publication).

---

## 5. The data layer

### 5.1 Free data sources

**What.** InvestIQ deliberately uses only free / delayed data:

- **Mutual fund NAVs** — `https://api.mfapi.in/mf/<schemeCode>` returns the *full* daily
  NAV history of a scheme plus metadata (fund house, category). The endpoint
  `https://api.mfapi.in/mf` lists ~37k schemes. `data/mfapi_adapter.py` fetches the list
  once, then `resolve_scheme()` matches a human name like "Parag Parikh Flexi Cap" to a
  concrete scheme code, **preferring Direct-Growth plans** (lower expense ratio, no
  payout distortions).
- **Equities & indices** — `yfinance` (Yahoo Finance) with the `.NS` suffix for NSE
  tickers (`RELIANCE.NS`) and `^NSEI` for the Nifty 50. We pull EOD OHLCV history and a
  best-effort fundamentals snapshot (PE, PB, ROE, debt/equity, dividend yield, sector).

**Why.** Real-time market data is expensive and unnecessary for a months-horizon
advisor. Free EOD data is sufficient and keeps the project reproducible by anyone.

**Concept — "Direct vs Regular" / "Growth vs IDCW":** Indian mutual funds have *Direct*
plans (bought without a distributor; lower expense ratio) and *Regular* plans, plus
*Growth* (reinvests gains) vs *IDCW* (pays out, which creates artificial NAV drops).
For analysis you always want **Direct-Growth** so the NAV series reflects pure
compounding. The resolver encodes this preference.

### 5.2 Why a time-series database (TimescaleDB)

**What.** TimescaleDB is a PostgreSQL extension that turns ordinary tables into
**hypertables** — tables automatically partitioned by a time column into "chunks."

**Why.** Our biggest tables (`price_history`, `nav_history`) are append-mostly,
time-ordered, and queried by ranges ("last 750 days for symbol X"). Hypertables make
those inserts and range scans fast as the data grows, while still being plain SQL.

**Concept — hypertable & chunking:** a hypertable looks like one table but is physically
many child tables split by time interval (we use 90-day chunks). Benefits: (1) inserts
touch only the latest chunk; (2) time-range queries prune irrelevant chunks; (3) old
chunks can be compressed/dropped. You get this with a single
`create_hypertable('price_history','date', chunk_time_interval => INTERVAL '90 days')`.

**Interview nuance:** for *this* dataset (a few hundred thousand daily rows) plain
Postgres would be perfectly fine — TimescaleDB is reused from the reference app and is
"right-sized for growth," not strictly required. Being able to say *"I know it's
over-provisioned for the current scale, and here's when it would start to matter"* shows
judgement.

### 5.3 The schema (`database/schema.sql`)

| Table | Purpose | Key | Hypertable? |
|---|---|---|---|
| `securities` | master list (symbol, name, type, category, fund house, benchmark, scheme code) | `symbol` | no |
| `nav_history` | daily mutual-fund NAVs | (`date`,`scheme_code`) | yes |
| `price_history` | daily equity/index OHLCV | (`date`,`symbol`) | yes |
| `fundamentals` | PE/PB/ROE/etc. snapshots | (`date`,`symbol`) | no |
| `features` | the 21-factor vectors per security/date | (`date`,`symbol`) | yes |
| `recommendations` | BUY/HOLD/SELL with sub-scores + rationale | (`date`,`symbol`) | no |
| `portfolio_transactions` | append-only paper trades | `id` | no |
| `portfolio_snapshots` | daily portfolio value (equity curve) | (`date`,`mode`) | no |
| `model_registry` | trained-model metadata (AUC, n_samples, path) | `id` | no |

**Concept — why composite primary keys?** `(date, symbol)` makes each row idempotent:
re-ingesting the same day can't create duplicates. TimescaleDB also *requires* the time
column to be part of any unique index on a hypertable.

### 5.4 The DB access layer (`database/db.py`)

Everything goes through four helpers — never raw psycopg2 in business code:

- `read_sql(query, params)` → DataFrame.
- `write_df(df, table)` → bulk insert.
- `upsert_rows(df, table, conflict_cols, update=False)` → the workhorse.
- `init_db()` → runs `schema.sql` (idempotent).

**`upsert_rows` and `ON CONFLICT`.** This wraps PostgreSQL's
`INSERT ... ON CONFLICT (cols) DO NOTHING|DO UPDATE`. With `update=False` it ignores
rows that already exist (perfect for idempotent backfills); with `update=True` it
refreshes the non-key columns (used for fundamentals/features that change). 

**Concept — idempotency:** an operation is idempotent if running it twice has the same
effect as running it once. Upserts make ingestion safe to re-run after a crash or a
partial download — a property you want in *any* data pipeline.

> **War story baked into the code:** `init_db()` originally split `schema.sql` on `;`
> and ran each statement in one shared transaction. A semicolon *inside an SQL comment*
> split a statement mid-way, the first statement errored, and because all statements
> shared one transaction, **every** subsequent statement failed with "transaction is
> aborted." Fix: strip full-line comments *before* splitting, and run each statement in
> **autocommit** so one failure can't poison the rest. Lesson: naive SQL splitting is a
> classic footgun; comments and dollar-quoted bodies break it.

### 5.5 Ingestion (`data/ingest.py`)

`run_ingest()` orchestrates: benchmark → equities (+fundamentals) → funds. Each fetch is
wrapped in try/except so one bad ticker doesn't abort the run. `refresh()` is the
lightweight daily variant (`period="1mo"`) that relies on upsert dedup. `--sample` mode
ingests a tiny subset for fast iteration.

**Concept — graceful degradation:** external APIs are flaky. The ingester logs and skips
a failed symbol rather than crashing, and `yfinance`'s notoriously unreliable `.info`
call is treated as best-effort (missing fundamentals become `NaN`, which the ML model
tolerates natively).

---

## 6. Feature engineering & factor investing

This is the analytical heart, and the richest interview territory. `features/factor_engine.py`
turns a raw price/NAV series into a **21-number factor vector** per security per date.

### 6.1 What is "factor investing"?

**Concept.** A *factor* is a measurable characteristic that has historically explained
differences in asset returns. Decades of academic + practitioner research converged on a
handful of robust factors:

- **Value** — cheap assets (low PE/PB) tend to outperform expensive ones long-term.
- **Quality** — profitable, low-debt, stable companies (high ROE, low debt/equity)
  outperform junk.
- **Momentum** — assets that did well over the past 3–12 months tend to keep doing well
  over the next few months (with a 1-month reversal skip).
- **Low volatility** — counter-intuitively, lower-volatility assets have historically
  delivered *better* risk-adjusted returns than high-volatility ones.

InvestIQ's 21 features are organised around exactly these families plus plain return and
risk descriptors. The model then learns *how to weight them*, while the scorer applies a
sensible hand-set blend.

### 6.2 The 21 features, defined

Let `P_t` be the price/NAV on day `t`, `r_t = P_t/P_{t-1} − 1` the daily return, and
`b_t` the benchmark's value. `RF` is the annual risk-free rate (6.5%), `TD = 252`
trading days/year.

**Returns (5)** — momentum/trend descriptors:
- `ret_1m`, `ret_3m`, `ret_6m`, `ret_1y` = `P_t / P_{t−k} − 1` for k = 21, 63, 126, 252.
- `cagr_3y` = `(P_t / P_{t−756})^(1/3) − 1` — compound annual growth over 3 years.

**Risk (7):**
- `volatility` = `std(r over 252d) × √252` — annualised standard deviation of returns.
  *Concept:* volatility is the standard measure of how much returns bounce around;
  annualising by √time assumes returns are roughly i.i.d.
- `downside_dev` = std of only the *negative* daily returns, annualised. *Concept:* plain
  volatility penalises big *up* moves too; downside deviation only counts the bad ones,
  which is what investors actually fear.
- `sharpe` = `(annualised_return − RF) / volatility`. *Concept:* the **Sharpe ratio** is
  excess return per unit of total risk — the single most-quoted risk-adjusted metric.
- `sortino` = `(annualised_return − RF) / downside_dev`. *Concept:* like Sharpe but
  divides by downside deviation, so it doesn't punish upside volatility.
- `max_drawdown` = the worst peak-to-trough decline over the trailing year, i.e.
  `min(P_t / running_max − 1)`. *Concept:* drawdown is the most *visceral* risk measure —
  "how much would I have been down at the worst point?" A −50% drawdown needs a +100%
  gain to recover.
- `beta` = `cov(r, b) / var(b)` over 252 days. *Concept:* **beta** measures sensitivity
  to the market. β=1 moves with the index; β=1.3 amplifies it; β<1 is defensive.
- `alpha` = annualised `mean(r) − RF_daily − β·(mean(b) − RF_daily)`. *Concept:* **alpha**
  is the return *not explained by market exposure* — the holy grail of active management.
  Positive alpha = genuine skill/edge after accounting for how much market risk you took.

**Momentum / trend (4):**
- `momentum_12_1` = `P_{t−21} / P_{t−252} − 1` — the classic "12-month return excluding
  the most recent month." *Concept:* the 1-month skip avoids short-term *reversal* noise.
- `dist_200dma` = `P_t / SMA_200 − 1` — distance above/below the 200-day moving average,
  a widely-watched long-term trend gauge.
- `dist_52w_high` = `P_t / max(P over 252d) − 1` — how far below the 52-week high (≤ 0);
  closer to 0 = stronger.
- `consistency` = fraction of the last 252 days on which the security's trailing-3-month
  return beat the benchmark's. *Concept:* a "win-rate vs benchmark" — rewards steady
  outperformers over lucky one-shot spikes.

**Fundamentals (5)** — equity quality/value (NaN for funds):
- `pe` (price/earnings), `pb` (price/book), `roe` (return on equity), `debt_equity`,
  `div_yield`.

### 6.3 Point-in-time computation & avoiding lookahead

**What.** All rolling features use only data up to date `t` (pandas `.rolling(252)`,
`.shift(k)`). Features are then **sampled monthly on real trading dates** (every ~21
rows), always including the latest date.

**Why / Concept — lookahead bias:** the cardinal sin of quant research is letting future
information leak into a feature or label used to "predict" the past. If your "feature"
for January secretly used February's price, your backtest will look brilliant and your
live trading will fail. Every rolling window here is strictly backward-looking.

**The honest simplification.** Free data only gives us *today's* fundamentals (yfinance
doesn't serve historical PE/ROE). So the latest fundamentals snapshot is **broadcast
across a security's history**. This is a mild, *documented* lookahead on the 5
fundamental features. The price-derived 16 features are fully point-in-time. Being able
to name this trade-off — and say how you'd fix it (a paid fundamentals history, or
point-in-time fundamental vendors) — is exactly the kind of intellectual honesty
interviewers reward.

---

## 7. The machine-learning core

### 7.1 Problem framing

**What.** A **supervised binary classification** problem: given a security's factor
vector today, predict whether it will **beat its benchmark over the next ~126 trading
days (≈6 months)**.

**Concept — framing matters more than the algorithm.** Note the target is *relative*
(beat the benchmark), not absolute (go up). In a bull market almost everything goes up;
the useful question is "which will go up *more than the index*?" Relative targets also
neutralise market-wide regime effects, making the label more stationary.

### 7.2 Labelling (`train_model.attach_labels`)

For each feature row at date `t`:
```
security_fwd = P_{t+126} / P_t − 1
benchmark_fwd = b_{t+126} / b_t − 1
label = 1 if (security_fwd − benchmark_fwd) > margin else 0   # margin = 0
```
Rows without 126 future days available are dropped (you can't label the most recent ~6
months yet).

**Concept — horizon & margin are hyperparameters.** A longer horizon = smoother, slower
signal; a shorter horizon = noisier. The `margin` sets how much outperformance "counts."
Here margin = 0 (any outperformance), which in the sample gave a **65% positive rate** —
unusually high because the trailing window was a broad up-market. You'd tune margin to
control class balance and how selective the label is.

### 7.3 The model: XGBoost

**What.** An `XGBClassifier` (gradient-boosted decision trees): 300 trees, depth 4,
learning rate 0.05, subsample/colsample 0.8, `scale_pos_weight` set from class balance.

**Concept — gradient boosting.** Boosting builds an ensemble of *weak* learners
(shallow trees) **sequentially**, where each new tree is trained to correct the residual
errors of the ensemble so far, using gradient descent on a loss function (logloss here).
Compared with a single deep tree it generalises far better; compared with random forests
(which average independent trees) boosting usually wins on tabular data. XGBoost adds
regularisation, handles missing values natively (important — our funds have NaN
fundamentals), and is fast.

**Why depth 4 & subsampling?** Shallow trees + row/column subsampling are
**regularisation** — they limit how much any single tree can memorise, reducing
overfitting. The train accuracy (~0.86) being much higher than the cross-validated AUC
(~0.60) is the tell-tale gap that says "the model fits training data well but the *honest*
out-of-sample signal is modest" — which is normal and expected for 6-month return
prediction.

### 7.4 Validation: walk-forward (`TimeSeriesSplit`)

**What.** `_walk_forward_auc()` uses scikit-learn's `TimeSeriesSplit` (expanding window):
train on the past, test on the immediately following block, repeat, average the AUC.

**Why / Concept — never shuffle time series.** A random train/test split leaks the future
into the past (you'd train on December to predict June). **Walk-forward** validation
respects the arrow of time: every test set is strictly *after* its training set, exactly
mimicking how the model is used live. This is the single most important methodological
point in financial ML.

```
Split 1:  train [........]  test [==]
Split 2:  train [..........]  test [==]
Split 3:  train [............]  test [==]
```

### 7.5 Class imbalance: `scale_pos_weight`

**Concept.** When one class dominates (say 65/35), a naive model can score well by always
predicting the majority. `scale_pos_weight = n_negative / n_positive` tells XGBoost to
weight the minority class more in the loss, so it actually learns to separate the classes
rather than predicting the prior.

### 7.6 The metric: AUC

**Concept — ROC-AUC.** The area under the ROC curve is the probability that the model
ranks a random *positive* example above a random *negative* one. 0.5 = coin flip, 1.0 =
perfect. We use AUC (not accuracy) because (a) it's threshold-independent — we care about
*ranking* securities, not a hard yes/no — and (b) it's robust to class imbalance. Our
**~0.595** means a real but modest edge: the model ranks future outperformers above
underperformers ~60% of the time. For a 6-month horizon on noisy markets, that's
believable and *not* over-fit; anything near 0.8 would be a red flag for leakage.

### 7.7 Persistence, registry, backups, prediction

- The trained bundle (`model`, `features`, `metrics`) is saved with **joblib** to
  `models/saved/outperformance_model.pkl` (gitignored — regenerate with `main.py train`).
- Before overwriting, the old model is **timestamp-backed-up** under `models/saved/backups/`.
- A row is written to `model_registry` (AUC, accuracy, n_samples, path) — a lightweight
  **model registry / experiment-tracking** pattern.
- `models/predict.py:Predictor` loads the bundle and exposes `predict_proba(features)`,
  returning a neutral **0.5** if no model exists yet (**graceful fallback** so the rest of
  the system runs before training).

---

## 8. Scoring & the recommendation engine

### 8.1 Cross-sectional percentile ranking (`strategy/scorer.py`)

**What.** For one snapshot (all securities on a date), each sub-factor is converted to a
**percentile rank across the universe** (pandas `.rank(pct=True)`), then averaged into
three sub-scores:
- `factor_score` = mean of {ROE↑, low-PE, low-PB, low-debt, consistency↑}.
- `risk_score` = mean of {Sharpe↑, Sortino↑, low-vol, shallow-drawdown}.
- `momentum_score` = mean of {6m return↑, 1y return↑, 12-1 momentum↑, near-52w-high}.

**Why / Concept — cross-sectional vs time-series normalisation.** We rank securities
*against each other on the same day* rather than against their own history. This makes the
scores directly comparable for building a *ranked list* and is naturally robust to
market-wide moves (if everything falls, the relative ranking still distinguishes the
better names). Percentiles also tame outliers — a stock with an absurd PE just lands at
rank 1.0 instead of blowing up an average.

### 8.2 The composite score

```
final_score = 0.45·ML_prob + 0.25·factor + 0.15·risk + 0.15·momentum     (all in [0,1])
```

**Why these weights?** ML gets the largest weight (it's the learned, holistic signal) but
not a majority — so a single model quirk can't dominate, and the interpretable factor/
risk/momentum scores keep the system sensible and explainable. This is a deliberate
**ensemble of a learned model + rule-based scores**, which is more robust and far easier
to explain to a user (or interviewer) than a black box alone.

### 8.3 Risk profiles (`config/risk_profiles.py`)

Three immutable dataclasses controlling selectivity and portfolio shape:

| Profile | buy / hold / sell | max holdings | max weight | equity target | max vol | cash buffer |
|---|---|---|---|---|---|---|
| Conservative | 0.60 / 0.50 / 0.45 | 15 | 10% | 40% | 30% | 10% |
| Balanced | 0.56 / 0.46 / 0.40 | 12 | 15% | 60% | 45% | 5% |
| Aggressive | 0.52 / 0.40 / 0.35 | 8 | 25% | 80% | 75% | 2% |

**Concept — risk appetite as configuration.** Conservative = more holdings, smaller
positions, lower volatility cap, more cash → diversified and defensive. Aggressive =
fewer, larger, higher-vol positions → concentrated and growth-tilted. Encoding the entire
risk personality as a frozen dataclass keeps the decision logic generic.

### 8.4 Mapping score → action (`recommendation_engine.py`)

For each security (INDEX excluded — you can't directly buy the raw index):
1. Compute `final_score`.
2. **Gates:** reject a BUY if volatility > profile cap (Sharpe gate is intentionally
   lenient — see the war story below).
3. **Thresholds:** `≥ buy` → BUY (or HOLD if already held); `≥ hold` → HOLD; else SELL.
4. **Holding-aware:** the engine takes the current paper holdings so names you already
   own surface as HOLD rather than BUY.
5. Attach a human **rationale** ("ML 90%, strong momentum, quality/value").

> **War story — the Sharpe gate that zeroed everything.** The first version hard-gated
> BUYs on an *absolute* `min_sharpe` (e.g. 0.3). But the trailing year was a drawdown
> period where **most securities had negative Sharpe**, so the gate filtered *everything*
> → zero BUYs. Fix: recognise that absolute risk floors are *regime-dependent and
> brittle*; the **cross-sectional `risk_score` already captures relative risk quality**,
> so the hard floor was relaxed to be permissive and the thresholds recalibrated to the
> real score distribution. Lesson: prefer *relative* gates over *absolute* ones in a
> ranking system, and always sanity-check that your filters don't degenerate.

---

## 9. Portfolio construction & the broker seam

### 9.1 The broker seam (`portfolio/broker_adapter.py`)

**What.** An abstract `BrokerAdapter` with `place_order()` / `transactions()`, a concrete
`PaperBroker` (records simulated trades to `portfolio_transactions`), and a `LiveBroker`
**stub** that raises `NotImplementedError`.

**Why / Concept — the adapter / port-and-adapter (hexagonal) pattern.** All portfolio and
rebalance logic depends on the *interface*, never on a concrete broker. To go live later,
you implement `LiveBroker` against a real brokerage API and swap it in — nothing else
changes. This is the textbook way to keep a risky external dependency (real money!)
isolated behind a seam, and it lets you develop/test entirely on the safe paper path.

### 9.2 The paper portfolio (`portfolio/paper_portfolio.py`)

Computes, from the append-only transaction log:
- **Holdings:** net units per symbol, **average cost**, market value, P&L, and **weight**.
- **Cash:** `initial_capital − Σ buys + Σ sells`.
- **Summary:** total value, invested, cash, P&L, P&L %.
- **Snapshot:** writes today's total value to `portfolio_snapshots` (the equity curve).

**Concept — average-cost basis & weights.** Average cost = total amount spent / total
units bought; unrealised P&L = (current price − avg cost) × units. A position's *weight*
is its value ÷ portfolio value — the number that actually controls risk concentration.
(A stricter system would use FIFO lots for tax-accurate realised P&L; average cost is the
pragmatic simplification here.)

A safety rail: `buy()` never spends more than available cash — a small but important
guard against negative balances.

### 9.3 The rebalancer (`portfolio/rebalancer.py`)

`rebalance(risk_level)`:
1. Get current BUY recommendations, take the top `max_holdings`.
2. Compute **score-weighted target weights**, **capped** at `max_holding_weight`, then
   renormalised; invest `total_value × (1 − cash_buffer)`.
3. **Sell first** (free up cash): exit non-target holdings, then trim overweight targets.
4. **Then buy** underweight/new targets toward their target value.
5. Snapshot the portfolio.

**Concept — rebalancing & the sell-then-buy ordering.** Rebalancing moves the portfolio
back to its intended target weights as prices drift. Selling before buying guarantees the
cash is available for the buys (a real-world settlement concern). Score-weighting tilts
more capital toward higher-conviction names; the per-name cap enforces diversification so
no single bet dominates.

---

## 10. Backtesting

### 10.1 What a backtest is

**Concept.** A backtest simulates a strategy on historical data to estimate how it
*would* have performed. The output is an **equity curve** (growth of ₹1 over time) plus
summary metrics. It is the primary evidence that a strategy has an edge — and the easiest
thing in finance to accidentally fake via lookahead.

### 10.2 InvestIQ's backtest (`backtest/backtest_engine.py`)

A **monthly-rebalanced, equal-weight, top-N factor strategy** vs the Nifty 50:
1. Build a clean **monthly schedule** from the benchmark's month-end trading days.
2. At each month-end, take each security's **as-of** feature row (latest on/before that
   date — no future leakage).
3. Score them by the **factor/risk/momentum composite *excluding ML*** and pick the top N.
4. Hold equal-weight for one month; compute each pick's realised forward-month return.
5. Compound into the strategy equity curve; do the same for the benchmark.

**Why exclude ML from the backtest?** The ML model is trained on the *entire* history, so
using it inside a historical backtest would be **lookahead** (the model "knows" the
future relative to backtest dates). Dropping ML and backtesting only the point-in-time
factor scores keeps the backtest *honest*. (A fully rigorous version would retrain the
model walk-forward at each rebalance — heavier, and a clear next step.)

### 10.3 Results & metrics

On the sample universe the balanced profile produced roughly:
- **CAGR ≈ 13.8%** vs benchmark **≈ 8.8%** → **alpha ≈ +5%/yr**.
- **Volatility ≈ 14.5%**, **Sharpe ≈ 0.50**, **max drawdown ≈ −17.5%**, over ~61 months.

**Concept — reading these numbers.** CAGR is the smoothed annual growth rate. Beating the
benchmark by ~5%/yr with a similar drawdown is a *plausible, not magical* factor edge —
exactly what you'd want to present honestly.

### 10.4 The backtest pitfalls this project is aware of

- **Lookahead** — addressed via as-of features and ML exclusion.
- **Survivorship bias** — the Nifty 50 list is *today's* membership; historically some
  constituents differed. This inflates results and is a known limitation.
- **No transaction costs / slippage / taxes** — real returns would be lower.
- **Small universe & single period** — not statistically bulletproof; it's a demo.

Naming these unprompted is a strong interview signal.

---

## 11. The backend API & scheduler

### 11.1 Flask REST API (`backend/app.py`, port 5055)

| Route | Returns |
|---|---|
| `GET /api/health` | status, model_loaded, row counts |
| `GET /api/risk/profiles` | the three profiles |
| `GET /api/securities` | the tracked universe |
| `GET /api/recommendations?risk=` | ranked BUY/HOLD/SELL (holding-aware) |
| `GET /api/screener?risk=&sec_type=&action=&min_score=` | filterable scored universe |
| `GET /api/security/<symbol>` | price/NAV history, features, recommendation, fundamentals |
| `GET /api/portfolio` | summary + holdings |
| `POST /api/portfolio/buy` `\|` `sell` `\|` `rebalance` | paper actions |
| `GET /api/portfolio/history` | equity-curve snapshots |
| `GET /api/market/overview` | benchmark level, 1d/1m change, BUY/HOLD/SELL breadth |
| `GET /api/backtest?risk=` | cached metrics + equity curve |

A small helper serialises DataFrames to JSON safely (`df.to_json(orient="records",
date_format="iso")`) to avoid NumPy/`datetime` serialisation errors.

### 11.2 No SSE — a daily scheduler instead (`scheduler/daily_refresh.py`)

**What.** APScheduler runs `daily_update()` once a day at 18:30: refresh data → rebuild
features → regenerate recommendations for all three profiles.

**Why / Concept — cadence dictates the mechanism.** The reference trading app streamed
updates over **Server-Sent Events** every second because prices changed every second.
InvestIQ's data changes **once a day**, so a streaming channel would be pure waste; a
scheduled batch job is the correct, simpler tool. Choosing the mechanism that matches the
data's rate of change is a clean systems-design instinct.

---

## 12. The frontend

### 12.1 Stack & structure

Next.js 16 (App Router) + React 19 + Tailwind v4 + Recharts + lucide-react. Pages live in
`frontend/app/*/page.tsx`; shared UI in `components/`; the typed API client in `lib/api.ts`.

- `/` Dashboard — portfolio value, market breadth, strategy-vs-Nifty equity chart, top
  recommendations.
- `/ideas` — recommendations with risk + action filters and score bars.
- `/portfolio` — holdings, summary, **Rebalance** + per-row **Sell**.
- `/screener` — filterable scored universe.
- `/security/[symbol]` — price/NAV chart, factor table, fundamentals, paper **Buy**.
- `/backtest` — risk selector, metric cards, equity curve.
- `/settings` — risk-profile table + system status.

### 12.2 Key frontend concepts

- **App Router & Server vs Client Components.** Next's App Router renders components on the
  server by default; interactive pages opt in with `"use client"` (needed for `useState`/
  `useEffect`/event handlers). Our data pages are client components that fetch on mount.
- **The `/api` rewrite proxy.** `next.config.ts` rewrites `/api/*` → `http://localhost:5055`.
  The browser calls *same-origin* `/api/...`, Next proxies to Flask — so no CORS dance and
  the API base never gets hard-coded into the client.
- **Tailwind v4 + design tokens.** A small set of CSS variables (`--primary`, `--positive`,
  `--negative`, radii, shadows) defines the *modern fintech light* theme — a deliberate
  replacement of the reference app's dark "retro-terminal" look. Centralising tokens means
  a re-theme is a few-line change.
- **Recharts** renders the equity curves and price charts declaratively from the JSON the
  API returns.

**Concept — the data contract.** `lib/api.ts` defines TypeScript interfaces
(`Recommendation`, `Holding`, `PortfolioSummary`, …) that mirror the Flask responses.
This typed boundary is the *contract* between frontend and backend; if the API shape
changes, TypeScript flags every break at compile time.

---

## 13. Engineering practices

### 13.1 The migration story

InvestIQ was built **additively** inside the personal `Trader-Ai` repo (a fork of the
trading app + UI tweaks) on a dedicated **`migration`** branch, leaving `main` untouched.
Everything lives under `investiq/` so the original trading app keeps working — "build the
new thing alongside, swap later" rather than a risky in-place rewrite.

### 13.2 The micro-PR workflow

Every increment followed: **create a GitHub issue → branch off `migration` → make the
change → one-line commit → open a PR into `migration` → merge → delete the branch → close
the issue.** Commits are single-line, no description, no co-author.

**Why / Concept — small, reversible increments.** Micro-PRs make each change easy to
review, bisect, and roll back. A bug is isolated to one small PR instead of buried in a
500-file mega-commit. (A subtlety learned here: `Closes #N` only auto-closes an issue when
the PR merges into the repo's *default* branch — since these targeted `migration`, issues
were closed manually.)

The whole system landed across ~12 such PRs: scaffold → DB → mock data → ingestion →
features → ML → scoring → portfolio/backtest → API → frontend (×2) → docs.

---

## 14. How to run & operate it

**Prerequisites:** Docker (for TimescaleDB), Python (reuses the reference `.venv`), Node.

```bash
# 0. Start the database (TimescaleDB in Docker on host port 5440)
docker start aitrader-timescaledb          # first time: docker run ... -p 5440:5432 timescale/timescaledb

# 1. One-time / periodic data + model build  (run from investiq/)
PYTHONUTF8=1 <python> main.py ingest        # pull the universe from free sources
PYTHONUTF8=1 <python> main.py train         # build features + train the model
PYTHONUTF8=1 <python> main.py recommend      # print today's BUYs
PYTHONUTF8=1 <python> main.py backtest       # backtest vs Nifty, save equity curve

# 2. Serve
PYTHONUTF8=1 <python> backend/app.py         # Flask API on :5055 (+ daily scheduler)
cd frontend && npm install && npm run dev -- -p 3001   # dashboard on :3001
```

> **Windows note:** always run Python with `PYTHONUTF8=1`. The code prints the ₹ symbol
> (U+20B9), which Windows' default cp1252 codec can't encode — UTF-8 mode fixes it.

CLI modes in `main.py`: `mock` (offline synthetic data), `ingest`, `train`, `backtest`,
`recommend`, `serve`. `mock` is the way to exercise the whole pipeline with **no network
and no real data** — the synthetic-universe generator (`data/mock_data.py`) mirrors the
real schema.

---

## 15. Limitations, risks & honest caveats

A mature engineer leads with these, not away from them:

1. **Modest predictive power.** Walk-forward AUC ≈ 0.60. Real, but not a money printer.
2. **Fundamentals lookahead.** Current fundamentals are broadcast across history (free-data
   limitation). Price-based features are clean.
3. **Survivorship bias** in the universe (today's Nifty 50 membership applied historically).
4. **No costs/slippage/taxes** in the backtest → real returns lower.
5. **High label positive rate (65%)** reflects a bull sample window; the label/margin would
   be tuned across regimes.
6. **Small universe, single market, single period** — a demo, not a validated product.
7. **Not investment advice / not SEBI-registered.** It's an educational paper system.
8. **Average-cost (not FIFO) accounting** — fine for P&L display, not tax-accurate.

---

## 16. Concept glossary

Quick-revision definitions you should be able to give in one breath:

- **Factor** — a measurable attribute (value/quality/momentum/low-vol) that explains
  cross-sectional return differences.
- **Alpha** — return beyond what market exposure (beta) explains; "skill."
- **Beta** — sensitivity to the market; 1 = moves with index.
- **Volatility** — annualised standard deviation of returns; total risk.
- **Downside deviation** — std of only negative returns; "bad" risk.
- **Sharpe ratio** — excess return ÷ volatility; risk-adjusted return.
- **Sortino ratio** — excess return ÷ downside deviation.
- **Max drawdown** — worst peak-to-trough loss; visceral risk.
- **CAGR** — compound annual growth rate.
- **Momentum (12-1)** — 12-month return skipping the last month.
- **PE / PB / ROE / D/E / dividend yield** — valuation & quality fundamentals.
- **Supervised classification** — learn a mapping from features to a known label.
- **Gradient boosting / XGBoost** — sequential ensemble of trees correcting prior errors.
- **Walk-forward / TimeSeriesSplit** — time-respecting validation; train past, test future.
- **Lookahead bias** — leaking future info into past features/labels; inflates backtests.
- **Class imbalance / scale_pos_weight** — handling skewed label distributions.
- **ROC-AUC** — probability a random positive outranks a random negative; ranking quality.
- **Overfitting** — fitting noise; signalled by train ≫ validation performance.
- **Cross-sectional ranking** — compare assets to each other at one time, not to history.
- **Hypertable** — TimescaleDB's time-partitioned table.
- **Idempotent upsert** — re-runnable insert via `ON CONFLICT`.
- **Adapter/port seam** — isolating an external dependency behind an interface.
- **Rebalancing** — restoring target weights as prices drift.
- **Equity curve** — cumulative growth of ₹1; backtest output.
- **Survivorship bias** — analysing only the survivors; over-optimistic.
- **SSE vs scheduled batch** — streaming for fast-changing data vs cron for slow.

---

## 17. Interview question bank

Practice answering these out loud.

**Q1. Walk me through InvestIQ end to end.**
> Free EOD data (mfapi + yfinance) lands in a TimescaleDB store. A factor engine turns
> each security's price/NAV history into a 21-feature vector. An XGBoost model, validated
> walk-forward, estimates P(beat-the-benchmark-over-6-months). A scorer blends that with
> cross-sectional factor/risk/momentum percentiles into a 0–1 score, which a risk profile
> maps to BUY/HOLD/SELL. A paper portfolio + rebalancer act on it, a backtest validates
> the factor strategy vs Nifty, and a Flask API serves a Next.js dashboard.

**Q2. Why XGBoost and not a neural net / logistic regression?**
> Tabular data with ~20 features and a few thousand rows is XGBoost's sweet spot: it
> captures non-linear interactions, handles missing values natively, regularises well, and
> trains in seconds. A neural net needs far more data and tuning for no gain here; logistic
> regression is a fine *baseline* but can't model interactions without manual feature
> crosses.

**Q3. How do you avoid lookahead bias?**
> Three places: (1) rolling features are strictly backward-looking; (2) validation uses
> TimeSeriesSplit so every test set follows its training set; (3) the backtest uses as-of
> features and *excludes* the ML model (trained on full history). The one residual is
> fundamentals being broadcast from the latest snapshot — documented, and fixable with a
> point-in-time fundamentals source.

**Q4. Your AUC is only 0.60 — isn't that bad?**
> For 6-month forward relative-return prediction on noisy markets, 0.60 is a *real* edge;
> markets are near-efficient, so anything near 0.8 would make me suspect leakage. What
> matters is that it ranks future outperformers above underperformers ~60% of the time,
> and the backtest of that ranking beats the index by ~5%/yr.

**Q5. Why cross-sectional percentile ranking instead of using raw factor values?**
> We need to *compare securities to each other* to build a ranked list. Percentiles make
> heterogeneous units comparable (a PE and a Sharpe aren't on the same scale), tame
> outliers, and are robust to market-wide moves — if everything drops, relative ranking
> still distinguishes quality.

**Q6. How does the ML probability combine with the rule-based scores?**
> A weighted blend: 0.45 ML + 0.25 factor + 0.15 risk + 0.15 momentum. ML leads but can't
> dominate, so a model quirk can't override sane factor logic, and the result stays
> explainable to the user. It's an ensemble of learned + interpretable signals.

**Q7. Why a daily scheduler and not the websocket/SSE the trading app used?**
> Cadence dictates mechanism. Investing data changes once a day, so streaming would be
> wasted infrastructure; a single 18:30 batch (refresh → features → recommend) is correct
> and simpler.

**Q8. What's the broker seam and why does it matter?**
> An abstract `BrokerAdapter` with a `PaperBroker` now and a `LiveBroker` stub. All
> portfolio logic depends on the interface, so going live later is a swap of one class —
> the dangerous external dependency (real money) is isolated behind a port.

**Q9. How would you productionise this?**
> Point-in-time fundamentals; transaction costs + slippage in the backtest; walk-forward
> *retraining* inside the backtest; a wider/point-in-time-correct universe; model
> monitoring + drift alerts; auth + a real broker behind `LiveBroker`; CI on the PRs;
> containerising the whole stack.

**Q10. Tell me about a bug you fixed and what it taught you.**
> The recommendation engine returned zero BUYs because an absolute `min_sharpe` gate
> filtered everything in a negative-Sharpe market window. I realised absolute risk floors
> are regime-dependent and brittle, relaxed the hard gate (relative risk is already in the
> score), and recalibrated thresholds to the actual score distribution. Lesson: in a
> ranking system, prefer relative gates and always check your filters can't degenerate.

**Q11. How is the database modelled and why TimescaleDB?**
> Time-series tables (`price_history`, `nav_history`, `features`) are hypertables
> partitioned by date; composite `(date, symbol)` keys make ingestion idempotent via
> upserts. TimescaleDB is reused from the reference app and right-sized for growth — at the
> current scale plain Postgres would also work, which I'd flag honestly.

**Q12. What is alpha vs beta, intuitively?**
> Beta is how much you move *with* the market; alpha is the return left over *after*
> accounting for that market exposure — genuine edge. A fund up 20% in a 20%-up market with
> β=1 has ~0 alpha; the same return with β=0.5 is large positive alpha.

**Q13. Why average-cost accounting, and when would it bite?**
> It's simple and correct for displaying unrealised P&L and weights. It bites on *realised*
> P&L and taxes, where lot-level FIFO/specific-identification matters — that's the upgrade
> path if real money is involved.

**Q14. How do you know the strategy isn't just overfit to one lucky period?**
> I don't, fully — it's a single market over one window with survivorship bias and no
> costs. I'd want multiple regimes, walk-forward retraining, out-of-sample years, and a
> deflated Sharpe / multiple-testing correction before trusting it with capital.

---

## 18. Possible extensions

- **Point-in-time fundamentals** to remove the one lookahead simplification.
- **Walk-forward retraining inside the backtest** for a fully honest strategy curve.
- **Transaction costs, slippage, STT/taxes** in the backtest.
- **Sector/cap constraints** in the rebalancer for true diversification.
- **More factors** (earnings revisions, accruals, liquidity) and factor-orthogonalisation.
- **Explainability** (SHAP values per recommendation).
- **Model monitoring**: feature drift, performance decay alerts.
- **A real broker behind `LiveBroker`** (e.g. an Indian brokerage / BSE StAR MF API).
- **Auth + multi-user portfolios**; containerised deploy; CI/CD on PRs.

---

## 19. Appendix: file-by-file map

```
investiq/
├── config/
│   ├── settings.py            DB URL, FEATURE_COLUMNS (21), score weights, RF, label horizon
│   ├── risk_profiles.py       Conservative/Balanced/Aggressive dataclasses + helpers
│   └── universe.py            Nifty 50 tickers + fund targets + benchmark
├── utils/logger.py            UTF-8-safe console logger
├── data/
│   ├── mfapi_adapter.py       scheme resolve (Direct-Growth) + NAV history
│   ├── yfinance_adapter.py    EOD OHLCV + best-effort fundamentals
│   ├── ingest.py              orchestrates the full/sample/refresh ingest
│   └── mock_data.py           synthetic universe for offline dev
├── database/
│   ├── db.py                  read_sql / write_df / upsert_rows / init_db
│   └── schema.sql             9 tables; hypertables for the time-series ones
├── features/factor_engine.py  21-factor vectors, point-in-time, monthly sampling
├── models/
│   ├── train_model.py         labels + walk-forward AUC + XGBoost + registry/backup
│   └── predict.py             Predictor (load + P(outperform) + 0.5 fallback)
├── strategy/
│   ├── scorer.py              cross-sectional sub-scores + weighted final_score
│   └── recommendation_engine.py  thresholds/gates → BUY/HOLD/SELL + rationale
├── portfolio/
│   ├── broker_adapter.py      BrokerAdapter ABC + PaperBroker + LiveBroker stub
│   ├── paper_portfolio.py     holdings/cash/summary/snapshot
│   └── rebalancer.py          score-weighted, capped, sell-then-buy
├── backtest/backtest_engine.py  monthly factor-rank vs Nifty; CAGR/Sharpe/maxDD
├── backend/app.py             Flask REST API (port 5055)
├── scheduler/daily_refresh.py APScheduler 18:30 daily job
├── frontend/                  Next.js dashboard (app/, components/, lib/api.ts)
└── main.py                    CLI: mock | ingest | train | backtest | recommend | serve
```

---

## 20. Annotated code walkthroughs

Reading the actual code with commentary is the fastest way to *own* the project in an
interview. Below are the load-bearing functions, lightly trimmed, with line-by-line notes.

### 20.1 Rolling features (`features/factor_engine.py`)

```python
def _rolling_features(val: pd.Series, bench: pd.Series) -> pd.DataFrame:
    b = bench.reindex(val.index).ffill()      # align benchmark to the security's dates
    r  = val.pct_change()                      # daily simple returns of the security
    rb = b.pct_change()                        # daily returns of the benchmark
    rf_d = RF / TD                             # daily risk-free rate (annual / 252)

    out = pd.DataFrame(index=val.index)
    out["ret_1m"]  = val / val.shift(21)  - 1  # trailing 1-month return (21 trading days)
    out["ret_6m"]  = val / val.shift(126) - 1
    out["cagr_3y"] = (val / val.shift(756)) ** (1/3) - 1   # geometric annualisation

    vol = r.rolling(252).std()                 # 1y rolling daily-return std
    out["volatility"] = vol * np.sqrt(TD)      # annualise: σ_annual = σ_daily·√252
    downside = r.where(r < 0, 0.0)             # keep only negative returns, zero the rest
    out["downside_dev"] = downside.rolling(252).std() * np.sqrt(TD)
    mean_r = r.rolling(252).mean()
    out["sharpe"]  = (mean_r*TD - RF) / (vol*np.sqrt(TD))   # (annual ret − RF) / annual σ
    out["sortino"] = (mean_r*TD - RF) / out["downside_dev"]

    roll_max = val.rolling(252, min_periods=20).max()
    out["max_drawdown"] = (val/roll_max - 1).rolling(252, min_periods=20).min()  # worst dip

    cov = r.rolling(252).cov(rb)
    var = rb.rolling(252).var()
    out["beta"]  = cov / var                   # β = cov(asset, mkt) / var(mkt)
    out["alpha"] = (mean_r - rf_d - out["beta"]*(rb.rolling(252).mean() - rf_d)) * TD
    ...
    return out.replace([np.inf, -np.inf], np.nan)   # guard divide-by-zero
```

**Things to notice / be asked about:**
- `.shift(k)` is what makes a feature *point-in-time*: today's value vs the value `k` days
  ago — never the future.
- `√252` annualisation assumes daily returns are independent and identically distributed
  (i.i.d.). They aren't perfectly (volatility clusters), but it's the standard convention.
- `min_periods=20` lets drawdown compute before a full year of data exists, trading a
  little accuracy for coverage early in a series.
- The final `replace(inf → NaN)` handles assets with near-zero benchmark variance; XGBoost
  ignores NaN, so downstream code stays simple.

### 20.2 Forward-outperformance labels (`models/train_model.py`)

```python
for sym, grp in feat.groupby("symbol"):
    val  = _load_value_series(sym, ...)        # the security's full price/NAV series
    benr = bench.reindex(val.index).ffill().values
    valr = val.values
    pos  = {d: i for i, d in enumerate(val.index)}   # date → integer position
    for idx, row in grp.iterrows():
        i = pos.get(pd.Timestamp(row["date"]))
        if i is None or i + forward >= len(valr):
            continue                            # not enough future data → leave unlabeled
        sec_fwd = valr[i+forward] / valr[i] - 1               # security's 6m forward return
        ben_fwd = benr[i+forward] / benr[i] - 1               # benchmark's 6m forward return
        feat.at[idx, "target"] = 1.0 if (sec_fwd - ben_fwd) > margin else 0.0
```

**Notes:** the label is computed by *looking forward `forward` days from each feature
date* — this is allowed because it's the **label** (the thing we're learning to predict),
not a feature. The most recent ~6 months have no label yet and are dropped from training
(but kept for live prediction).

### 20.3 Walk-forward AUC (`models/train_model.py`)

```python
def _walk_forward_auc(X, y, n_splits=5):
    aucs = []
    for tr, te in TimeSeriesSplit(n_splits=n_splits).split(X):
        ytr, yte = y.iloc[tr], y.iloc[te]
        spw = (ytr == 0).sum() / max((ytr == 1).sum(), 1)     # per-fold class weight
        m = _build_xgb(spw); m.fit(X.iloc[tr], ytr)
        aucs.append(roc_auc_score(yte, m.predict_proba(X.iloc[te])[:, 1]))
    return float(np.mean(aucs))
```

**Notes:** the model and `scale_pos_weight` are recomputed *inside* each fold so no fold
sees information from another. `predict_proba(...)[:, 1]` takes the probability of the
positive class. We average AUC across folds for a single honest number.

### 20.4 Cross-sectional scoring (`strategy/scorer.py`)

```python
def _pct(s): return s.rank(pct=True)           # percentile rank in [0,1], NaN-safe

factor = pd.DataFrame({
    "roe": _pct(df["roe"]), "low_pe": 1 - _pct(df["pe"]),    # high ROE good, low PE good
    "low_pb": 1 - _pct(df["pb"]), "low_de": 1 - _pct(df["debt_equity"]),
    "consistency": _pct(df["consistency"]),
})
df["factor_score"] = factor.mean(axis=1, skipna=True).fillna(0.5)   # avg of available
...
df["final_score"] = (W_ML*df["ml_prob"] + W_FACTOR*df["factor_score"]
                     + W_RISK*df["risk_score"] + W_MOMENTUM*df["momentum_score"])
```

**Notes:** `1 - _pct(pe)` flips the direction (cheap = good). `fillna(0.5)` gives a neutral
score to securities missing a sub-factor (e.g. funds with no PE) rather than penalising
them. The weighted sum stays in [0,1] because every term is in [0,1] and weights sum to 1.

### 20.5 Rebalance to targets (`portfolio/rebalancer.py`)

```python
w = buys["final_score"] / buys["final_score"].sum()   # score-weighted
w = w.clip(upper=profile.max_holding_weight)           # cap any single name
w = w / w.sum()                                        # renormalise after capping
investable = pf.summary()["total_value"] * (1 - profile.cash_buffer)
targets = dict(zip(buys["symbol"], w * investable))    # target ₹ per name

# 1) sell everything not in targets   2) trim overweight   3) buy underweight
```

**Notes:** capping *then* renormalising is the subtle bit — after you clip a dominant
name, the freed weight must be redistributed so weights still sum to 1. Sell-before-buy
guarantees cash is on hand for the purchases.

---

## 21. Worked numeric examples (do these on paper)

Being able to *compute* a metric on a toy example cements understanding.

**Annualising volatility.** Daily return std = 1.2% = 0.012.
`σ_annual = 0.012 × √252 ≈ 0.012 × 15.87 ≈ 0.19` → **~19% annual volatility.**

**Sharpe ratio.** Annual return 18%, annual vol 19%, RF 6.5%.
`Sharpe = (0.18 − 0.065) / 0.19 ≈ 0.115 / 0.19 ≈ 0.61.` Rule of thumb: <1 mediocre, 1–2
good, >2 excellent (for a diversified portfolio).

**Sortino.** Same excess return 11.5%, but downside deviation only 12%.
`Sortino = 0.115 / 0.12 ≈ 0.96` — higher than Sharpe because upside swings weren't
penalised.

**Max drawdown.** Series peaks at ₹120, troughs at ₹84 before recovering.
`DD = 84/120 − 1 = −0.30` → **−30% max drawdown.** To get back to ₹120 from ₹84 you need
`120/84 − 1 ≈ +43%` — drawdowns are asymmetric, which is why they hurt.

**CAGR.** ₹1 grows to ₹1.61 over 3 years. `CAGR = 1.61^(1/3) − 1 ≈ 0.172` → **~17.2%/yr.**

**Beta & alpha.** Asset up 24% in a year; market up 20%; RF 6%; β = 1.2.
Expected (CAPM) return = `RF + β·(mkt − RF) = 6% + 1.2×(20% − 6%) = 6% + 16.8% = 22.8%`.
`alpha = actual − expected = 24% − 22.8% = +1.2%.` Small positive skill after paying for
the extra market risk the β=1.2 implies.

**Percentile rank.** Five PEs: [12, 18, 22, 30, 45]. The stock at PE 18 is the 2nd-cheapest
of 5 → `_pct(pe) = 0.4`, and `low_pe = 1 − 0.4 = 0.6` (above-average cheapness).

**ROC-AUC intuition.** If the model outputs scores and you pick one true outperformer and
one true underperformer at random, AUC = 0.60 means the outperformer gets the higher score
60% of the time.

---

## 22. Deeper ML theory (the bits interviewers dig into)

### 22.1 Bias–variance trade-off

- **Bias** = error from too-simple assumptions (underfitting). **Variance** = error from
  being too sensitive to the training set (overfitting). Total error ≈ bias² + variance +
  irreducible noise.
- Our knobs: shallow trees (`max_depth=4`), subsampling (0.8), and a moderate tree count
  (300) push toward *lower variance* (more bias) — appropriate because financial labels are
  extremely noisy, so we'd rather underfit slightly than chase noise.
- The symptom of healthy regularisation: train accuracy 0.86 but CV AUC 0.60 — a gap that
  says "don't trust the training fit; the honest signal is the CV number."

### 22.2 Confusion matrix, precision, recall, F1

For a chosen probability threshold:

```
                 predicted BUY    predicted not-BUY
actual outperf.   TP               FN
actual underperf. FP               TN
```
- **Precision** = TP / (TP+FP) — "of the BUYs I made, how many were right?"
- **Recall** = TP / (TP+FN) — "of the outperformers, how many did I catch?"
- **F1** = harmonic mean of precision & recall.
- For an *advisor*, **precision matters more than recall** — a wrong BUY costs real money,
  while a missed opportunity only costs regret. That's an argument for a *higher* score
  threshold (the conservative profile's 0.60).

### 22.3 ROC-AUC vs PR-AUC

- **ROC-AUC** plots TPR vs FPR across thresholds; threshold-independent ranking quality.
- **PR-AUC** (precision-recall) is more informative under heavy class imbalance. Here the
  classes are fairly balanced (65/35), so ROC-AUC is fine, but mention PR-AUC as the better
  choice if the positive rate were, say, 5%.

### 22.4 Why logloss as the training objective?

`logloss = −[y·log(p) + (1−y)·log(1−p)]` heavily punishes *confident wrong* predictions.
Optimising it yields **calibrated probabilities** (a "0.7" really means ~70% likelihood),
which matters because we *use the probability as a number* in the weighted score — not just
a yes/no. Accuracy as an objective would ignore calibration.

### 22.5 Feature importance vs SHAP

XGBoost's `feature_importances_` (we log the top 8 — ROE, beta, max-drawdown, consistency,
…) shows *global* importance but can be biased toward high-cardinality features. **SHAP**
values would give *per-prediction* attributions ("this BUY is driven by momentum + low
debt"), which is the natural next step for explainable recommendations.

### 22.6 Why tree ensembles beat linear models here

Factors interact non-linearly: e.g. high momentum is good *unless* valuation is extreme;
low volatility helps *more* for certain sectors. Trees split on these interactions
automatically; a linear model needs hand-crafted interaction terms. Trees are also
**scale-invariant** (no need to standardise features) and handle NaN — both convenient
for a mixed equity/fund universe.

---

## 23. Alternative designs considered (and why the choice)

| Decision | Alternatives | Why the chosen path |
|---|---|---|
| In-place rewrite vs additive module | rewrite the trading app | **additive** under `investiq/` keeps the working app intact and risk low |
| Plain Postgres vs TimescaleDB | plain Postgres | reused TimescaleDB; honest that it's over-provisioned now |
| ML-in-backtest vs ML-excluded | use the model | **exclude** to avoid lookahead; flagged walk-forward retrain as the rigorous upgrade |
| Absolute risk gates vs relative | hard Sharpe floor | **relative** (cross-sectional) gates don't degenerate across regimes |
| SSE streaming vs daily batch | keep SSE | **batch** matches daily data cadence |
| Average cost vs FIFO lots | FIFO | **average cost** is enough for display; FIFO is the upgrade for tax-accurate realised P&L |
| Hand-set blend vs pure-ML score | pure ML | **blend** keeps it explainable and robust to model quirks |
| Equal-weight vs cap-weight backtest | cap-weight | **equal-weight top-N** is the cleanest factor-strategy demonstration |

Being able to articulate the road *not* taken — and the trade-off — is often more
impressive than the choice itself.

---

## 24. A short revision plan & 60-second pitches

### 24.1 If you have one evening

1. Read Sections 1–4 (narrative + architecture).
2. Re-derive the six metrics in Section 21 on paper.
3. Read Sections 7 (ML) and 8 (scoring) closely.
4. Rehearse Q1, Q3, Q4, Q6, Q7, Q10 aloud.

### 24.2 60-second pitch per subsystem (practice each)

- **Data:** "Free EOD data — mutual-fund NAVs from mfapi, equities from yfinance — upserted
  idempotently into a TimescaleDB store; composite `(date, symbol)` keys make re-ingestion
  safe."
- **Features:** "21 factor features per security per day across value, quality, momentum and
  risk families, all point-in-time via rolling windows; fundamentals are the one documented
  simplification."
- **ML:** "XGBoost predicts 6-month outperformance vs the benchmark, validated walk-forward
  with TimeSeriesSplit; AUC ~0.60 — a real, modest, non-overfit edge."
- **Scoring:** "Cross-sectional percentile sub-scores for factor/risk/momentum, blended
  45/25/15/15 with the ML probability into a 0–1 conviction score."
- **Decision:** "Risk profiles map the score to BUY/HOLD/SELL with diversification and
  volatility gates; recommendations are holding-aware."
- **Execution:** "A paper portfolio behind an adapter seam, with a score-weighted, capped,
  sell-then-buy rebalancer; a `LiveBroker` stub is the swap-in for real trading."
- **Backtest:** "Monthly equal-weight top-N factor strategy vs Nifty — CAGR ~13.8% vs 8.8%,
  Sharpe ~0.5 — with ML excluded to stay lookahead-free."
- **Serving:** "Flask REST API plus a daily APScheduler refresh; a Next.js light-theme
  dashboard proxies `/api` to it."

---

## 25. Extended interview question bank (Q15–Q30)

**Q15. What is the risk-free rate and why does it appear in Sharpe/alpha?**
> The return on a "riskless" asset (here ~6.5%, an Indian-government-yield proxy). Risk
> metrics measure *excess* return over what you'd earn risk-free, because earning the
> risk-free rate requires no skill.

**Q16. Why annualise with √time for vol but with compounding for returns?**
> Variance scales linearly with time for i.i.d. returns, so std scales with √time; wealth
> *compounds* multiplicatively, so returns annualise geometrically (CAGR). Mixing them up
> is a classic error.

**Q17. Your label has a 65% positive rate — does that bias the model?**
> It reflects a bull sample window. `scale_pos_weight` rebalances the loss so the model
> still learns to discriminate, and AUC (not accuracy) is imbalance-robust. Across regimes
> I'd tune the `margin` to stabilise the positive rate.

**Q18. How would you detect that the model has gone stale in production?**
> Monitor input **feature drift** (distribution shift vs training), **prediction drift**,
> and realised **hit-rate/AUC** on newly-resolved labels; alert when they decay, and
> retrain on a schedule (walk-forward).

**Q19. Why store recommendations in a table at all if you recompute them?**
> It's a cache + audit log: cheap reads for the dashboard, a historical record of what was
> advised when, and the basis for tracking realised recommendation performance later.

**Q20. What happens on the very first run with no trained model?**
> `Predictor` returns a neutral 0.5 for every security, so the factor/risk/momentum scores
> drive recommendations until a model exists — graceful degradation, nothing crashes.

**Q21. Why exclude the INDEX from recommendations?**
> You can't directly buy the raw Nifty index; you'd buy an index *fund* (which is in the
> universe). The index is kept only as the benchmark for beta/alpha/relative labels.

**Q22. How do you keep the frontend and backend in sync?**
> A typed contract: `lib/api.ts` interfaces mirror the Flask JSON. TypeScript fails the
> build if the client uses a field the API doesn't return, catching drift at compile time.

**Q23. Why upsert with ON CONFLICT instead of delete-then-insert?**
> Upsert is atomic and idempotent; delete-then-insert has a window where the row is missing
> and can lose data on a crash between the two statements.

**Q24. What's the difference between your `factor_score` and the ML model — don't they
overlap?**
> They use overlapping inputs but differently: `factor_score` is a transparent, hand-set
> percentile blend; the ML model learns non-linear interactions and weights from the *label*.
> Blending them hedges model risk and keeps the output explainable.

**Q25. How would transaction costs change the backtest?**
> Every monthly rebalance trades; costs (brokerage + STT + slippage, maybe 0.1–0.5% per
> turnover) compound and would shave the CAGR and Sharpe. High-turnover strategies are hit
> hardest — a reason to penalise turnover or rebalance less often.

**Q26. Why monthly rebalancing — why not daily or yearly?**
> Daily chases noise and racks up costs; yearly is too slow for momentum to work. Monthly
> is the common compromise that lets the ~6-month signal express itself at acceptable
> turnover.

**Q27. What is survivorship bias, concretely, in this project?**
> Using *today's* Nifty 50 membership for historical dates silently excludes companies that
> were dropped (often after doing badly), making the past look rosier than it was. A
> point-in-time index-membership history fixes it.

**Q28. If two securities tie on score, what breaks the tie / how is N chosen?**
> Sorting is by `final_score` descending; ties fall back to row order. N = the profile's
> `max_holdings` (8/12/15). A refinement would add a sector cap so the top-N isn't all one
> sector.

**Q29. Could you A/B test recommendation quality?**
> Yes — track realised forward returns of BUY vs HOLD vs SELL buckets over time; a healthy
> system shows BUY > HOLD > SELL on average forward return. That's the live analogue of the
> backtest.

**Q30. What's the single biggest risk in shipping this for real?**
> Acting on a modest-AUC model as if it were certain. Mitigations: position caps,
> diversification, the volatility gate, paper-first, and never removing the "not investment
> advice / educational" framing until it's properly validated and (in India) SEBI-compliant.

---

### Final framing for the interview

If you remember nothing else: **InvestIQ ranks a universe of investable assets every
period by an honest, validated estimate of future risk-adjusted outperformance, blends a
learned model with interpretable factors, and acts on the ranking through a clean,
swappable execution layer — with the intellectual honesty to name exactly where the
estimate is weak.** That sentence, plus the ability to go one level deeper on any clause,
is what carries the conversation.
