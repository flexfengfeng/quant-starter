PY ?= python3
export PYTHONPATH := src

.PHONY: help run validate audit orders size explain test clean

help:
	@echo "make run       backtest + audit + HTML report  /  回测 + 自检 + 报告  (start here / 从这里开始)"
	@echo "make validate  data contract checks  /  数据契约检查"
	@echo "make audit     six self-deception probes  /  六项自欺检查"
	@echo "make explain   today's factor percentiles  /  今日因子百分位"
	@echo "make orders    target orders, paper only  /  纸面目标订单（不连券商）"
	@echo "make size      how many names your capital can afford  /  资金能养几个仓位"
	@echo "make test      unit tests  /  单元测试"

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
