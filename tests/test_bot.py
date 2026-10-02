import numpy as np
import pandas as pd

from signal_bot.backtest import backtest, outcome, stats, trade_r
from signal_bot.config import Config
from signal_bot.indicators import adx, atr, rsi
from signal_bot.strategy import add_indicators, signal_at
from signal_bot.telegram import DISCLAIMER, format_result, format_signal
from signal_bot.tracker import Tracker

CFG = Config(ema_fast=3, ema_slow=6, ema_trend=0, rsi_period=5, atr_period=5, adx_min=0,
             stop_atr_mult=1.5, take_profit_rr=2.0, fee_pct=0.0)
CROSS = list(np.linspace(120, 100, 20)) + list(np.linspace(100, 106, 8))


def make_df(closes):
    closes = np.asarray(closes, dtype=float)
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="4h", tz="UTC")
    return pd.DataFrame(
        {"open": closes, "high": closes + 1, "low": closes - 1, "close": closes, "volume": 1.0}, index=idx
    )


def first_signal(df, cfg=CFG):
    df = add_indicators(df, cfg)
    return next((s for i in range(len(df)) if (s := signal_at(df, i, "BTC/USDT", cfg))), None)


def test_rsi_bounds_and_extremes():
    assert rsi(pd.Series(np.arange(1, 50, dtype=float)), 14).dropna().eq(100).all()
    assert rsi(pd.Series(np.arange(50, 1, -1, dtype=float)), 14).dropna().lt(1).all()


def test_atr_constant_range():
    assert atr(make_df([100.0] * 30), 5).iloc[-1] == 2.0


def test_adx_high_in_trend():
    assert adx(make_df(np.linspace(100, 200, 100)), 14).iloc[-1] > 50


def test_long_signal_on_bullish_cross():
    s = first_signal(make_df(CROSS))
    assert s and s.side == "LONG"
    assert s.stop_loss < s.entry < s.take_profit
    assert abs((s.take_profit - s.entry) - 2 * (s.entry - s.stop_loss)) < 1e-9


def test_trend_filter_blocks_counter_trend_long():
    # Long-term downtrend: the small bounce crosses the fast EMAs but stays under the trend EMA
    closes = list(np.linspace(300, 100, 230)) + list(np.linspace(100, 106, 8))
    assert first_signal(make_df(closes), CFG.with_(ema_trend=200)) is None


def test_outcome_and_fees():
    assert outcome("LONG", 95, 110, high=111, low=99) == "WIN"
    assert outcome("LONG", 95, 110, high=111, low=94) == "LOSS"  # both hit -> conservative loss
    assert outcome("SHORT", 105, 90, high=104, low=91) is None
    assert trade_r("WIN", 100, 95, CFG.with_(take_profit_rr=1.0, fee_pct=0.5)) == 0.9


def test_backtest_and_stats():
    rng = np.random.default_rng(0)
    trades = backtest(make_df(100 + np.cumsum(rng.normal(0, 1, 2000))), "BTC/USDT", CFG)
    assert trades and all(t["result"] in {"WIN", "LOSS"} for t in trades)
    st = stats(trades)
    assert 0 <= st.win_rate <= 1 and st.max_dd >= 0


def test_messages():
    s = first_signal(make_df(CROSS))
    assert DISCLAIMER in format_signal(s, "4h")
    t = {"side": "LONG", "symbol": "BTC/USDT", "result": "WIN", "R": 1.9, "time": "2026-01-01"}
    assert "Win rate 100%" in format_result(t, [t])


def test_tracker_resolves_and_persists(tmp_path):
    df = make_df(CROSS)
    s = first_signal(df)
    path = str(tmp_path / "state.json")
    tr = Tracker(path)
    tr.add(s)
    assert tr.has(s) and tr.has_open("BTC/USDT")
    # Price rallies hard after the signal -> take-profit
    later = pd.concat([df[df.index <= s.timestamp], make_df([s.take_profit + 5] * 3).set_index(
        pd.date_range(s.timestamp + pd.Timedelta("4h"), periods=3, freq="4h"))])
    done = tr.update("BTC/USDT", later, CFG)
    assert [d["result"] for d in done] == ["WIN"]
    reloaded = Tracker(path)
    assert not reloaded.open and len(reloaded.closed) == 1


def test_win_rate_range():
    from signal_bot.optimize import win_rate_range
    lo, hi = win_rate_range(12, 18)  # 67% on 18 trades is very uncertain
    assert lo < 0.5 < hi
    lo, hi = win_rate_range(650, 1000)
    assert 0.6 < lo < 0.65 < hi < 0.7
