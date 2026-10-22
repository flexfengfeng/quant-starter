"""quant-starter — a small, honest, reproducible personal quant system.

Four layers, each replaceable on its own:

    pipeline/   raw data -> validated panel -> point-in-time features
    strategy/   features -> cross-sectional scores -> target portfolio
    backtest/   target portfolio -> equity curve + an honest audit
    live/       target portfolio -> orders on a paper account

Read ``LEARNING_PATH.md`` for the order in which to open them.
"""

__version__ = "0.1.0"
