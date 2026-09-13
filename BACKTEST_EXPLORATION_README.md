# Comprehensive Backtest Exploration Framework

This framework enables systematic exploration of three key dimensions of the TrendPullback trading strategy:

1. **Different Tickers** - Test performance across BTC, SOL, HYPE, ZEC, ETH, and combinations
2. **Different Entry Strategies** - Test various timeframe combinations (30m/1h, 1h/2h, 2h/4h, 6h/12h)
3. **Different Risk Profiles** - Test from Moderate (1%/2% heat) to Hyper-Aggressive (5%/15% heat)

## 📁 File Structure

### Strategy Files (in `user_data/strategies/`)

#### Risk Profile Variations
- `TrendPullbackScaleOutModerate.py` - **BASELINE**: 1% risk/trade, 2% portfolio heat, 0.8% pullback
- `TrendPullbackScaleOutAggressive5pct.py` - 2% risk/trade, 5% heat, 5% pullback  
- `TrendPullbackScaleOutVeryAggressive.py` - 3% risk/trade, 9% heat, 9% pullback
- `TrendPullbackScaleOutHyperAggressive.py` - 5% risk/trade, 15% heat, 15% pullback

#### Entry Strategy Variations (all use Moderate risk profile)
- `TrendPullback30m1hModerate.py` - 30min entry + 1h bias (fastest)
- `TrendPullback1h2hModerate.py` - 1h entry + 2h bias (fast)
- `TrendPullbackScaleOutModerate.py` - **BASELINE**: 2h entry + 4h bias
- `TrendPullback6h12hModerate.py` - 6h entry + 12h bias (slowest)

### Config Files (in `user_data/backtest_configs/`)

- `config_btc_sol.json` - Core majors: BTC, SOL
- `config_btc_sol_hype_zec.json` - Extended: BTC, SOL, HYPE, ZEC  
- `config_major_alts.json` - Full set: BTC, ETH, SOL, HYPE, ZEC

### Runner Script

`run_comprehensive_backtest.py` - Master script that:
- Downloads/validates data for all required pairs
- Runs backtests for all combinations systematically
- Generates comparison reports and CSV exports
- Identifies best performers in each dimension

## 🎯 Test Matrix

### Test Area 1: Tickers (using baseline 2h/4h Moderate strategy)
- BTC + SOL only
- BTC + SOL + HYPE + ZEC
- BTC + ETH + SOL + HYPE + ZEC (full set)

### Test Area 2: Entry Strategies (using full ticker set, Moderate risk)
- 30m/1h (fastest - more signals, smaller moves)
- 1h/2h (fast)
- **2h/4h** (baseline)
- 6h/12h (slowest - fewer signals, larger moves)

### Test Area 3: Risk Profiles (using full ticker set, 2h/4h entry)
- **Moderate**: 1% risk, 2% heat, 0.8% pullback (baseline)
- Aggressive 5%: 2% risk, 5% heat, 5% pullback
- Very Aggressive: 3% risk, 9% heat, 9% pullback  
- Hyper Aggressive: 5% risk, 15% heat, 15% pullback

## 📊 Expected Outputs

### Per-Test Outputs (in `user_data/backtest_results/`)
- `{test_name}_output.txt` - Full freqtrade backtest output
- `{test_name}.json` - Trade export for detailed analysis

### Comparison Reports
- `comparison_results.csv` - All metrics in tabular format
- `comparison_summary.txt` - Formatted summary with best performers highlighted

### Key Metrics Compared
- Total Profit %
- Total Trades
- Win Rate %
- Max Drawdown %
- Risk-adjusted returns (Sharpe when available)

## 🚀 Usage

### Prerequisites
```bash
# Ensure freqtrade is installed
python3 -m pip install -e .

# Add to PATH
export PATH="/home/ubuntu/.local/bin:$PATH"
```

### Download Historical Data

For 6-month backtests, you need data for all timeframes and pairs. Example using an accessible exchange:

```bash
# Using Coinbase or other accessible exchange
freqtrade download-data \
    --exchange coinbasepro \
    --pairs BTC/USD ETH/USD SOL/USD \
    --timeframes 30m 1h 4h 6h 12h \
    --timerange 20260315-20260913 \
    --datadir user_data/data/coinbasepro
```

**Note**: Update config files to match your data source exchange.

### Run Complete Test Suite

```bash
# Run all tests (takes several hours for 6-month backtests)
python3 run_comprehensive_backtest.py
```

### Run Individual Tests

```bash
# Test specific ticker combination
freqtrade backtesting \
    --strategy TrendPullbackScaleOutModerate \
    --config user_data/backtest_configs/config_btc_sol.json \
    --timerange 20260315-20260913

# Test specific entry strategy  
freqtrade backtesting \
    --strategy TrendPullback1h2hModerate \
    --config user_data/backtest_configs/config_major_alts.json \
    --timerange 20260315-20260913

# Test specific risk profile
freqtrade backtesting \
    --strategy TrendPullbackScaleOutHyperAggressive \
    --config user_data/backtest_configs/config_major_alts.json \
    --timerange 20260315-20260913
```

## 🔍 Analysis Workflow

1. **Run baseline** - 2h/4h Moderate on BTC+SOL to establish baseline
2. **Test tickers** - Add pairs progressively to see correlation impact
3. **Test entries** - Compare timeframe speeds on full ticker set
4. **Test risk** - Ramp up aggression to find risk/reward sweet spot
5. **Compare results** - Review `comparison_summary.txt` for insights

## 📈 Interpreting Results

### Ticker Comparison
- **Fewer tickers**: Less diversification, more concentrated risk
- **More tickers**: Better diversification, but heat cap limits concurrent positions
- **Watch for**: Same-way correlation among BTC/SOL/HYPE limiting entries

### Entry Strategy Comparison  
- **Faster timeframes (30m/1h)**: More signals, tighter stops, more activity
- **Slower timeframes (6h/12h)**: Fewer signals, wider stops, smoother equity
- **Watch for**: Win rate vs avg profit trade-off across speeds

### Risk Profile Comparison
- **Moderate (1%)**: Lower heat, fewer concurrent positions, steadier growth
- **Aggressive (2-3%)**: More heat, more positions, higher volatility  
- **Hyper (5%)**: Maximum heat/risk, explosive growth or drawdown
- **Watch for**: Drawdown expansion vs profit acceleration

## ⚠️ Important Notes

### Data Requirements
- Minimum 6 months of OHLCV data required for each timeframe
- Need both entry timeframe AND bias timeframe (e.g., 2h + 4h)
- Futures/perpetual data preferred for leverage testing

### Exchange Compatibility
- Current configs use Backpack exchange
- Update `exchange.name` in configs to match your data source
- Adjust pair formats (e.g., `BTC/USDC:USDC` for futures, `BTC/USD` for spot)

### Runtime Expectations
- Single 6-month backtest: 1-5 minutes per strategy
- Full test suite (11 tests): 30-60 minutes total
- Data download: 10-30 minutes depending on exchange

### Known Limitations
- Kill-switches disabled in backtest (would need live environment)
- Slippage/fees from config (may differ from live)
- No market impact modeling for large positions

## 🛠️ Customization

### Add More Risk Profiles
Create new strategy files inheriting from `TrendPullbackScaleOutStrategy`:
```python
class TrendPullbackScaleOutCustom(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    risk_pct = 0.015          # 1.5% per trade
    portfolio_heat_cap = 0.03  # 3% total heat
    pullback_band = 0.03       # 3% pullback band
    book_tag = "CUSTOM"
```

### Add More Entry Strategies  
Create new timeframe combinations:
```python
@informative("8h")  # Use 8h for bias
def populate_indicators_8h(self, dataframe, metadata):
    # ... calculate bias on 8h
    
# Then use 4h for entries (self.timeframe = "4h")
```

### Add More Ticker Combinations
Edit config JSON files:
```json
{
  "exchange": {
    "pair_whitelist": [
      "BTC/USDC:USDC",
      "ETH/USDC:USDC",
      "CUSTOM/USDC:USDC"
    ]
  }
}
```

## 📋 Checklist Before Running

- [ ] Historical data downloaded for all required pairs and timeframes
- [ ] Config files updated with correct exchange name
- [ ] Pair formats match exchange (futures vs spot notation)
- [ ] Date range covers at least 6 months (180 days)
- [ ] Sufficient disk space for results (~1GB for full suite)
- [ ] Python environment has all dependencies installed

## 🎓 Learning Outcomes

After running this exploration, you will understand:

1. **Portfolio effects** - How different assets behave together
2. **Timeframe sensitivity** - How speed vs stability trade off
3. **Risk scaling** - How position sizing affects returns and drawdowns
4. **Optimization** - Which levers matter most for your goals

## 📞 Support

For questions about:
- **Strategy logic**: See `TrendPullbackStrategy.py` inline documentation
- **Freqtrade usage**: https://www.freqtrade.io/en/stable/backtesting/
- **Risk management**: See `portfolio_heat.py` and `risk_killswitches.py`

---

**Happy backtesting! 🚀**

*Note: Past performance does not guarantee future results. Backtest thoroughly and paper trade before risking real capital.*
