---
name: code-fix
description: Diagnose and fix code errors and dependency issues
triggers:
  - fix error
  - debug
  - solve problem
  - patch
  - ModuleNotFoundError
  - AttributeError
  - TypeError
  - SyntaxError
  - fix this
  - code fix
model: gemini-3.1-pro-preview-customtools
---

# Code Fix Skill

## When I Activate
User provides an error message, stack trace, or asks to fix a specific bug in the code.

## Process

### Step 1 — Analyze Error
1. Identify the error type (e.g., `ModuleNotFoundError`).
2. Identify the failing module or file.
3. Search for the error in the project's `logs/` directory for full context.

### Step 2 — Verify Environment
- Check `venv/` status.
- Check `requirements.txt` for missing dependencies.
- Run `pip show <package>` to verify installation.

### Step 3 — Propose Fix
1. For **Missing Dependencies**:
   - Command: `pip install <package>`
   - Update: `pip freeze > requirements.txt`
2. For **Logic Bugs**:
   - Provide exact diff for the failing file.
   - Explain the "Why" behind the fix.

### Step 4 — Validation
1. Apply the fix.
2. Run relevant tests (e.g., `run_sentiment_tests.py` or strategy backtests).
3. Verify the error no longer appears in logs.

## Critical Rules
- Never use `--force` on pip installs without reason.
- Always update `requirements.txt` after adding a package.
- Ensure fixes follow the project's Python coding standards.
