"""EMA-crossover strategy with an RSI filter and ATR-based risk levels.

LONG:  fast EMA crosses above slow EMA and RSI is between 50 and 70
       (momentum is up but the market is not yet overbought).
SHORT: fast EMA crosses below slow EMA and RSI is between 30 and 50.

Stop-loss = entry -/+ ATR * stop_atr_mult
Take-profit = entry +/- (stop distance * take_profit_rr)
"""
from dataclasses import dataclass

import pandas as pd

from .indicators import atr, ema, rsi


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry: float
    stop_loss: float
    take_profit: float
    rsi: float
    timestamp: pd.Timestamp


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = ema(df["close"], cfg.ema_fast)
    df["ema_slow"] = ema(df["close"], cfg.ema_slow)
    df["rsi"] = rsi(df["close"], cfg.rsi_period)
    df["atr"] = atr(df, cfg.atr_period)
    return df


def signal_at(df: pd.DataFrame, i: int, symbol: str, cfg) -> Signal | None:
    """Check row i of a DataFrame that already has indicators. i must be a closed candle."""
    if i < 1:
        return None
    prev, cur = df.iloc[i - 1], df.iloc[i]
    if pd.isna(cur["rsi"]) or pd.isna(cur["atr"]) or pd.isna(prev["ema_slow"]):
        return None

    crossed_up = prev["ema_fast"] <= prev["ema_slow"] and cur["ema_fast"] > cur["ema_slow"]
    crossed_down = prev["ema_fast"] >= prev["ema_slow"] and cur["ema_fast"] < cur["ema_slow"]

    entry = float(cur["close"])
    stop_dist = float(cur["atr"]) * cfg.stop_atr_mult
    if crossed_up and 50 <= cur["rsi"] <= 70:
        side, sl, tp = "LONG", entry - stop_dist, entry + stop_dist * cfg.take_profit_rr
    elif crossed_down and 30 <= cur["rsi"] <= 50:
        side, sl, tp = "SHORT", entry + stop_dist, entry - stop_dist * cfg.take_profit_rr
    else:
        return None

    return Signal(symbol, side, entry, sl, tp, float(cur["rsi"]), df.index[i])


def latest_signal(df: pd.DataFrame, symbol: str, cfg) -> Signal | None:
    """Signal on the last *closed* candle (the final row is still forming, so it is skipped)."""
    df = add_indicators(df, cfg)
    return signal_at(df, len(df) - 2, symbol, cfg)
