# Quick Start: Running the Backtest Exploration

## TL;DR - Fast Path

```bash
# 1. Setup (one-time)
cd /workspace
export PATH="/home/ubuntu/.local/bin:$PATH"

# 2. Download data (adjust exchange/pairs as needed)
freqtrade download-data \
    --exchange coinbasepro \
    --pairs BTC/USD ETH/USD SOL/USD \
    --timeframes 30m 1h 4h 6h 12h \
    --timerange 20260315-20260913

# 3. Update configs to match your exchange
# Edit user_data/backtest_configs/*.json
# Change "exchange": {"name": "backpack"} to your exchange

# 4. Run full test suite
python3 run_comprehensive_backtest.py

# 5. Review results
cat user_data/backtest_results/comparison_summary.txt
```

## What Gets Tested

### Area 1: Tickers (3 tests)
- BTC + SOL
- BTC + SOL + HYPE + ZEC
- BTC + ETH + SOL + HYPE + ZEC

### Area 2: Entry Strategies (4 tests)
- 30m/1h (fastest)
- 1h/2h (fast)
- 2h/4h (baseline)
- 6h/12h (slowest)

### Area 3: Risk Profiles (4 tests)
- Moderate: 1% risk, 2% heat
- Aggressive: 2% risk, 5% heat
- Very Aggressive: 3% risk, 9% heat
- Hyper Aggressive: 5% risk, 15% heat

**Total: 11 six-month backtests**

## Expected Runtime

- Data download: 10-30 min
- Backtests: 30-60 min  
- Total: ~1-2 hours

## Troubleshooting

### "No data found" error
→ Download data for all required timeframes
→ Update config exchange name to match downloaded data

### "Strategy not found" error  
→ Strategies are in `user_data/strategies/`
→ Check strategy name spelling matches exactly

### "Markets not loaded" error
→ Exchange may be geo-blocked
→ Try different exchange (coinbasepro, kraken, etc.)

### Results missing metrics
→ Backtest may have had no trades
→ Check if data covers full date range
→ Verify pairs exist on exchange

## What to Look For in Results

1. **Best ticker combo** - Which assets together give best Sharpe?
2. **Optimal timeframe** - Faster = more trades or slower = better win rate?
3. **Risk sweet spot** - Where does return/drawdown ratio peak?

## Next Steps

Once you have results:
1. Identify best configuration from `comparison_summary.txt`
2. Run extended backtest (1-2 years) on that config
3. Walk-forward test with out-of-sample periods
4. Paper trade before live deployment

---

Need more detail? See [BACKTEST_EXPLORATION_README.md](../BACKTEST_EXPLORATION_README.md)
