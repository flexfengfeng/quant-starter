PY ?= python3
export PYTHONPATH := src

.PHONY: help run validate audit orders size explain test clean

help:
	@echo "make run       backtest + audit + HTML report  (start here)"
	@echo "make validate  data contract checks"
	@echo "make audit     six self-deception probes only"
	@echo "make explain   today's factor percentiles"
	@echo "make orders    target orders for the paper account (no broker)"
	@echo "make size      how many names your capital can afford"
	@echo "make test      unit tests"

run: validate
	@$(PY) -m qs run

validate:
	@$(PY) -m qs validate

audit:
	@$(PY) -m qs audit

orders:
	@$(PY) -m qs orders

size:
	@$(PY) -m qs size

explain:
	@$(PY) -m qs explain

test:
	@$(PY) -m pytest -q

clean:
	@rm -rf reports .pytest_cache
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
