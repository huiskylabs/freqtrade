#!/usr/bin/env python3
"""
Comprehensive backtest runner for exploring:
1. Different tickers (BTC, SOL, HYPE, ZEC, ETH)
2. Different entry strategies (30m/1h, 1h/2h, 2h/4h, 6h/12h)
3. Different risk profiles (Moderate, Aggressive5pct, VeryAggressive, HyperAggressive)

Runs 6-month backtests for each combination and generates comparison reports.
"""
import subprocess
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd


# Calculate 6 months back from today
END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")

BACKTEST_DIR = Path("/workspace/user_data")
CONFIG_DIR = BACKTEST_DIR / "backtest_configs"
RESULTS_DIR = BACKTEST_DIR / "backtest_results"
RESULTS_DIR.mkdir(exist_ok=True)

# Test configurations
TICKER_CONFIGS = {
    "btc_sol": str(CONFIG_DIR / "config_btc_sol.json"),
    "btc_sol_hype_zec": str(CONFIG_DIR / "config_btc_sol_hype_zec.json"),
    "major_alts": str(CONFIG_DIR / "config_major_alts.json"),
}

ENTRY_STRATEGIES = {
    "30m_1h": "TrendPullback30m1hModerate",
    "1h_2h": "TrendPullback1h2hModerate",
    "2h_4h": "TrendPullbackScaleOutModerate",  # baseline
    "6h_12h": "TrendPullback6h12hModerate",
}

RISK_STRATEGIES = {
    "moderate": "TrendPullbackScaleOutModerate",
    "aggressive_5pct": "TrendPullbackScaleOutAggressive5pct",
    "very_aggressive": "TrendPullbackScaleOutVeryAggressive",
    "hyper_aggressive": "TrendPullbackScaleOutHyperAggressive",
}


def run_backtest(strategy_name, config_path, test_name):
    """Run a single backtest"""
    print(f"\n{'='*80}")
    print(f"Running backtest: {test_name}")
    print(f"Strategy: {strategy_name}")
    print(f"Config: {config_path}")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"{'='*80}\n")
    
    cmd = [
        "freqtrade",
        "backtesting",
        "--strategy", strategy_name,
        "--config", config_path,
        "--timerange", f"{START_DATE}-{END_DATE}",
        "--export", "trades",
        "--export-filename", str(RESULTS_DIR / f"{test_name}.json"),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd="/workspace",
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout per backtest
        )
        
        output_file = RESULTS_DIR / f"{test_name}_output.txt"
        with open(output_file, "w") as f:
            f.write(f"Command: {' '.join(cmd)}\n\n")
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\n\nSTDERR:\n")
            f.write(result.stderr)
            f.write(f"\n\nReturn code: {result.returncode}")
        
        if result.returncode == 0:
            print(f"✓ Backtest completed successfully: {test_name}")
            return True
        else:
            print(f"✗ Backtest failed: {test_name}")
            print(f"  See output in: {output_file}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ Backtest timed out: {test_name}")
        return False
    except Exception as e:
        print(f"✗ Backtest error: {test_name} - {e}")
        return False


def parse_backtest_results(test_name):
    """Parse backtest results from output file"""
    output_file = RESULTS_DIR / f"{test_name}_output.txt"
    
    if not output_file.exists():
        return None
    
    with open(output_file, "r") as f:
        output = f.read()
    
    # Extract key metrics using simple text parsing
    metrics = {
        "test_name": test_name,
        "total_profit_pct": None,
        "total_trades": None,
        "wins": None,
        "losses": None,
        "win_rate": None,
        "avg_profit": None,
        "max_drawdown": None,
        "sharpe_ratio": None,
    }
    
    for line in output.split("\n"):
        if "Total Profit %" in line or "Total profit" in line:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if "%" in part:
                        metrics["total_profit_pct"] = float(part.replace("%", "").replace(",", ""))
                        break
            except:
                pass
        elif "Total/Daily Avg Trades" in line or "Total trades" in line:
            try:
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        metrics["total_trades"] = int(part)
                        break
            except:
                pass
        elif "Win " in line and "Loss " in line:
            try:
                if " W " in line and " L " in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "W":
                            metrics["wins"] = int(parts[i-1])
                        elif part == "L":
                            metrics["losses"] = int(parts[i-1])
            except:
                pass
        elif "Win rate" in line or "Winrate" in line:
            try:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        metrics["win_rate"] = float(part.replace("%", ""))
                        break
            except:
                pass
        elif "Max Drawdown" in line or "Max drawdown" in line:
            try:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        metrics["max_drawdown"] = float(part.replace("%", "").replace(",", ""))
                        break
            except:
                pass
    
    return metrics


def main():
    """Run all backtests and generate comparison report"""
    
    print("="*80)
    print("COMPREHENSIVE BACKTEST EXPLORATION")
    print("="*80)
    print(f"Date Range: {START_DATE} to {END_DATE} (6 months)")
    print(f"Results Directory: {RESULTS_DIR}")
    print()
    
    all_results = []
    
    # Test 1: Different Tickers (using baseline 2h/4h moderate strategy)
    print("\n" + "="*80)
    print("TEST AREA 1: DIFFERENT TICKERS")
    print("="*80)
    
    baseline_strategy = "TrendPullbackScaleOutModerate"
    for ticker_name, config_path in TICKER_CONFIGS.items():
        test_name = f"tickers_{ticker_name}"
        success = run_backtest(baseline_strategy, config_path, test_name)
        if success:
            metrics = parse_backtest_results(test_name)
            if metrics:
                metrics["test_area"] = "Tickers"
                metrics["variation"] = ticker_name
                all_results.append(metrics)
    
    # Test 2: Different Entry Strategies (using major_alts config)
    print("\n" + "="*80)
    print("TEST AREA 2: DIFFERENT ENTRY STRATEGIES")
    print("="*80)
    
    baseline_config = TICKER_CONFIGS["major_alts"]
    for strategy_name_short, strategy_class in ENTRY_STRATEGIES.items():
        test_name = f"entry_{strategy_name_short}"
        success = run_backtest(strategy_class, baseline_config, test_name)
        if success:
            metrics = parse_backtest_results(test_name)
            if metrics:
                metrics["test_area"] = "Entry Strategy"
                metrics["variation"] = strategy_name_short
                all_results.append(metrics)
    
    # Test 3: Different Risk Profiles (using major_alts config)
    print("\n" + "="*80)
    print("TEST AREA 3: DIFFERENT RISK PROFILES")
    print("="*80)
    
    for risk_name, strategy_class in RISK_STRATEGIES.items():
        test_name = f"risk_{risk_name}"
        success = run_backtest(strategy_class, baseline_config, test_name)
        if success:
            metrics = parse_backtest_results(test_name)
            if metrics:
                metrics["test_area"] = "Risk Profile"
                metrics["variation"] = risk_name
                all_results.append(metrics)
    
    # Generate comparison report
    print("\n" + "="*80)
    print("GENERATING COMPARISON REPORT")
    print("="*80)
    
    if all_results:
        df = pd.DataFrame(all_results)
        
        # Save to CSV
        csv_file = RESULTS_DIR / "comparison_results.csv"
        df.to_csv(csv_file, index=False)
        print(f"\nResults saved to: {csv_file}")
        
        # Create summary by test area
        summary_file = RESULTS_DIR / "comparison_summary.txt"
        with open(summary_file, "w") as f:
            f.write("="*80 + "\n")
            f.write("COMPREHENSIVE BACKTEST COMPARISON SUMMARY\n")
            f.write("="*80 + "\n")
            f.write(f"Date Range: {START_DATE} to {END_DATE} (6 months)\n")
            f.write(f"Total Tests: {len(all_results)}\n\n")
            
            for test_area in ["Tickers", "Entry Strategy", "Risk Profile"]:
                area_df = df[df["test_area"] == test_area]
                if not area_df.empty:
                    f.write("\n" + "="*80 + "\n")
                    f.write(f"{test_area.upper()}\n")
                    f.write("="*80 + "\n\n")
                    
                    for _, row in area_df.iterrows():
                        f.write(f"{row['variation']}:\n")
                        if pd.notna(row['total_profit_pct']):
                            f.write(f"  Total Profit: {row['total_profit_pct']:.2f}%\n")
                        if pd.notna(row['total_trades']):
                            f.write(f"  Total Trades: {row['total_trades']}\n")
                        if pd.notna(row['win_rate']):
                            f.write(f"  Win Rate: {row['win_rate']:.2f}%\n")
                        if pd.notna(row['max_drawdown']):
                            f.write(f"  Max Drawdown: {row['max_drawdown']:.2f}%\n")
                        f.write("\n")
                    
                    # Find best performer in this area
                    if pd.notna(area_df['total_profit_pct']).any():
                        best = area_df.loc[area_df['total_profit_pct'].idxmax()]
                        f.write(f"BEST PERFORMER: {best['variation']} ")
                        f.write(f"({best['total_profit_pct']:.2f}% profit)\n\n")
        
        print(f"Summary saved to: {summary_file}")
        print("\n" + "="*80)
        print("ALL BACKTESTS COMPLETED")
        print("="*80)
    else:
        print("\n✗ No successful backtests to report")


if __name__ == "__main__":
    main()
