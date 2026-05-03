---
name: risk-auditor
description: Audit risk management configurations and ensure system safety.
---

# Risk Auditor Skill

Use this skill when reviewing `risk/risk_manager.py`, auditing balance state, or responding to drawdown alerts.

## Core Directives
- **Zero Tolerance:** Never suggest increasing the daily drawdown limit above 5%.
- **Integrity Check:** Ensure `stoploss_on_exchange` is always `True` in strategy configs.
- **Exposure Audit:** Verify that no single position exceeds 10% of total balance.
- **Circuit Breaker:** If 3 consecutive losses are detected, verify that the entry pause is active.

## Audit Workflow
1. Check `risk/balance_state.json` for current drawdowns.
2. Review `logs/risk_manager.log` for rejected entries.
3. Validate API key permissions — ensure "Withdrawals" is DISABLED.
4. Confirm `caffeinate` is running to prevent M1 node sleep during live trades.
