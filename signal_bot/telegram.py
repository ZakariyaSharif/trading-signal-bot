import requests

from .strategy import Signal

DISCLAIMER = "⚠️ Educational only, not financial advice. Always manage your risk."


def format_signal(sig: Signal, timeframe: str) -> str:
    emoji = "🟢" if sig.side == "LONG" else "🔴"
    risk_pct = abs(sig.entry - sig.stop_loss) / sig.entry * 100
    return (
        f"{emoji} <b>{sig.side} {sig.symbol}</b> ({timeframe})\n\n"
        f"Entry: <code>{sig.entry:.6g}</code>\n"
        f"Stop-loss: <code>{sig.stop_loss:.6g}</code> ({risk_pct:.2f}%)\n"
        f"Take-profit: <code>{sig.take_profit:.6g}</code>\n"
        f"RSI: {sig.rsi:.1f}\n\n"
        f"{DISCLAIMER}"
    )


def send_message(token: str, chat_id: str, text: str) -> None:
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    resp.raise_for_status()
