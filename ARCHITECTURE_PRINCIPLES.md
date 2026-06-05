# Cipher — Architecture Principles

**Established:** 2026-06-05 (post-audit repair)
**Reason:** Paper trading results showed catastrophic signal failure across all strategies.

---

## The One Strategy Rule

**Cipher runs ONE strategy until it proves positive edge.**

The system launched with 8 concurrent strategies. Paper trading results as of 2026-06-05:

| Strategy | Trades | Win Rate | P&L | Verdict |
|---|---|---|---|---|
| ScalpV1 | 21 | 23.8% | -$55.22 | Halted |
| SwingV1 | 16 | 12.5% | -$48.00 | Halted |
| TrendFollowV1 | 1 | 0% | -$8.54 | Halted |
| DailyTrendV1 | 0 | — | — | Halted |
| MicroScalpV1 | 3 | — | +$11.86 | Halted (N=3) |
| MeanReversionV1 | 6 | 83.3% | +$1.91 | **ACTIVE** (N=6, needs more data) |

An ensemble of negative-expectancy strategies produces a negative-expectancy portfolio. Averaging losses does not create profits.

**MeanReversionV1 is the sole active strategy** until it demonstrates:
- ≥ 30 closed paper trades with ≥ 50% win rate
- ≥ 3 months of paper trading without halting
- Out-of-sample Sharpe > 0.5 on the 2025-06-01 → 2026-06-01 hold-out period

No new strategies may be added to `strategies/active/` without passing the above criteria first.

---

## Infrastructure Freeze

The infrastructure layer (Rust engine, Qdrant vector DB, NATS messaging, LLM agents, MCP server, Ray distributed hyperopt) is **frozen**.

No new features may be added to infrastructure while the core strategy is unproven. Complexity is not an edge. It is a liability.

Specifically frozen:
- `rust_engine/` — do not extend
- `qnt/vault/` (Qdrant) — do not expand
- `qnt/thesis/` (LLM thesis gate) — disabled in all active strategies
- `qnt/oracle/oracle_anomaly.py`, `order_flow.py`, `realtime_orderflow.py` — not wired to MeanReversionV1
- `cipher_mcp/` — operational for monitoring only, not for trade decisions

---

## Fail-Safe, Not Fail-Open

Every system that fails must default to **NO TRADE**, not unrestricted trading.

| Component | Failure | Before | After |
|---|---|---|---|
| HMM model missing | Can't load from M2 | Return "RANGING" (trade) | Return "UNKNOWN" (block) |
| Sentiment pipeline down | can't read score | Default 0.0 (neutral, trade) | Default 0.0 (risk manager still checks; sentiment=UNAVAILABLE ranks 0 → block) |
| Volatility breaker error | exception | n/a (didn't exist) | Log error, block entry |
| Kelly WR < 45% | poor edge | Trade at floor multiplier | Return 0.0 (halt) |

---

## Bi-Weekly Review Protocol

Every 2 weeks, review paper trading results. Decision tree:

```
Last 40 trades WR < 45% ?
    YES → Halt MeanReversionV1, diagnose signal failure, do NOT resume
           without parameter re-optimization on new data
    NO  →
        Sharpe (rolling 30 trades) < 0 ?
            YES → Investigate: check regime filter, slippage, data quality
            NO  → Continue paper trading, log results
```

If MeanReversionV1 fails three consecutive 2-week reviews, the project is shelved pending fundamental strategy redesign.

---

## Costs Matter More Than Signals

Assume the following costs are REAL and model them conservatively:

| Pair | Min slippage (bps) | Stress (2× normal) |
|---|---|---|
| BTC/USDT | 3 | 6 |
| ETH/USDT | 5 | 10 |
| SOL/USDT | 8 | 16 |
| Altcoins (LINK, DOT, ADA, AVAX) | 10 | 20 |

A strategy profitable at 1× slippage but failing at 2× has no real edge — it is exploiting the backtest's optimistic assumptions.

Every backtest must report a "Sharpe under 2× slippage" metric before acceptance.

---

## No Dead Code

Every function in `strategies/active/` must be exercised. Specifically:

- The Skeptic Agent (`qnt/agents/strategist.py`, `qnt/agents/trade_gate.py`) does not exist. It is removed from all active strategies. If it is re-implemented, it must have unit tests before being added to production.
- The Thesis Gate (`qnt/thesis/`) is disabled in all active strategies. It may be re-enabled only after a controlled experiment shows measurable improvement in win rate (A/B test with >= 40 trades in each arm).
- `_partial_exits_done` module-level sets (in archived strategies) were removed because they reset on restart and could produce duplicate partial exits. If partial exits are re-implemented, they must use persistent trade-level flags in the database.

---

## The Review Criterion for Re-enabling Archived Strategies

Archived strategies (`strategies/archive/`) may be moved back to `strategies/active/` only if:

1. Their fundamental signal failure is diagnosed and fixed (not just re-tuned)
2. They pass a standalone out-of-sample backtest (Sharpe > 0.5, max DD < 15%)
3. They pass 4 weeks of solo paper trading (≥ 20 trades, WR ≥ 50%)
4. They are added one at a time to the ensemble — never more than 2 strategies simultaneously

---

## What "Infrastructure" Is For

The infrastructure exists to support the strategy, not to replace it. Specifically:

- **NATS**: real-time sentiment delivery to running bots ✓
- **Qdrant**: storing trade lessons for post-mortem analysis ✓ (not for live decisions)
- **Rust engine**: fast nearest-neighbour for VectorVaultV1 ✓ (archived)
- **Prometheus/Grafana**: monitoring and alerting ✓
- **Ray + Optuna**: walk-forward hyperopt ✓ (run offline, not in real-time)

None of the above should be in the critical path of a live trade decision. Trade decisions must be deterministic, fast, and testable without running any of the above.
