# JULES DAILY DEVELOPMENT SCHEDULE & COMMIT PROTOCOL

## Overview
This document defines the daily development schedule and commit protocol for Jules (Google's AI assistant) to maintain continuous improvement of the cipher trading bot project.

**IMPORTANT: How to Instruct Jules**

When giving instructions to Jules (Google's AI coding agent), follow these principles:

1. **Be Specific and Actionable**: Use clear verbs and specific file paths
2. **Provide Context**: Reference existing documentation and project goals
3. **Set Measurable Goals**: Define exact commit counts, time blocks, and deliverables
4. **Include Verification Steps**: Specify how to validate completion
5. **Reference Project Standards**: Link to AGENTS.md, ARCHITECTURE_PRINCIPLES.md, etc.

### Example Instruction Format for Jules:
```
Jules, execute the daily development protocol from JULES_SCHEDULE.md:
1. Complete minimum 50 commits today (target: 57 commits - differs from yesterday's 52)
2. Focus areas: [specific modules/features]
3. Follow commit message format from section "Commit Quality Standards"
4. Run verification checklist before EOD
5. Document all new features in README.md
```

---

## Core Requirements

### 1. Daily Commit Target
- **Minimum commits per day:** 50 commits
- **Constraint:** No two consecutive days may have the same number of commits
- **Recommended variation pattern:** Use a rotating sequence (e.g., 50, 55, 52, 58, 51, 60, 53...)
- **Tracking:** Log daily commit count in a dedicated file `.commit_log.md`

### 2. Daily Improvement Mandate
Every day must include:
- At least one new feature or enhancement
- Code quality improvements (refactoring, optimization, documentation)
- Bug fixes or edge case handling
- Test coverage additions

---

## Automated Daily Instruction Template for Jules

### Morning Activation Command
```
Jules, begin daily development cycle [DATE]:

TODAY'S TARGETS:
- Commit count: [X] commits (yesterday was [Y], must differ)
- Primary focus: [module/feature area]
- Secondary focus: [backup area if blocked]

MANDATES:
1. Implement at least 2 new features from Feature Priority Queue
2. Add minimum 5 test commits
3. Complete 3 documentation commits
4. Run full test suite after every 10 commits

COMMIT DISTRIBUTION:
- Block 1 (Strategies): [X*0.25] commits
- Block 2 (Intelligence): [X*0.25] commits
- Block 3 (Infrastructure): [X*0.20] commits
- Block 4 (Risk/Automation): [X*0.20] commits
- Tests/Docs: [X*0.10] commits

VERIFICATION:
- Log commit count to .commit_log.md
- Push to remote before EOD
- Update DEVELOPMENT.md changelog section
```

### Mid-Day Check-In Command
```
Jules, report progress:
1. Current commit count: [check git log --since="today"]
2. Features completed vs planned
3. Any blockers requiring human intervention
4. Adjusted plan for remaining blocks if needed
```

### End-of-Day Wrap-Up Command
```
Jules, complete daily cycle:
1. Final commit count verification (target: [X])
2. Run: uv run pytest && uv run ruff check .
3. Update .commit_log.md with today's count and summary
4. Create tomorrow's target commit number (must differ from today)
5. Push all changes to origin/main
6. Generate daily summary in DEVELOPMENT.md
```

---

## Commit Log Template (.commit_log.md)

Create and maintain this file in the project root:

```markdown
# Daily Commit Log

| Date | Commit Count | Key Features | Notes |
|------|--------------|--------------|-------|
| YYYY-MM-DD | XX | feature1, feature2 | brief note |
| YYYY-MM-DD | YY | feature3, feature4 | brief note |

## Weekly Summary
- Week [N]: Average [Z] commits/day
- Total features shipped: [M]
- Technical debt addressed: [K] items
```

---

## Daily Schedule Template

### Morning Session (Planning & Analysis)
1. **Review previous day's changes** (15 min)
   - Check git log for last session
   - Verify all tests pass
   - Review any CI/CD feedback

2. **Market & Feature Research** (30 min)
   - Check latest trading patterns/strategies
   - Review financial data sources (ForexFactory, alternative.me fear/greed)
   - Identify new indicators or signals to implement

3. **Task Planning** (15 min)
   - Define 5-7 discrete features/improvements for the day
   - Break each into atomic commits (target: 7-10 commits per feature area)
   - Prioritize by impact and complexity

### Development Sessions (4 blocks)

#### Block 1: Core Strategy Improvements (90 min)
- Focus: `strategies/active/`, `indicators/`
- Expected commits: 12-15
- Examples:
  - Add new technical indicator
  - Refactor entry/exit logic
  - Optimize parameter ranges
  - Add strategy-specific tests

#### Block 2: Intelligence Layer Enhancements (90 min)
- Focus: `qnt/`, `qnt/oracle/`, `qnt/vault/`, `qnt/memory/`
- Expected commits: 12-15
- Examples:
  - Improve pattern recognition
  - Enhance vector search (rust_engine integration)
  - Add new memory persistence features
  - Update hyperopt configurations

#### Block 3: Infrastructure & Bus (60 min)
- Focus: `bus/`, `mcp/`, `config/`
- Expected commits: 10-12
- Examples:
  - Add new event types
  - Improve MCP tools
  - Enhance async messaging
  - Update configuration schemas

#### Block 4: Risk, Sentiment & Automation (60 min)
- Focus: `risk/`, `sentiment/`, `automation/`
- Expected commits: 10-12
- Examples:
  - Refine stake sizing algorithms
  - Add sentiment data sources
  - Improve correlation guards
  - Enhance reporting automation

### Evening Session (Testing & Documentation)
1. **Full Test Suite** (30 min)
   - Run: `uv run pytest`
   - Run: `uv run ruff check .`
   - Fix any failures immediately

2. **Documentation Updates** (20 min)
   - Update README.md if features changed
   - Add docstrings to new functions
   - Update AGENTS.md if agent policies changed

3. **Commit Audit** (10 min)
   - Verify commit count meets daily target
   - Ensure commit messages are clear and descriptive
   - Confirm no consecutive-day commit count duplication

---

## Commit Quality Standards

### Commit Message Format
```
<type>(<scope>): <subject>

<body - optional>

<footer - optional>
```

**Types:** feat, fix, docs, style, refactor, test, chore, perf, ci, build

**Examples:**
```
feat(indicators): add RSI divergence detection
fix(strategies): handle edge case in ScalpV1 exit logic
refactor(bus): simplify event channel subscription pattern
test(qnt): add unit tests for VectorVaultV1 recall accuracy
docs(readme): update quickstart with new environment variables
perf(rust_engine): optimize euclidean distance calculation with AVX2
```

### Atomic Commit Principles
- Each commit should represent one logical change
- Commits should compile and pass tests independently
- Avoid mixing unrelated changes in single commits
- Keep commits small enough to review in <5 minutes

---

## Best Practices for Instructing Jules

### DO:
- ✅ Give specific, measurable targets (e.g., "57 commits focusing on strategies and tests")
- ✅ Reference existing project files and documentation
- ✅ Provide clear priority ordering for tasks
- ✅ Include verification commands Jules should run
- ✅ Specify the commit message format to use
- ✅ Set time boundaries for each work block
- ✅ Ask for progress reports at checkpoints

### DON'T:
- ❌ Give vague instructions like "improve the code"
- ❌ Forget to mention the consecutive-day commit count rule
- ❌ Skip mentioning test requirements
- ❌ Assume Jules knows the current state without checking
- ❌ Request breaking changes without migration planning

### Sample Complete Daily Instruction:

```
Jules, execute today's development cycle (2026-01-15):

CONTEXT:
- Yesterday: 52 commits (see .commit_log.md)
- Today's target: 58 commits (must differ from yesterday)
- Current branch: main, last sync: this morning

PRIMARY OBJECTIVES:
1. Add MACD divergence detection to indicators/technical/
2. Refactor strategy entry logic in strategies/active/ScalpV1.py
3. Expand MCP tools for better browser automation
4. Add 10 new unit tests for qnt/vault/ module

COMMIT BREAKDOWN:
- Features: 35 commits (atomic, one feature per commit)
- Tests: 12 commits (grouped by module)
- Docs: 6 commits (docstrings + README updates)
- Refactoring: 5 commits (small, focused improvements)

QUALITY GATES:
- Run `uv run pytest` after every 10 commits
- Run `uv run ruff check .` before final push
- All new functions must have docstrings
- No breaking changes without DEPRECATED comments

END OF DAY:
1. Verify 58+ commits in git log --since="2026-01-15 00:00"
2. Update .commit_log.md with summary
3. Push to origin/main
4. Post daily summary in DEVELOPMENT.md changelog

Begin now and report back after Block 1 completion.
```

---

## Weekly Commit Variation Schedule

To ensure no consecutive days have identical commit counts, use this rotating pattern:

| Week | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 | Day 6 | Day 7 |
|------|-------|-------|-------|-------|-------|-------|-------|
| A    | 52    | 57    | 51    | 60    | 54    | 58    | 53    |
| B    | 55    | 51    | 59    | 52    | 56    | 50    | 61    |
| C    | 50    | 56    | 53    | 58    | 51    | 55    | 59    |
| D    | 58    | 52    | 55    | 50    | 57    | 54    | 51    |

**Note:** Adjust based on actual development velocity, but always maintain the non-consecutive rule.

---

## Feature Priority Queue

### High Priority (Daily Focus)
1. Strategy performance optimization
2. New signal/indicator development
3. Risk management enhancements
4. Backtesting accuracy improvements

### Medium Priority (Weekly Goals)
1. MCP tool expansions
2. Sentiment analysis pipeline improvements
3. Memory/persistence optimizations
4. Automation and reporting features

### Low Priority (As Time Permits)
1. Documentation polish
2. Code cleanup and refactoring
3. CI/CD pipeline enhancements
4. Developer experience improvements

---

## Verification Checklist (End of Day)

- [ ] Minimum 50 commits completed
- [ ] Commit count differs from previous day
- [ ] All tests passing (`uv run pytest`)
- [ ] Linting clean (`uv run ruff check .`)
- [ ] At least one new feature implemented
- [ ] Documentation updated where needed
- [ ] No breaking changes without migration notes
- [ ] Git history shows logical progression

---

## Special Considerations

### When Blocked
If unable to complete planned features:
1. Increase granularity of commits (smaller atomic changes)
2. Add more test cases as separate commits
3. Improve documentation with detailed commits
4. Refactor existing code with focused commits

### High-Impact Days
On days with major feature launches:
- Commit count may exceed 70+
- Still maintain atomic commit principles
- Document breaking changes prominently

### Maintenance Days
When focusing on stability:
- Emphasize test coverage commits
- Add profiling/benchmarking commits
- Document technical debt and TODOs
- Refactor with safety-focused commits

---

## Integration with Existing Workflows

### Before Starting Bot
```bash
# Verify current state
git status
git log --oneline -10
uv run pytest -q
./start_bot.sh
```

### After Development Session
```bash
# Stage and commit incrementally
git add -p
git commit -m "feat(scope): description"
# Repeat for each atomic change
```

### End of Day
```bash
# Final verification
git log --since="today" --oneline | wc -l  # Count today's commits
uv run pytest
uv run ruff check .
git push origin main
```

---

## Contact & Escalation

If uncertain about:
- Feature direction → Review `cipher_project_dossier.md`
- Architecture decisions → Consult `ARCHITECTURE_PRINCIPLES.md`
- Agent behavior → Follow `AGENTS.md` policies
- Development setup → See `DEVELOPMENT.md`

---

*Last Updated: $(date +%Y-%m-%d)*
*Version: 1.0*
*Next Review: Weekly*