#!/bin/bash
# Download historical data for backtesting
set -e

export PATH="/home/ubuntu/.local/bin:$PATH"
cd /workspace

# Calculate date range (6 months back)
END_DATE=$(date +%Y%m%d)
START_DATE=$(date -d "180 days ago" +%Y%m%d)

echo "Downloading data from $START_DATE to $END_DATE"

# List of pairs to download (using Binance as fallback since Backpack data may not be available)
PAIRS="BTC/USDT ETH/USDT SOL/USDT"

# Download for different timeframes
for TIMEFRAME in 30m 1h 2h 4h 6h 12h; do
    echo "Downloading $TIMEFRAME data..."
    freqtrade download-data \
        --exchange binance \
        --pairs $PAIRS \
        --timeframes $TIMEFRAME \
        --timerange ${START_DATE}-${END_DATE} \
        --trading-mode futures \
        --datadir user_data/data/binance || echo "Warning: Some $TIMEFRAME downloads may have failed"
done

echo "Data download complete!"
ls -lh user_data/data/binance/
