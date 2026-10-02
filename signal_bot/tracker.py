"""Tracks every signal posted live until it hits take-profit or stop-loss.

State is saved to a JSON file so results survive restarts. This produces a real,
verifiable win rate for the channel (not a backtest).
"""
import json
import os

import pandas as pd

from .backtest import outcome, trade_r
from .strategy import Signal


class Tracker:
    def __init__(self, path: str):
        self.path = path
        self.open: list[dict] = []
        self.closed: list[dict] = []
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self.open, self.closed = data.get("open", []), data.get("closed", [])

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"open": self.open, "closed": self.closed}, f, indent=2)
        os.replace(tmp, self.path)

    def has(self, sig: Signal) -> bool:
        ts = sig.timestamp.isoformat()
        return any(t["symbol"] == sig.symbol and t["time"] == ts for t in self.open + self.closed)

    def has_open(self, symbol: str) -> bool:
        return any(t["symbol"] == symbol for t in self.open)

    def add(self, sig: Signal) -> None:
        self.open.append({"symbol": sig.symbol, "side": sig.side, "entry": sig.entry,
                          "stop_loss": sig.stop_loss, "take_profit": sig.take_profit,
                          "time": sig.timestamp.isoformat()})
        self.save()

    def update(self, symbol: str, df: pd.DataFrame, cfg) -> list[dict]:
        """Check closed candles after each open signal's candle. Returns newly closed trades."""
        done = []
        for t in [t for t in self.open if t["symbol"] == symbol]:
            after = df[df.index > pd.Timestamp(t["time"])].iloc[:-1]  # closed candles only
            for ts, row in after.iterrows():
                res = outcome(t["side"], t["stop_loss"], t["take_profit"], row["high"], row["low"])
                if res:
                    t.update(result=res, closed=ts.isoformat(),
                             R=trade_r(res, t["entry"], t["stop_loss"], cfg))
                    done.append(t)
                    break
        if done:
            self.open = [t for t in self.open if t not in done]
            self.closed += done
            self.save()
        return done
