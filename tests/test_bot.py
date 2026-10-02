import numpy as np
import pandas as pd

from signal_bot.backtest import backtest, summarize
from signal_bot.config import Config
from signal_bot.indicators import atr, rsi
from signal_bot.strategy import add_indicators, signal_at
from signal_bot.telegram import DISCLAIMER, format_signal

CFG = Config("", "", "binance", ["BTC/USDT"], "4h", 3, 6, 5, 5, 1.5, 2.0, 60, True)


def make_df(closes):
    closes = np.asarray(closes, dtype=float)
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="4h", tz="UTC")
    return pd.DataFrame(
        {"open": closes, "high": closes + 1, "low": closes - 1, "close": closes, "volume": 1.0}, index=idx
    )


def test_rsi_bounds_and_extremes():
    up = rsi(pd.Series(np.arange(1, 50, dtype=float)), 14)
    assert up.dropna().eq(100).all()
    down = rsi(pd.Series(np.arange(50, 1, -1, dtype=float)), 14)
    assert down.dropna().lt(1).all()


def test_atr_constant_range():
    df = make_df([100.0] * 30)
    assert atr(df, 5).iloc[-1] == 2.0


def test_long_signal_on_bullish_cross():
    # Downtrend then a moderate recovery -> fast EMA crosses above slow
    closes = list(np.linspace(120, 100, 20)) + list(np.linspace(100, 106, 8))
    df = add_indicators(make_df(closes), CFG)
    sigs = [s for i in range(len(df)) if (s := signal_at(df, i, "BTC/USDT", CFG))]
    assert sigs and sigs[0].side == "LONG"
    s = sigs[0]
    assert s.stop_loss < s.entry < s.take_profit
    assert abs((s.take_profit - s.entry) - 2 * (s.entry - s.stop_loss)) < 1e-9


def test_backtest_runs_and_summarizes():
    rng = np.random.default_rng(0)
    closes = 100 + np.cumsum(rng.normal(0, 1, 500))
    trades = backtest(make_df(closes), "BTC/USDT", CFG)
    assert all(t["result"] in {"WIN", "LOSS", "OPEN"} for t in trades)
    assert isinstance(summarize(trades), str)


def test_message_has_disclaimer():
    closes = list(np.linspace(120, 100, 20)) + list(np.linspace(100, 106, 8))
    df = add_indicators(make_df(closes), CFG)
    sig = next(s for i in range(len(df)) if (s := signal_at(df, i, "BTC/USDT", CFG)))
    assert DISCLAIMER in format_signal(sig, "4h")
