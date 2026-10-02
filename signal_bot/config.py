import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    exchange: str
    symbols: list[str]
    timeframe: str
    ema_fast: int
    ema_slow: int
    rsi_period: int
    atr_period: int
    stop_atr_mult: float
    take_profit_rr: float
    poll_seconds: int
    dry_run: bool


def load_config() -> Config:
    load_dotenv()
    env = os.getenv
    return Config(
        telegram_bot_token=env("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=env("TELEGRAM_CHAT_ID", ""),
        exchange=env("EXCHANGE", "binance"),
        symbols=[s.strip() for s in env("SYMBOLS", "BTC/USDT").split(",") if s.strip()],
        timeframe=env("TIMEFRAME", "4h"),
        ema_fast=int(env("EMA_FAST", "20")),
        ema_slow=int(env("EMA_SLOW", "50")),
        rsi_period=int(env("RSI_PERIOD", "14")),
        atr_period=int(env("ATR_PERIOD", "14")),
        stop_atr_mult=float(env("STOP_ATR_MULT", "1.5")),
        take_profit_rr=float(env("TAKE_PROFIT_RR", "2.0")),
        poll_seconds=int(env("POLL_SECONDS", "300")),
        dry_run=env("DRY_RUN", "true").lower() == "true",
    )
