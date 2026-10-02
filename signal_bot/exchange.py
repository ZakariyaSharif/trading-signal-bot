import ccxt
import pandas as pd


def make_exchange(name: str):
    return getattr(ccxt, name)({"enableRateLimit": True})


def fetch_ohlcv(exchange, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("ts"), unit="ms", utc=True)
    return df
