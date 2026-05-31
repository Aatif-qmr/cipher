VENV := .venv/bin
MATURIN := $(VENV)/maturin
PYTHON := $(VENV)/python3

.PHONY: rust rust-engine risk-checks test lint format help

## Build both Rust/PyO3 extensions (run after `uv sync --dev`)
rust: rust-engine risk-checks

rust-engine:
	@echo "Building rust_engine..."
	cd rust_engine && VIRTUAL_ENV=$(PWD)/.venv $(MATURIN) develop --release

risk-checks:
	@echo "Building risk_checks_rs..."
	cd risk/risk_checks_rs && VIRTUAL_ENV=$(PWD)/.venv $(MATURIN) develop --release

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	$(VENV)/ruff check .

format:
	$(VENV)/ruff format .

help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | awk -F: '{printf "  %-18s\n", $$1}'
