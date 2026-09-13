# Example Expected Results Format

This shows what the comparison output would look like after running the full backtest suite.

## Sample Comparison Summary

```
================================================================================
COMPREHENSIVE BACKTEST COMPARISON SUMMARY
================================================================================
Date Range: 20260315 to 20260913 (6 months)
Total Tests: 11

================================================================================
TICKERS
================================================================================

btc_sol:
  Total Profit: 12.45%
  Total Trades: 23
  Win Rate: 52.17%
  Max Drawdown: -8.32%

btc_sol_hype_zec:
  Total Profit: 18.73%
  Total Trades: 42
  Win Rate: 54.76%
  Max Drawdown: -11.25%

major_alts:
  Total Profit: 21.89%
  Total Trades: 51
  Win Rate: 56.86%
  Max Drawdown: -12.47%

BEST PERFORMER: major_alts (21.89% profit)

================================================================================
ENTRY STRATEGY
================================================================================

30m_1h:
  Total Profit: 15.23%
  Total Trades: 87
  Win Rate: 48.28%
  Max Drawdown: -15.67%

1h_2h:
  Total Profit: 19.45%
  Total Trades: 63
  Win Rate: 52.38%
  Max Drawdown: -12.89%

2h_4h:
  Total Profit: 21.89%
  Total Trades: 51
  Win Rate: 56.86%
  Max Drawdown: -12.47%

6h_12h:
  Total Profit: 18.34%
  Total Trades: 28
  Win Rate: 60.71%
  Max Drawdown: -9.23%

BEST PERFORMER: 2h_4h (21.89% profit)

================================================================================
RISK PROFILE
================================================================================

moderate:
  Total Profit: 21.89%
  Total Trades: 51
  Win Rate: 56.86%
  Max Drawdown: -12.47%

aggressive_5pct:
  Total Profit: 34.56%
  Total Trades: 49
  Win Rate: 55.10%
  Max Drawdown: -18.93%

very_aggressive:
  Total Profit: 48.23%
  Total Trades: 47
  Win Rate: 53.19%
  Max Drawdown: -26.45%

hyper_aggressive:
  Total Profit: 67.89%
  Total Trades: 43
  Win Rate: 51.16%
  Max Drawdown: -38.76%

BEST PERFORMER: hyper_aggressive (67.89% profit)
```

## Key Insights from Example

### Ticker Findings
- **More assets = better diversification**: Adding more pairs increased profit from 12.45% → 21.89%
- **Trade count scaled**: More pairs = more opportunities (23 → 51 trades)
- **Drawdown increased modestly**: 8.32% → 12.47% (acceptable for profit gain)

### Entry Strategy Findings  
- **2h/4h baseline was optimal**: Balance of signal count and quality
- **Faster timeframes (30m/1h)** had more trades but lower win rate and worse drawdown
- **Slower timeframes (6h/12h)** had best win rate but fewer opportunities

### Risk Profile Findings
- **Higher risk = higher reward (and drawdown)**: Linear scaling observed
- **Hyper-aggressive** crushed in % returns (67.89%) but had severe drawdown (-38.76%)
- **Risk-adjusted best** might be Aggressive 5pct (34.56% profit, -18.93% DD)

## Decision Framework

Based on these results, optimal config would be:

**Conservative trader → Moderate risk, 2h/4h, major_alts**
- Profit: 21.89%, Drawdown: -12.47%
- Steady, proven, manageable

**Aggressive trader → Aggressive 5pct, 2h/4h, major_alts**  
- Profit: 34.56%, Drawdown: -18.93%
- Good risk/reward balance

**Maximum risk → Hyper Aggressive, 1h/2h, major_alts**
- Profit: 67.89%+, Drawdown: -38.76%+
- Only for high risk tolerance and adequate capital

## CSV Export Sample

The `comparison_results.csv` file provides all data for custom analysis:

```csv
test_name,test_area,variation,total_profit_pct,total_trades,win_rate,max_drawdown
tickers_btc_sol,Tickers,btc_sol,12.45,23,52.17,-8.32
tickers_btc_sol_hype_zec,Tickers,btc_sol_hype_zec,18.73,42,54.76,-11.25
tickers_major_alts,Tickers,major_alts,21.89,51,56.86,-12.47
entry_30m_1h,Entry Strategy,30m_1h,15.23,87,48.28,-15.67
entry_1h_2h,Entry Strategy,1h_2h,19.45,63,52.38,-12.89
entry_2h_4h,Entry Strategy,2h_4h,21.89,51,56.86,-12.47
entry_6h_12h,Entry Strategy,6h_12h,18.34,28,60.71,-9.23
risk_moderate,Risk Profile,moderate,21.89,51,56.86,-12.47
risk_aggressive_5pct,Risk Profile,aggressive_5pct,34.56,49,55.10,-18.93
risk_very_aggressive,Risk Profile,very_aggressive,48.23,47,53.19,-26.45
risk_hyper_aggressive,Risk Profile,hyper_aggressive,67.89,43,51.16,-38.76
```

Import into Excel/Python for further analysis, charting, etc.

---

**Note**: These are illustrative examples showing the expected output format and the types of insights you can derive. Actual results will vary based on market conditions during your backtest period.
