# Graph Report - qnt  (2026-05-13)

## Corpus Check
- 74 files · ~24,315 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 453 nodes · 591 edges · 27 communities (25 shown, 2 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 54 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `698bc015`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]

## God Nodes (most connected - your core abstractions)
1. `QNT — MasterBot Intelligence System` - 18 edges
2. `load_memory()` - 17 edges
3. `TelegramWebhookHandler` - 13 edges
4. `save_memory()` - 11 edges
5. `risk_check()` - 9 edges
6. `run_on_m1()` - 9 edges
7. `DashboardPanel` - 9 edges
8. `send_telegram_message()` - 8 edges
9. `Cockpit` - 8 edges
10. `Active Strategies` - 8 edges

## Surprising Connections (you probably didn't know these)
- `risk_check()` --calls--> `load_memory()`  [INFERRED]
  shield/shield.py → memory/memory_manager.py
- `risk_check()` --calls--> `save_memory()`  [INFERRED]
  shield/shield.py → memory/memory_manager.py
- `autonomous_shield_check()` --calls--> `load_memory()`  [INFERRED]
  shield/shield.py → memory/memory_manager.py
- `autonomous_shield_check()` --calls--> `save_memory()`  [INFERRED]
  shield/shield.py → memory/memory_manager.py
- `killswitch()` --calls--> `run_on_m1()`  [INFERRED]
  bridge/bridge.py → memory/device_router.py

## Communities (27 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (48): BaseHTTPRequestHandler, execute_command(), execute_command_raw(), get_current_time_ist(), get_device_name(), handle_callback_query(), Enhanced Telegram Bot with Inline Keyboards and Advanced Commands ==============, Identify device (M1/M2). (+40 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (42): Active Strategies, Always Safe To Do Without Asking, Auto202605030340, Automation Schedule, Bridge Commands (available from M1 or M2), Browser Engine, Cockpit Command, code:block1 (*/5 * * * * bash /Users/aatifquamre/masterbot/qnt/memory/syn) (+34 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (35): evaluate_trade(), get_skeptic_stats(), Load skeptic stats from memory and return formatted string., Main gate function called by strategies.     Returns dict with decision and reas, check_connectivity(), create_initial_memory(), get_recent_actions(), load_memory() (+27 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (31): bot_restart(), bot_start(), bot_status(), bot_stop(), call_api_all(), get_ist_now(), killswitch(), Stream logs from all 5 bot instances. (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (23): build_skeptic_prompt(), get_vault_context(), run_skeptic(), generate_post_mortem(), generate_weekly_post_mortem(), Analyze all losses from the past week across all databases., Generate detailed AI analysis of a specific trade., add_entry() (+15 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (9): App, Cockpit, DashboardPanel, GlobalStatusPanel, IntegratedLogPanel, MarketOraclePanel, A generic panel for the dashboard., ShieldPanel (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (17): get_global_status_panel(), get_ist_now(), get_logs_panel(), get_market_intel_panel(), get_shield_panel(), get_trades_panel(), run_dashboard(), check_and_act() (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.14
Nodes (17): detect_regime(), get_regime_for_strategy(), load_hmm_model(), Load HMM model from M2 via SCP if not cached locally., Returns: 'BULL', 'BEAR', or 'RANGING'     Uses last 100 candles of 1m data for m, Returns True if strategy should trade in current regime.     MicroScalpV1: trade, extract_lesson(), generate_negative_constraint() (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (16): deploy_strategy(), evolve_strategy(), generate_strategy(), optimize_strategy(), Analyze losers and generate a V2., Deploy strategy to active/ folder., Generate a Freqtrade strategy based on a hypothesis., run_backtest() (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.2
Nodes (16): autonomous_shield_check(), calculate_risk_level(), call_freqtrade_api_all(), get_balance(), get_db_path(), get_exposure(), get_ist_now(), get_pnl() (+8 more)

### Community 10 - "Community 10"
Cohesion: 0.17
Nodes (13): get_device_identity(), Detect if running on M1 or M2 and return identity dict., check_fear_greed_extreme(), check_funding_sentiment_divergence(), check_performance_divergence(), check_sentiment_velocity(), Detect when news/social sentiment disagrees with leverage (funding)., Detect contrarian signals from extreme Fear & Greed. (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (12): handle_anomaly(), handle_macro(), handle_orderflow_live(), handle_regime(), handle_sentiment(), Instantly write new sentiment to disk., Instantly write macro state to disk., Instantly write HMM regime to disk. (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (12): After Diagnosis, Bot Diagnostics Skill, Diagnostic Sequence (always in this order), Hard Limits, Step 1 — Process Check, Step 2 — API Check, Step 3 — Recent Log Check, Step 4 — Sentiment Freshness (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (12): Browser Extract Skill, Pre-configured Extractions, Process, Step 1 — Use Built-in Web Tools, Step 1b — Heavy Browser (via M2), Step 2 — Extract Clean Content, Step 3 — Structure The Output, Step 4 — Save Output (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.24
Nodes (9): fetch_binance_macro(), fetch_dxy_change(), main(), Fetches DXY daily percentage change from Yahoo Finance., Fetches BTC/USDT Funding Rate and Open Interest from Binance., publish(), publish_sync(), Publish a message to a NATS subject.     M2 calls this after every intelligence (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.24
Nodes (8): backup_all_databases(), cleanup_old_backups(), create_backup(), ensure_backup_dir(), Remove backups older than specified days, Create backup directory if it doesn't exist, Create a timestamped backup of a SQLite database          Args:         db_path:, Backup all known databases

### Community 16 - "Community 16"
Cohesion: 0.44
Nodes (9): backup_chromadb(), backup_constraints(), backup_models(), backup_sqlite_databases(), get_r2_client(), list_backups(), restore_latest_sqlite(), run_full_backup() (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.2
Nodes (9): Data Collection (fetch all, then synthesize), Market Analysis Skill, Output Format, Source 1 — Live Sentiment Score, Source 2 — Binance Funding Rate, Source 3 — Fear & Greed Index, Source 4 — CoinGecko Global, Source 5 — Bot Status (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.2
Nodes (9): Critical Rules, Phase 1 — Search Sources, Phase 2 — Extract Strategy Logic, Phase 3 — Rate Feasibility, Phase 4 — Present Top 3, Phase 5 — Implementation (only after confirmation), Research Process, Strategy Research Skill (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.22
Nodes (8): Code Fix Skill, Critical Rules, Process, Step 1 — Analyze Error, Step 2 — Verify Environment, Step 3 — Propose Fix, Step 4 — Validation, When I Activate

### Community 20 - "Community 20"
Cohesion: 0.36
Nodes (7): check_improvement(), load_training_data(), main_loop(), Compare new Sharpe vs current live strategy baseline.     Baseline stored in qnt, Continuous shadow optimization loop., Run Hyperopt for one strategy on recent data.     Returns result dict if success, run_shadow_hyperopt()

### Community 21 - "Community 21"
Cohesion: 0.33
Nodes (6): get_daily_report(), get_resource_snapshot(), monitor_continuously(), Aggregates last 24h of data into a report., Captures a snapshot of current system resources., Main monitoring loop.

### Community 23 - "Community 23"
Cohesion: 0.38
Nodes (6): fetch_binance_liquidation_ratio(), fetch_cvd_divergence(), Fetches Long/Short ratio and estimates liquidation pressure., Simplified CVD check using volume/price divergence logic., Fetch and save order flow state., update_state()

## Knowledge Gaps
- **197 isolated node(s):** `Publish a message to a NATS subject.     M2 calls this after every intelligence`, `Synchronous wrapper for publish.`, `Instantly write new sentiment to disk.`, `Instantly write macro state to disk.`, `Instantly write HMM regime to disk.` (+192 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_memory()` connect `Community 2` to `Community 0`, `Community 9`, `Community 3`?**
  _High betweenness centrality (0.238) - this node is a cross-community bridge._
- **Why does `check_calendar_risk_today()` connect `Community 2` to `Community 5`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `send_analytics_summary()` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `load_memory()` (e.g. with `risk_check()` and `autonomous_shield_check()`) actually correct?**
  _`load_memory()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `save_memory()` (e.g. with `risk_check()` and `autonomous_shield_check()`) actually correct?**
  _`save_memory()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `risk_check()` (e.g. with `load_memory()` and `save_memory()`) actually correct?**
  _`risk_check()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Publish a message to a NATS subject.     M2 calls this after every intelligence`, `Synchronous wrapper for publish.`, `Instantly write new sentiment to disk.` to the rest of the system?**
  _197 weakly-connected nodes found - possible documentation gaps or missing edges._