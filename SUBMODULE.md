# Private strategies submodule

Private benchmarking / strategy code lives in `trading-strategies` (private GitHub).

```bash
git clone --recurse-submodules git@github.com:huiskylabs/freqtrade.git
# or after clone:
git submodule update --init --recursive

mkdir -p user_data
ln -sfn ../trading-strategies/user_data/strategies user_data/strategies
ln -sfn ../trading-strategies/user_data/data user_data/data
ln -sfn ../trading-strategies/user_data/ACTIVE_STRATEGY.txt user_data/ACTIVE_STRATEGY.txt
```

Public tree keeps exchange adapters (e.g. Backpack) and core only — no strategy edge, research configs, or candle dumps.
