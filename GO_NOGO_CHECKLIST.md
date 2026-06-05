# Cipher — Live Deployment Go/No-Go Checklist

**Last updated:** 2026-06-05
**Current status:** PAPER TRADING ONLY

This checklist must be fully checked before ANY live capital is deployed.
No exceptions. Each item requires documented evidence, not just assertion.

---

## SECURITY

- [ ] All credentials in `.env` file (not committed). Verify with `git diff HEAD -- config/` shows no secrets.
- [ ] `FT_JWT_SECRET_KEY` regenerated with `openssl rand -hex 32` (old key `cdc94c50...` was exposed in git history — rotate exchange API keys if the repo was ever public).
- [ ] Telegram token and chat_id confirmed working via `curl` test.
- [ ] PostgreSQL password changed from the default `dummy` placeholder.
- [ ] `.gitignore` covers all `config/config_*.json` files.

---

## STRATEGY VALIDATION (MeanReversionV1 only)

- [ ] **Out-of-sample backtest completed** on 2025-06-01 → 2026-06-01 hold-out period (data NEVER used during development).
  - Required: Sharpe > 0.5
  - Required: Max drawdown < 15%
  - Required: beats BTC buy-and-hold on risk-adjusted basis
  - Actual results: _______________ (fill in)

- [ ] **Slippage stress test**: backtest re-run with 2× base slippage (6 bps for BTC, 10 bps for ETH, 16 bps for alts). Strategy must remain profitable.
  - Stress-test results: _______________ (fill in)

- [ ] **Paper trading: minimum 3 months** (start date ≥ 2026-06-05, so not before 2026-09-05).
  - Paper trade start date: _______________
  - Paper trade end date: _______________
  - Number of closed trades: _______________ (must be ≥ 30)
  - Win rate: _______________ (must be ≥ 50% for 1:1 R/R target)
  - Total paper P&L: _______________
  - Worst drawdown during paper period: _______________

- [ ] **Parameter sensitivity analysis**: vary `bb_period` ±5 and `bb_std` ±0.3 from optimal. Performance must not collapse (no more than 30% Sharpe degradation). If performance is cliff-edge sensitive, the strategy is curve-fit.
  - Sensitivity results: _______________ (fill in)

---

## DATA INTEGRITY

- [ ] Historical sentiment data available and point-in-time verified (or sentiment disabled in backtests).
- [ ] Macro data (`macro_history.json`) provenance documented — timestamps are collection-time, not candle-close time.
- [ ] Data validation layer (`qnt/data/validation.py`) active and logging to `logs/data_validation.log`.
- [ ] No data gaps > 3 consecutive candles in the last 30 days for BTC/USDT 1h (primary pair).

---

## RISK MANAGEMENT

- [ ] Daily drawdown circuit breaker tested: simulated 3% loss halts all entries.
- [ ] Weekly drawdown circuit breaker tested: simulated 7% loss requires manual reset.
- [ ] Kelly sizing WR floor verified: query `risk/stake_sizer.py` with 40% WR → confirms `stake_multiplier = 0.0`.
- [ ] Correlation guard tested: two simultaneous BTC entries → second is blocked.
- [ ] Volatility breaker tested: elevated-vol dataframe → entry blocked.
- [ ] Telegram alerts enabled (`"enabled": true` in config) and tested with `/start` command.
- [ ] Balance state file (`risk/balance_state.json`) auto-updated at day/week start.
- [ ] Emergency kill switch documented and tested: `supervisorctl stop freqtrade_mean_reversion`.

---

## EXECUTION

- [ ] Binance API keys configured with **trade permissions only** (no withdrawal permissions).
- [ ] Exchange API rate limits understood and respected.
- [ ] Order type confirmed: limit entry, market emergency exit.
- [ ] Exchange-side stoploss confirmed working in dry_run before live.
- [ ] Partial fill behavior tested.

---

## INFRASTRUCTURE

- [ ] PostgreSQL running and persisting across reboots.
- [ ] NATS server running for sentiment delivery.
- [ ] Supervisord set to restart MeanReversionV1 on unexpected exit.
- [ ] Log rotation configured (max 50MB per file, 5 backups).
- [ ] HMM model validated: if `qnt/oracle/hmm_model.pkl` missing, bot logs `UNKNOWN` regime and blocks entries (fail-safe, not fail-open).

---

## MONITORING

- [ ] Grafana dashboard showing equity curve, open trades, risk metrics.
- [ ] Prometheus scraping bot metrics.
- [ ] Alert rule: page if no candles received for > 15 minutes.
- [ ] Alert rule: page if daily drawdown > 2% (warning before 3% halt).

---

## ONE-STRATEGY RULE

- [ ] Confirm `supervisord.conf` has `autostart=false` for ALL strategies except `freqtrade_mean_reversion`.
- [ ] Confirm `strategies/active/` contains ONLY `MeanReversionV1.py`.
- [ ] Confirm no other ensemble is running.

---

## SIGN-OFF

| Check | Verified by | Date |
|-------|-------------|------|
| Security | | |
| Out-of-sample backtest | | |
| 3-month paper trade | | |
| Risk management tests | | |
| Infrastructure | | |

**DO NOT deploy live capital until every checkbox above is ticked with documented evidence.**
