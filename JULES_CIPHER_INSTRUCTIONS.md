# Jules Daily Development Instructions - Cipher Trading Bot Project

## Executive Summary

This document provides complete instructions for Jules (Google's AI coding agent) to maintain daily development of the Cipher cryptocurrency trading bot project with **minimum 50 commits per day**, ensuring no two consecutive days have the same commit count, while continuously improving the codebase.

---

## Part 1: Understanding Jules

### What is Jules?
Jules is Google's AI-powered coding assistant that can:
- Read and understand entire codebases
- Execute multi-step development tasks
- Make atomic, well-documented commits
- Run tests and verification commands
- Follow complex scheduling protocols

### How to Communicate with Jules
Jules responds best to:
1. **Clear, specific commands** with measurable outcomes
2. **Context references** to existing documentation
3. **Step-by-step breakdowns** of complex tasks
4. **Verification requirements** for quality assurance
5. **Time-bounded work blocks** for focused development

---

## Part 2: Project Context - Cipher Trading Bot

### Project Overview
Cipher is a sophisticated cryptocurrency trading system featuring:
- **8 active strategies**: ScalpV1, MeanReversionV1, TrendFollowV1, SwingV1, BearScalpV1, DailyTrendV1, MicroScalpV1, VectorVaultV1
- **Multi-layer risk management**: Drawdown limits, correlation guards, stake sizing
- **AI/ML integration**: FreqAI, vector search (Rust), sentiment analysis (FinBERT/CryptoBERT)
- **Regime detection**: 3-state HMM (BULL/BEAR/RANGING)
- **Event-driven architecture**: NATS message bus, MCP server for AI agent access
- **Automation suite**: Health checks, reporting, self-healing

### Key Directories
```
/workspace/
├── strategies/active/      # Live trading strategies
├── indicators/             # Technical indicators (Polaris-accelerated)
├── qnt/                    # Quantitative intelligence layer
│   ├── oracle/            # HMM regime detector, macro oracle
│   ├── vault/             # Trade memory (Qdrant vector DB)
│   ├── memory/            # Learning persistence
│   └── skills/            # AI agent capabilities
├── risk/                   # Risk management (drawdown, stake sizing)
├── sentiment/              # News/reddit sentiment pipeline
├── bus/                    # Event bus (NATS publishers/consumers)
├── mcp/                    # Model Context Protocol server
├── automation/             # Scheduled jobs, health checks
├── rust_engine/            # High-performance Rust extensions
└── config/                 # Strategy configs, supervisord, credentials
```

### Critical Files to Reference
- `cipher_project_dossier.md` - Complete project technical specification
- `ARCHITECTURE_PRINCIPLES.md` - System design guidelines
- `AGENTS.md` - AI agent behavior policies
- `DEVELOPMENT.md` - Development workflow documentation
- `README.md` - Project overview and quickstart

---

## Part 3: Daily Commit Protocol

### Core Rules

#### Rule 1: Minimum 50 Commits Per Day
- Every development day must have **at least 50 git commits**
- Commits must be atomic and meaningful (not artificially split)
- Each commit should represent one logical change

#### Rule 2: No Consecutive Duplicate Counts
- If yesterday had 52 commits, today cannot have 52
- Use the weekly rotation schedule (see below) or choose a different number
- Track daily counts in `.commit_log.md`

#### Rule 3: Daily Improvement Mandate
Every session must include:
- ✅ At least 1 new feature or enhancement
- ✅ Code quality improvements (refactoring, optimization)
- ✅ Bug fixes or edge case handling
- ✅ Test coverage additions
- ✅ Documentation updates

### Weekly Commit Rotation Schedule

Use this pattern to ensure variation:

| Week | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|------|-----|-----|-----|-----|-----|-----|-----|
| A    | 52  | 57  | 51  | 60  | 54  | 58  | 53  |
| B    | 55  | 51  | 59  | 52  | 56  | 50  | 61  |
| C    | 50  | 56  | 53  | 58  | 51  | 55  | 59  |
| D    | 58  | 52  | 55  | 50  | 57  | 54  | 51  |

**Before starting each day:** Check `.commit_log.md` for yesterday's count and select a different target.

---

## Part 4: Daily Schedule Template

### Morning Session (Planning & Setup) - 60 minutes

#### Step 1: State Verification (15 min)
```bash
# Check git status and recent history
git status
git log --oneline -20
git log --since="yesterday" --oneline | wc -l

# Verify test suite passes
uv run pytest -q

# Check current branch and sync status
git branch
git remote -v
```

#### Step 2: Research & Planning (30 min)
- Review market conditions and trading patterns
- Check ForexFactory calendar for economic events
- Review alternative.me fear/greed index
- Identify 5-7 discrete features/improvements for today
- Break each feature into 7-10 atomic commits

#### Step 3: Task Queue Creation (15 min)
Create today's task list prioritized by impact.

### Development Blocks (4 sessions) - 5 hours total

#### Block 1: Core Strategy Improvements (90 min) - Target: 12-15 commits
**Focus Areas:** `strategies/active/`, `indicators/`

Example Tasks:
- Add new technical indicator (3-4 commits)
- Refactor entry/exit logic (4-5 commits)
- Optimize parameter ranges (3-4 commits)
- Strategy-specific tests (2-3 commits)

#### Block 2: Intelligence Layer Enhancements (90 min) - Target: 12-15 commits
**Focus Areas:** `qnt/`, `qnt/oracle/`, `qnt/vault/`, `qnt/memory/`

Example Tasks:
- Improve pattern recognition (4-5 commits)
- Enhance vector search (3-4 commits)
- Memory persistence features (3-4 commits)
- Hyperopt configurations (2-3 commits)

#### Block 3: Infrastructure & Bus (60 min) - Target: 10-12 commits
**Focus Areas:** `bus/`, `mcp/`, `config/`

Example Tasks:
- Add new event types (3-4 commits)
- Improve MCP tools (3-4 commits)
- Async messaging enhancements (2-3 commits)
- Configuration schema updates (2-3 commits)

#### Block 4: Risk, Sentiment & Automation (60 min) - Target: 10-12 commits
**Focus Areas:** `risk/`, `sentiment/`, `automation/`

Example Tasks:
- Stake sizing algorithms (3-4 commits)
- Sentiment data sources (3-4 commits)
- Correlation guards (2-3 commits)
- Reporting automation (2-3 commits)

### Evening Session (Testing & Documentation) - 60 minutes

#### Step 1: Full Test Suite (30 min)
```bash
uv run pytest
uv run ruff check .
```

#### Step 2: Documentation Updates (20 min)
- Update `README.md` if user-facing features changed
- Add docstrings to all new public functions/classes
- Update `DEVELOPMENT.md` changelog section

#### Step 3: Commit Audit (10 min)
```bash
git log --since="today 00:00" --oneline | wc -l
```

---

## Part 5: Commit Quality Standards

### Commit Message Format
Follow Conventional Commits specification:
```
<type>(<scope>): <subject>

<body - optional>

<footer - optional>
```

### Commit Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance
- `perf`: Performance
- `ci`: CI/CD
- `build`: Build system

### Good Commit Examples
```
feat(indicators): add RSI divergence detection

Implement bullish and bearish RSI divergence detection using
local extrema identification over configurable lookback period.

Closes #142
```

### Atomic Commit Principles
✅ DO: One logical change per commit, compiles independently, reviewable in <5 min
❌ DON'T: Mix unrelated changes, commit broken code, use vague messages

---

## Part 6: Instruction Templates for Jules

### Template 1: Morning Activation Command

```
Jules, begin daily development cycle for [DATE]:

CONTEXT:
- Yesterday's commit count: [XX] (see .commit_log.md)
- Today's target: [YY] commits (must differ from yesterday)
- Current branch: [branch_name], last sync: [timestamp]

PRIMARY OBJECTIVES:
1. [Feature 1]: Brief description (~X commits)
2. [Feature 2]: Brief description (~X commits)
3. [Enhancement]: Brief description (~X commits)

COMMIT DISTRIBUTION:
- Block 1 (Strategies/Indicators): [YY*0.25] commits
- Block 2 (Intelligence/qnt): [YY*0.25] commits
- Block 3 (Infrastructure/bus/mcp): [YY*0.20] commits
- Block 4 (Risk/Sentiment/Automation): [YY*0.20] commits
- Tests/Docs: [YY*0.10] commits

QUALITY GATES:
- Run uv run pytest after every 10 commits
- Run uv run ruff check . before final push
- All new functions must have docstrings
- Commit messages must follow Conventional Commits format

END OF DAY DELIVERABLES:
1. Verify [YY]+ commits
2. Update .commit_log.md
3. Push to origin/main
4. Post summary in DEVELOPMENT.md
5. Set tomorrow's target (must differ)

Begin with Block 1 and report back after completion.
```

### Template 2: Mid-Day Check-In Command

```
Jules, report progress on daily cycle:

1. Current commit count
2. Features completed vs planned
3. Any blockers
4. Adjusted plan for remaining blocks
5. Estimated completion time

Continue with next block after reporting.
```

### Template 3: End-of-Day Wrap-Up Command

```
Jules, complete daily development cycle:

FINAL VERIFICATION:
1. Count commits: git log --since="today 00:00" --oneline | wc -l
2. Run quality checks: uv run pytest && uv run ruff check .
3. Update .commit_log.md with summary
4. Push to origin/main
5. Generate summary of features, tests, docs, breaking changes

Daily cycle complete.
```

---

## Part 7: Tracking & Verification

### .commit_log.md Template

Maintain this file with:
- Date, commit count, key features, notes
- Weekly summaries
- Monthly goals
- Quick git commands

### End-of-Day Verification Checklist

- [ ] Minimum 50 commits completed
- [ ] Commit count differs from previous day
- [ ] All tests passing (uv run pytest)
- [ ] Linting clean (uv run ruff check .)
- [ ] At least one new feature implemented
- [ ] Documentation updated
- [ ] No breaking changes without migration notes
- [ ] .commit_log.md updated
- [ ] Changes pushed to origin/main

---

## Part 8: Best Practices

### DO ✅
1. Give specific, measurable targets
2. Reference existing project files
3. Provide clear priority ordering
4. Include verification commands
5. Specify commit message format
6. Set time boundaries
7. Ask for progress reports

### DON'T ❌
1. Give vague instructions
2. Forget the consecutive-day rule
3. Skip test requirements
4. Assume state knowledge
5. Request breaking changes without planning
6. Sacrifice quality for quantity

---

## Part 9: Special Scenarios

### When Blocked
1. Increase commit granularity
2. Shift focus to tests/docs/refactoring
3. Add diagnostic commits
4. Request human intervention if needed

### High-Impact Days
- Expect 70+ commits
- Document breaking changes prominently
- Coordinate with bot operation

### Maintenance Days
- Emphasize test coverage
- Add profiling/benchmarking commits
- Document technical debt
- Refactor with safety focus

---

## Part 10: Quick Reference

### Daily Commands
```
MORNING: "Jules, begin daily cycle [DATE]: Target [XX] commits (yesterday: [YY])"
MID-DAY: "Jules, progress report: count, completed, blockers, plan"
EVENING: "Jules, complete cycle: verify, test, update log, push"
```

### Commit Types
```
feat(scope): New feature
fix(scope): Bug fix
docs(scope): Documentation
refactor(scope): Code restructuring
test(scope): Adding tests
perf(scope): Performance improvement
```

### Common Scopes
```
strategies, indicators, risk, sentiment, qnt, bus, mcp, config, automation, rust_engine, tests, docs
```

---

## Part 11: Example Complete Day

### Sample Instruction
```
Jules, execute daily development cycle for 2026-01-20:

CONTEXT:
- Yesterday: 54 commits
- Today's target: 59 commits (differs ✓)
- Branch: main, synced at 08:00 UTC

OBJECTIVES:
1. Add Bollinger Band width indicator (~5 commits)
2. Implement dynamic stake adjustment (~6 commits)
3. Enhance MCP tools (~5 commits)
4. Add qnt/oracle tests (~8 commits)
5. Refactor sentiment pipeline (~6 commits)
6. Performance optimizations (~7 commits)
7. Bug fixes (~7 commits)
8. Additional tests (~6 commits)
9. Documentation (~4 commits)

QUALITY GATES:
✓ pytest after every 10 commits
✓ ruff before push
✓ All functions documented
✓ Conventional Commits format

MILESTONES:
- 10:30: Block 1 complete, report
- 13:00: Block 2 complete, report
- 15:00: Block 3 complete
- 17:00: Block 4 complete
- 18:00: Final verification and push

BEGIN NOW.
```

---

## Conclusion

This document provides comprehensive instructions for Jules to maintain daily development of the Cipher trading bot project with:

1. **Consistency**: 50+ commits every day with variation
2. **Quality**: Atomic commits with clear messages and tests
3. **Progress**: Continuous improvement of the codebase
4. **Documentation**: Comprehensive tracking and changelogs
5. **Verification**: Automated checks and quality gates

**Document Version**: 1.0
**Last Updated**: 2026-01-20
**Next Review**: Weekly

For questions, refer to:
- `cipher_project_dossier.md` - Technical specifications
- `ARCHITECTURE_PRINCIPLES.md` - Design guidelines
- `AGENTS.md` - Agent behavior policies
- `DEVELOPMENT.md` - Development workflows
