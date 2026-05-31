# AGENTS.md — cipher
# Optimized per: arXiv:2601.20404 (−28.6% runtime, −16.6% tokens)

## Repo Quick-Map
- strategies/active/     — 7 production Freqtrade strategies
- indicators/            — shared indicator library (macro_merge, ta_wrappers, time_features)
- bus/                   — async event bus (channel, events, producers, consumers)
- mcp/                   — MCP server + 10 AI agent tools (port 9010)
- qnt/                   — intelligence layer (oracle, vault, hyperopt, freqai, memory)
- qnt/hyperopt/          — Ray + Optuna distributed hyperopt
- risk/                  — risk manager, stake sizer, correlation guard
- sentiment/             — FinBERT + multi-source sentiment pipeline
- automation/            — scheduled tasks, reporting
- rust_engine/           — PyO3/rayon Euclidean nearest-neighbour (VectorVaultV1)
- config/                — per-strategy Freqtrade JSON configs
- tests/                 — pytest suite
- .github/workflows/     — CI: Rust clippy+test, ruff, pytest, strategy backtest

## Entry Points
- Test:  `uv run pytest`
- Lint:  `uv run ruff check .`
- Format: `uv run ruff format .`
- Start: `./start_bot.sh`
- Stop:  `./stop_bot.sh`
- Agent CLI: `python qnt/agent.py --help`
- MCP server: `python -m mcp.server --port 9010`
- Hyperopt: `python -c "from qnt.hyperopt.distributed import run_study; run_study('ScalpV1')"`

## Off-Limits Paths
- `.env` and `.env.*` — never read or modify
- `__pycache__/`, `.git/`, `.venv/`, `venv/`
- Files with "secret", "credential", "key" in name

## Agent Behavior Policy
- Prefer surgical edits over full rewrites.
- Run tests after every code change.
- For files > 500 lines: read only the relevant section.
- Confirm before: deleting files, installing packages, changing configs.
- New indicators go in `indicators/` — not inline in strategy files.
- New event types go in `bus/events.py`.

## Context Compaction Triggers
- Manual: /compact after each discrete task.
- Auto: fires at 95% — manually compact at 70% for best quality.

## Parallelism Rules
- Tasks flagged [PARALLEL-SAFE] can run as simultaneous subagents.
- All others must run sequentially.
