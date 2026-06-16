# InvestIQ

AI-assisted **mutual-fund + equity investing advisor** (India) — long-term BUY/HOLD/SELL signals and
a simulated (paper) portfolio. Built as an additive module inside this repo; it does not touch the
existing trading app.

- **Domain:** investing (daily / EOD cadence), not intraday trading.
- **Data:** free / delayed sources — AMFI NAV, [api.mfapi.in](https://www.mfapi.in/), `yfinance`.
- **ML:** XGBoost classifier predicting forward outperformance vs benchmark (walk-forward validated).
- **Action scope:** paper portfolio now, with a broker-adapter seam for real execution later.

> ⚠️ Educational / personal-use. Not investment advice.

## Layout (target)

```
investiq/
├── config/      settings.py, risk_profiles.py
├── utils/       logger.py
├── data/        amfi_adapter.py, mfapi_adapter.py, yfinance_adapter.py, refresh.py, mock_data.py
├── database/    db.py, schema.sql
├── features/    factor_engine.py
├── models/      train_model.py, predict.py, recommender.py
├── strategy/    scorer.py, recommendation_engine.py
├── portfolio/   paper_portfolio.py, rebalancer.py, broker_adapter.py
├── backtest/    backtest_engine.py
├── backend/     app.py
└── main.py      modes: mock | ingest | train | backtest | recommend | serve
```

This scaffold ships the `config/` + `utils/` foundation only.
