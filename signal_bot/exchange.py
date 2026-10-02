import os

import ccxt
import pandas as pd


def make_exchange(name: str):
    return getattr(ccxt, name)({"enableRateLimit": True})


def _to_df(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates("ts")
    df.index = pd.to_datetime(df.pop("ts"), unit="ms", utc=True)
    return df.sort_index()


def fetch_ohlcv(exchange, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
    return _to_df(exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit))


def fetch_history(exchange, symbol: str, timeframe: str, candles: int, cache_dir: str = "data") -> pd.DataFrame:
    """Fetch up to `candles` closed candles, paging backwards; cached as CSV for repeat runs."""
    path = os.path.join(cache_dir, f"{exchange.id}_{symbol.replace('/', '-')}_{timeframe}_{candles}.csv")
    if os.path.exists(path):
        return pd.read_csv(path, index_col=0, parse_dates=True)

    step = exchange.parse_timeframe(timeframe) * 1000
    since = exchange.milliseconds() - candles * step
    rows: list = []
    while len(rows) < candles:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not batch:
            break
        rows += batch
        since = batch[-1][0] + step
        if len(batch) < 2:
            break
    df = _to_df(rows).iloc[:-1]  # drop the still-forming candle
    os.makedirs(cache_dir, exist_ok=True)
    df.to_csv(path)
    return df
