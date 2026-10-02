"""Simple backtest: python -m signal_bot.backtest BTC/USDT --limit 1000

Each signal is followed candle by candle until stop-loss or take-profit is hit.
If both are touched in the same candle, it counts as a loss (conservative).
Ignores fees, slippage and funding, so real results will be worse.
"""
import argparse

import pandas as pd

from .config import load_config
from .exchange import fetch_ohlcv, make_exchange
from .strategy import add_indicators, signal_at


def backtest(df: pd.DataFrame, symbol: str, cfg) -> list[dict]:
    df = add_indicators(df, cfg)
    trades, i = [], 1
    while i < len(df):
        sig = signal_at(df, i, symbol, cfg)
        if sig is None:
            i += 1
            continue
        result, exit_i = "OPEN", len(df) - 1
        for j in range(i + 1, len(df)):
            hi, lo = df["high"].iloc[j], df["low"].iloc[j]
            if sig.side == "LONG":
                hit_sl, hit_tp = lo <= sig.stop_loss, hi >= sig.take_profit
            else:
                hit_sl, hit_tp = hi >= sig.stop_loss, lo <= sig.take_profit
            if hit_sl or hit_tp:
                result, exit_i = ("LOSS" if hit_sl else "WIN"), j
                break
        r = {"WIN": cfg.take_profit_rr, "LOSS": -1.0, "OPEN": 0.0}[result]
        trades.append({"time": sig.timestamp, "side": sig.side, "entry": sig.entry, "result": result, "R": r})
        i = exit_i + 1  # one trade at a time
    return trades


def summarize(trades: list[dict]) -> str:
    closed = [t for t in trades if t["result"] != "OPEN"]
    if not closed:
        return "No closed trades."
    wins = sum(t["result"] == "WIN" for t in closed)
    total_r = sum(t["R"] for t in closed)
    return (
        f"Trades: {len(closed)} | Win rate: {wins / len(closed):.1%} | "
        f"Total: {total_r:+.1f}R | Avg: {total_r / len(closed):+.2f}R per trade"
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol")
    p.add_argument("--limit", type=int, default=1000)
    args = p.parse_args()
    cfg = load_config()
    df = fetch_ohlcv(make_exchange(cfg.exchange), args.symbol, cfg.timeframe, args.limit)
    trades = backtest(df.iloc[:-1], args.symbol, cfg)  # drop the still-forming candle
    for t in trades:
        print(f"{t['time']:%Y-%m-%d %H:%M} {t['side']:5} {t['entry']:>12.6g} {t['result']}")
    print(summarize(trades))


if __name__ == "__main__":
    main()
