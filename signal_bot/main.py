"""Run the bot: python -m signal_bot.main"""
import logging
import time

from .config import load_config
from .exchange import fetch_ohlcv, make_exchange
from .strategy import latest_signal
from .telegram import format_signal, send_message

log = logging.getLogger("signal_bot")


def run_once(cfg, exchange, sent: set) -> None:
    for symbol in cfg.symbols:
        try:
            df = fetch_ohlcv(exchange, symbol, cfg.timeframe)
            sig = latest_signal(df, symbol, cfg)
        except Exception:
            log.exception("Failed to check %s", symbol)
            continue
        if sig is None:
            continue
        key = (sig.symbol, sig.side, sig.timestamp)
        if key in sent:  # one message per candle
            continue
        text = format_signal(sig, cfg.timeframe)
        if cfg.dry_run:
            print(text, end="\n\n")
        else:
            send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, text)
        sent.add(key)
        log.info("Signal: %s %s @ %s", sig.side, sig.symbol, sig.entry)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    if not cfg.dry_run and not (cfg.telegram_bot_token and cfg.telegram_chat_id):
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, or DRY_RUN=true")
    exchange = make_exchange(cfg.exchange)
    sent: set = set()
    log.info("Watching %s on %s (%s), dry_run=%s", cfg.symbols, cfg.exchange, cfg.timeframe, cfg.dry_run)
    while True:
        run_once(cfg, exchange, sent)
        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    main()
