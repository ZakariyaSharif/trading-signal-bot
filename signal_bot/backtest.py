"""Backtest: python -m signal_bot.backtest BTC/USDT ETH/USDT --candles 3000

Each signal is followed candle by candle until stop-loss or take-profit is hit.
If both are touched in the same candle, it counts as a LOSS (conservative).
Fees + slippage (FEE_PCT) are subtracted from every trade.

Results are in R (1R = the amount risked on a trade). Key numbers:
  win rate       share of trades that hit take-profit
  expectancy     average R per trade after fees  -> must be > 0 to make money
  profit factor  gross wins / gross losses       -> > 1.2 is decent, > 1.5 is good
  max drawdown   worst peak-to-trough losing streak, in R
"""
import argparse
from dataclasses import dataclass

import pandas as pd

from .config import load_config
from .exchange import fetch_history, make_exchange
from .strategy import add_indicators, signal_at


def outcome(side: str, stop_loss: float, take_profit: float, high: float, low: float) -> str | None:
    """WIN / LOSS if this candle hit a level, else None. Both hit -> LOSS."""
    if side == "LONG":
        hit_sl, hit_tp = low <= stop_loss, high >= take_profit
    else:
        hit_sl, hit_tp = high >= stop_loss, low <= take_profit
    if hit_sl:
        return "LOSS"
    return "WIN" if hit_tp else None


def trade_r(result: str, entry: float, stop_loss: float, cfg) -> float:
    fee_r = entry * cfg.fee_pct / 100 / abs(entry - stop_loss)
    return (cfg.take_profit_rr if result == "WIN" else -1.0) - fee_r


def backtest(df: pd.DataFrame, symbol: str, cfg) -> list[dict]:
    df = add_indicators(df, cfg)
    highs, lows = df["high"].to_numpy(), df["low"].to_numpy()
    n, trades, free_from = len(df), [], 0
    for i in (df["signal"] != "").to_numpy().nonzero()[0]:
        if i < free_from:  # one trade at a time per symbol
            continue
        sig = signal_at(df, i, symbol, cfg)
        result = None
        for j in range(i + 1, n):
            result = outcome(sig.side, sig.stop_loss, sig.take_profit, highs[j], lows[j])
            if result:
                break
        if not result:  # still open at the end of the data
            break
        trades.append({"time": sig.timestamp, "symbol": symbol, "side": sig.side, "entry": sig.entry,
                       "result": result, "R": trade_r(result, sig.entry, sig.stop_loss, cfg)})
        free_from = j + 1
    return trades


@dataclass
class Stats:
    trades: int
    win_rate: float
    expectancy: float
    profit_factor: float
    total_r: float
    max_dd: float

    def __str__(self) -> str:
        return (f"Trades: {self.trades} | Win rate: {self.win_rate:.1%} | Expectancy: {self.expectancy:+.3f}R"
                f" | Profit factor: {self.profit_factor:.2f} | Total: {self.total_r:+.1f}R"
                f" | Max drawdown: {self.max_dd:.1f}R")


def stats(trades: list[dict]) -> Stats:
    if not trades:
        return Stats(0, 0.0, 0.0, 0.0, 0.0, 0.0)
    trades = sorted(trades, key=lambda t: t["time"])
    rs = pd.Series([t["R"] for t in trades])
    gains, losses = rs[rs > 0].sum(), -rs[rs < 0].sum()
    equity = rs.cumsum()
    max_dd = float((equity.cummax().clip(lower=0) - equity).max())
    wins = sum(t["result"] == "WIN" for t in trades)
    return Stats(len(rs), wins / len(rs), float(rs.mean()),
                 float(gains / losses) if losses else float("inf"), float(rs.sum()), max_dd)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbols", nargs="*")
    p.add_argument("--candles", type=int, default=3000)
    p.add_argument("--list", action="store_true", help="print every trade")
    args = p.parse_args()
    cfg = load_config()
    ex = make_exchange(cfg.exchange)
    all_trades = []
    for sym in args.symbols or cfg.symbols:
        trades = backtest(fetch_history(ex, sym, cfg.timeframe, args.candles), sym, cfg)
        print(f"{sym:12} {stats(trades)}")
        all_trades += trades
    if args.list:
        for t in sorted(all_trades, key=lambda t: t["time"]):
            print(f"{t['time']:%Y-%m-%d %H:%M} {t['symbol']:10} {t['side']:5} {t['entry']:>12.6g} {t['result']:4} {t['R']:+.2f}R")
    print(f"{'ALL':12} {stats(all_trades)}")


if __name__ == "__main__":
    main()
