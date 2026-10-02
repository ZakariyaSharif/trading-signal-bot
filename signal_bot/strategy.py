"""Trend-following EMA-crossover strategy with three filters.

LONG when ALL are true on a closed candle:
  1. Fast EMA crosses above slow EMA          (momentum turns up)
  2. Close is above the trend EMA (200)        (trade with the big trend only)
  3. RSI between 50 and 70                     (momentum up, not overbought)
  4. ADX >= adx_min                            (market is trending, not choppy)
SHORT is the mirror image (RSI between 30 and 50, close below trend EMA).

Stop-loss   = entry -/+ ATR * stop_atr_mult
Take-profit = entry +/- stop distance * take_profit_rr

Win rate vs reward: a smaller take_profit_rr raises the win rate but each win pays less.
Profitability depends on expectancy, not win rate alone (see backtest.py).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .indicators import adx, atr, ema, rsi


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry: float
    stop_loss: float
    take_profit: float
    rsi: float
    adx: float
    timestamp: pd.Timestamp


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = ema(df["close"], cfg.ema_fast)
    df["ema_slow"] = ema(df["close"], cfg.ema_slow)
    df["ema_trend"] = ema(df["close"], cfg.ema_trend) if cfg.ema_trend else np.nan
    df["rsi"] = rsi(df["close"], cfg.rsi_period)
    df["atr"] = atr(df, cfg.atr_period)
    df["adx"] = adx(df, cfg.adx_period)

    above = df["ema_fast"] > df["ema_slow"]
    prev_above = above.shift(fill_value=False)
    prev_below = (df["ema_fast"] < df["ema_slow"]).shift(fill_value=False)
    crossed_up = above & ~prev_above
    crossed_down = (df["ema_fast"] < df["ema_slow"]) & ~prev_below

    # EMA trend needs enough history to be meaningful
    warm = pd.Series(np.arange(len(df)) >= max(cfg.ema_slow, cfg.ema_trend), index=df.index)
    ok = warm & df["rsi"].notna() & df["atr"].notna()
    if cfg.adx_min:
        ok &= df["adx"] >= cfg.adx_min
    trend_up = df["close"] > df["ema_trend"] if cfg.ema_trend else True
    trend_down = df["close"] < df["ema_trend"] if cfg.ema_trend else True

    long_ = ok & crossed_up & trend_up & df["rsi"].between(50, 70)
    short = ok & crossed_down & trend_down & df["rsi"].between(30, 50)
    df["signal"] = np.select([long_, short], ["LONG", "SHORT"], default="")
    return df


def signal_at(df: pd.DataFrame, i: int, symbol: str, cfg) -> Signal | None:
    """Signal on row i of a DataFrame from add_indicators(). Row i must be a closed candle."""
    if i < 0:
        return None
    cur = df.iloc[i]
    side = cur["signal"]
    if not side:
        return None
    entry = float(cur["close"])
    dist = float(cur["atr"]) * cfg.stop_atr_mult
    sign = 1 if side == "LONG" else -1
    return Signal(
        symbol, side, entry,
        stop_loss=entry - sign * dist,
        take_profit=entry + sign * dist * cfg.take_profit_rr,
        rsi=float(cur["rsi"]), adx=float(cur["adx"]), timestamp=df.index[i],
    )


def latest_signal(df: pd.DataFrame, symbol: str, cfg) -> Signal | None:
    """Signal on the last *closed* candle (the final row is still forming, so it is skipped)."""
    return signal_at(add_indicators(df, cfg), len(df) - 2, symbol, cfg)
