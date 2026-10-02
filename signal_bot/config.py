import os
from dataclasses import dataclass, replace

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    exchange: str = "binance"
    symbols: tuple[str, ...] = ("BTC/USDT",)
    timeframe: str = "4h"
    ema_fast: int = 20
    ema_slow: int = 50
    ema_trend: int = 200  # 0 disables the trend filter
    rsi_period: int = 14
    atr_period: int = 14
    adx_period: int = 14
    adx_min: float = 20.0  # 0 disables the ADX filter
    stop_atr_mult: float = 2.0
    take_profit_rr: float = 1.0
    fee_pct: float = 0.1  # round-trip fee + slippage, % of entry
    poll_seconds: int = 300
    dry_run: bool = True
    state_file: str = "data/state.json"

    def with_(self, **kw) -> "Config":
        return replace(self, **kw)


def load_config() -> Config:
    load_dotenv()
    env = os.getenv
    d = Config()
    return Config(
        telegram_bot_token=env("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=env("TELEGRAM_CHAT_ID", ""),
        exchange=env("EXCHANGE", d.exchange),
        symbols=tuple(s.strip() for s in env("SYMBOLS", "BTC/USDT").split(",") if s.strip()),
        timeframe=env("TIMEFRAME", d.timeframe),
        ema_fast=int(env("EMA_FAST", d.ema_fast)),
        ema_slow=int(env("EMA_SLOW", d.ema_slow)),
        ema_trend=int(env("EMA_TREND", d.ema_trend)),
        rsi_period=int(env("RSI_PERIOD", d.rsi_period)),
        atr_period=int(env("ATR_PERIOD", d.atr_period)),
        adx_period=int(env("ADX_PERIOD", d.adx_period)),
        adx_min=float(env("ADX_MIN", d.adx_min)),
        stop_atr_mult=float(env("STOP_ATR_MULT", d.stop_atr_mult)),
        take_profit_rr=float(env("TAKE_PROFIT_RR", d.take_profit_rr)),
        fee_pct=float(env("FEE_PCT", d.fee_pct)),
        poll_seconds=int(env("POLL_SECONDS", d.poll_seconds)),
        dry_run=env("DRY_RUN", "true").lower() == "true",
        state_file=env("STATE_FILE", d.state_file),
    )
