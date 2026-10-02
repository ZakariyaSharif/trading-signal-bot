# Trading Signal Bot

Watches crypto pairs and posts trading signals to a Telegram channel, then **tracks every
signal until it hits take-profit or stop-loss** and posts the result with a live win rate.

> ⚠️ **Educational only, not financial advice.** No strategy guarantees a win rate.
> Backtest first, paper-trade second, and never risk money you can't afford to lose.

## Strategy

| Filter | LONG | SHORT |
|---|---|---|
| Trigger | fast EMA crosses **above** slow EMA | fast EMA crosses **below** slow EMA |
| Trend | close **above** 200 EMA | close **below** 200 EMA |
| Momentum | RSI 50–70 | RSI 30–50 |
| Trend strength | ADX ≥ `ADX_MIN` | ADX ≥ `ADX_MIN` |
| Stop-loss | entry − `STOP_ATR_MULT` × ATR | entry + `STOP_ATR_MULT` × ATR |
| Take-profit | `TAKE_PROFIT_RR` × stop distance | same |

## About win rate (read this)

Win rate is mostly a setting, not a skill. You can raise it by making the take-profit smaller
than the stop-loss, but each win then pays less:

| Take-profit : Stop | Win rate needed to break even (before fees) |
|---|---|
| 0.5 : 1 | 67% |
| 1 : 1 | 50% |
| 2 : 1 | 33% |

So a **70% win rate at 0.5:1 loses money**, and a 40% win rate at 2:1 makes money. The number
that matters is **expectancy** (average R per trade after fees). The tools here show both.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit it
```

Telegram: create a bot with [@BotFather](https://t.me/BotFather), put the token in
`TELEGRAM_BOT_TOKEN`, add the bot as admin of your channel, and set `TELEGRAM_CHAT_ID=@yourchannel`.

## Workflow

```bash
# 1. Find settings with a 60%+ win rate AND positive expectancy (train/test split)
python -m signal_bot.optimize BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT --candles 6000 --min-win 0.6

# 2. Copy the best settings (judged by TEST, with 100+ trades) into .env, then confirm
python -m signal_bot.backtest --candles 6000

# 3. Paper-trade: DRY_RUN=true prints signals and results instead of sending them
python -m signal_bot.main

# 4. Go live after a few weeks of paper results: DRY_RUN=false

pytest   # tests
```

Live results are stored in `data/state.json`; each closed trade posts a message like
`✅ TAKE-PROFIT HIT ... 📊 Live record: 24 trades | Win rate 63% | Total +4.2R`.

## Layout

```
signal_bot/
  config.py      # loads .env
  indicators.py  # EMA, RSI, ATR, ADX
  strategy.py    # signal rules + SL/TP
  exchange.py    # OHLCV data via ccxt (no API key needed), cached history
  backtest.py    # historical test with fees: win rate, expectancy, profit factor, drawdown
  optimize.py    # parameter search with train/test split and confidence ranges
  tracker.py     # live TP/SL tracking, persisted to JSON
  telegram.py    # message formats + sending
  main.py        # polling loop
tests/
```
