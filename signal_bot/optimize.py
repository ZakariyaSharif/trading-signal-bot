"""Search strategy settings for a high win rate WITHOUT fooling yourself.

    python -m signal_bot.optimize BTC/USDT ETH/USDT SOL/USDT --candles 5000 --min-win 0.6

How it avoids overfitting:
  * Data is split in time: settings are chosen on the first 70% (TRAIN)
    and then checked on the last 30% (TEST) the optimizer never saw.
  * Only settings with positive expectancy after fees on TRAIN are kept.
  * Ranking is by expectancy, not win rate. A 70% win rate that loses money is useless.
Trust the TEST column. If TEST is much worse than TRAIN, the settings are curve-fitted.

Sample size matters: on pure random prices this optimizer can still "find" 65-70% win
rates over ~20 trades by luck. The 95% range printed for TEST shows how uncertain the
win rate is. Don't trust any setting until TEST has 100+ trades and the range is narrow.
"""
import argparse
import itertools
import math

from .backtest import backtest, stats
from .config import load_config
from .exchange import fetch_history, make_exchange

GRID = {
    "take_profit_rr": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
    "stop_atr_mult": [1.0, 1.5, 2.0, 2.5, 3.0],
    "adx_min": [0, 20, 25],
    "ema_pair": [(9, 21), (20, 50)],
    "ema_trend": [0, 200],
}


def win_rate_range(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson confidence interval for the true win rate."""
    if n == 0:
        return 0.0, 1.0
    p = wins / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def run(datasets: dict, cfg) -> list[dict]:
    trades = []
    for sym, df in datasets.items():
        trades += backtest(df, sym, cfg)
    return trades


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbols", nargs="*")
    p.add_argument("--candles", type=int, default=5000)
    p.add_argument("--min-win", type=float, default=0.6, help="minimum TRAIN win rate")
    p.add_argument("--min-trades", type=int, default=30, help="minimum TRAIN trades")
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args()

    base = load_config()
    ex = make_exchange(base.exchange)
    symbols = args.symbols or list(base.symbols)
    full = {s: fetch_history(ex, s, base.timeframe, args.candles) for s in symbols}
    # Indicators need warm-up, so TEST starts earlier and only trades after the split are counted
    split = {s: df.index[int(len(df) * 0.7)] for s, df in full.items()}
    train = {s: df[df.index < split[s]] for s, df in full.items()}

    keys = list(GRID)
    results = []
    for values in itertools.product(*GRID.values()):
        params = dict(zip(keys, values))
        fast, slow = params.pop("ema_pair")
        cfg = base.with_(ema_fast=fast, ema_slow=slow, **params)
        st = stats(run(train, cfg))
        if st.trades < args.min_trades or st.win_rate < args.min_win or st.expectancy <= 0:
            continue
        test_trades = [t for t in run(full, cfg) if t["time"] >= split[t["symbol"]]]
        results.append((st, stats(test_trades), cfg))

    if not results:
        print(f"No settings reached {args.min_win:.0%} win rate with positive expectancy on TRAIN.")
        print("Try lowering --min-win, adding symbols, or more --candles.")
        return

    results.sort(key=lambda r: r[0].expectancy, reverse=True)
    print(f"{len(results)} settings passed on TRAIN. Top {args.top} (judge them by TEST):\n")
    for tr, te, c in results[: args.top]:
        print(f"RR={c.take_profit_rr} STOP_ATR={c.stop_atr_mult} ADX_MIN={c.adx_min:g} "
              f"EMA={c.ema_fast}/{c.ema_slow} TREND={c.ema_trend}")
        print(f"  TRAIN {tr}")
        lo, hi = win_rate_range(round(te.win_rate * te.trades), te.trades)
        warn = "  <- too few trades, likely luck" if te.trades < 100 else ""
        print(f"  TEST  {te}")
        print(f"        true win rate is probably between {lo:.0%} and {hi:.0%}{warn}\n")


if __name__ == "__main__":
    main()
