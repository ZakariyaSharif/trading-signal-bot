import requests

from .backtest import stats
from .strategy import Signal

DISCLAIMER = "⚠️ Educational only, not financial advice. Always manage your risk."


def format_signal(sig: Signal, timeframe: str) -> str:
    emoji = "🟢" if sig.side == "LONG" else "🔴"
    risk_pct = abs(sig.entry - sig.stop_loss) / sig.entry * 100
    reward_pct = abs(sig.take_profit - sig.entry) / sig.entry * 100
    return (
        f"{emoji} <b>{sig.side} {sig.symbol}</b> ({timeframe})\n\n"
        f"Entry: <code>{sig.entry:.6g}</code>\n"
        f"Take-profit: <code>{sig.take_profit:.6g}</code> (+{reward_pct:.2f}%)\n"
        f"Stop-loss: <code>{sig.stop_loss:.6g}</code> (-{risk_pct:.2f}%)\n"
        f"RSI: {sig.rsi:.1f} | ADX: {sig.adx:.1f}\n\n"
        f"{DISCLAIMER}"
    )


def format_result(trade: dict, closed: list[dict]) -> str:
    win = trade["result"] == "WIN"
    st = stats(closed)
    return (
        f"{'✅ TAKE-PROFIT HIT' if win else '❌ STOP-LOSS HIT'}: {trade['side']} {trade['symbol']}\n"
        f"Result: {trade['R']:+.2f}R (after fees)\n\n"
        f"📊 Live record: {st.trades} trades | Win rate {st.win_rate:.0%} | Total {st.total_r:+.1f}R"
    )


def send_message(token: str, chat_id: str, text: str) -> None:
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    resp.raise_for_status()
