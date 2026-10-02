"""Run the bot: python -m signal_bot.main"""
import logging
import time

from .config import load_config
from .exchange import fetch_ohlcv, make_exchange
from .strategy import latest_signal
from .telegram import format_result, format_signal, send_message
from .tracker import Tracker

log = logging.getLogger("signal_bot")


def publish(cfg, text: str) -> None:
    if cfg.dry_run:
        print(text, end="\n\n")
    else:
        send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, text)


def run_once(cfg, exchange, tracker: Tracker) -> None:
    for symbol in cfg.symbols:
        try:
            df = fetch_ohlcv(exchange, symbol, cfg.timeframe)
            for trade in tracker.update(symbol, df, cfg):
                publish(cfg, format_result(trade, tracker.closed))
                log.info("Closed %s %s: %s", trade["side"], symbol, trade["result"])
            sig = latest_signal(df, symbol, cfg)
            # One open trade per symbol, one message per candle
            if sig is None or tracker.has(sig) or tracker.has_open(symbol):
                continue
            publish(cfg, format_signal(sig, cfg.timeframe))
            tracker.add(sig)
            log.info("Signal: %s %s @ %s", sig.side, symbol, sig.entry)
        except Exception:
            log.exception("Failed to process %s", symbol)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    if not cfg.dry_run and not (cfg.telegram_bot_token and cfg.telegram_chat_id):
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, or DRY_RUN=true")
    exchange = make_exchange(cfg.exchange)
    tracker = Tracker(cfg.state_file)
    log.info("Watching %s on %s (%s), dry_run=%s", cfg.symbols, cfg.exchange, cfg.timeframe, cfg.dry_run)
    while True:
        run_once(cfg, exchange, tracker)
        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    main()
