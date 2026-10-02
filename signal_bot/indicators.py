"""Technical indicators on a pandas OHLCV DataFrame (columns: open, high, low, close, volume)."""
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI (0-100)."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss
    out = 100 - 100 / (1 + rs)
    # No losses in the window -> RSI 100
    return out.where(loss != 0, 100.0).where(gain.notna())


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range: typical candle size, used to size stop-losses."""
    prev_close = df["close"].shift()
    true_range = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index: trend strength (0-100). Above ~20-25 = trending market."""
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    atr_ = atr(df, period)
    smooth = lambda s: s.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * smooth(plus_dm) / atr_
    minus_di = 100 * smooth(minus_dm) / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return smooth(dx)
