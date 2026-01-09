# Crypto Data Updater

Automated cryptocurrency OHLCV data updater for HuggingFace datasets with GitHub Actions support. Maintains continuously growing historical price data for 22 cryptocurrency trading pairs across multiple timeframes (15m, 1h).

## Features

- Automated data updates from Binance API
- HuggingFace dataset integration
- Duplicate detection and data merging
- Hourly scheduled updates via GitHub Actions
- Colab notebook support for manual data initialization
- Comprehensive error handling and logging

## Supported Cryptocurrencies

22 trading pairs:
- Major: BTCUSDT, ETHUSDT, BNBUSDT
- Layer 1: ADAUSDT, AVAXUSDT, DOGEUSDT, DOTUSDT, SOLUSDT, ATOMUSDT
- Layer 2: ARBUSDT, OPUSDT, MATICUSDT
- DeFi: AAVEUSDT, UNIUSDT, LINKUSDT
- Alt coins: ALGOUSDT, BCHUSDT, ETCUSDT, FILUSDT, LTCUSDT, NEARUSDT, XRPUSDT

## Timeframes

- 15m (15 minutes)
- 1h (1 hour)

## Directory Structure

```
crypto-data-updater/
├── config.py                 # Configuration file with symbols and settings
├── data_handler.py          # Core data handling logic
├── colab_updater.py         # Colab-compatible update script
├── update_runner.py         # GitHub Actions runner script
├── requirements.txt         # Python dependencies
├── .github/workflows/       # GitHub Actions workflows
│   └── hourly-update.yml   # Scheduled hourly update workflow
└── README.md               # This file
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- HuggingFace account with dataset access
- HuggingFace API token

### For Google Colab (Initial Data Update)

1. Open Google Colab: https://colab.research.google.com/

2. Run the following in a cell:
```python
!git clone https://github.com/caizongxun/crypto-data-updater.git
%cd crypto-data-updater

from colab_updater import main, setup_colab_environment
setup_colab_environment()
main()
```

3. When prompted, enter your HuggingFace API token
4. Confirm to proceed with the data update
5. Wait for all updates to complete

### For GitHub Actions (Automated Hourly Updates)

1. Fork or clone this repository to your GitHub account

2. Create HuggingFace API token:
   - Visit: https://huggingface.co/settings/tokens
   - Create new token with write access
   - Copy the token

3. Add token to GitHub Secrets:
   - Go to your repository settings
   - Navigate to: Secrets and variables > Actions
   - Create new secret named: `HF_TOKEN`
   - Paste your HuggingFace token

4. Enable GitHub Actions:
   - Go to Actions tab
   - Enable workflows if not already enabled

5. The workflow will automatically run:
   - Every hour at minute 0 (e.g., 1:00, 2:00, 3:00, etc.)
   - Can be manually triggered from Actions tab

## Data Format

Each parquet file contains the following columns:

- `open_time`: Candlestick open time (UTC)
- `open`: Opening price
- `high`: Highest price in period
- `low`: Lowest price in period
- `close`: Closing price
- `volume`: Trading volume
- `close_time`: Candlestick close time (UTC)
- `quote_asset_volume`: Quote asset volume
- `number_of_trades`: Number of trades
- `taker_buy_base_asset_volume`: Taker buy base asset volume
- `taker_buy_quote_asset_volume`: Taker buy quote asset volume
- `ignore`: Binance API field (ignored)

## Data Growth Rate

With hourly updates:
- 15m timeframe: 4 new candles per hour (96 per day, 2,880 per month)
- 1h timeframe: 1 new candle per hour (24 per day, 720 per month)

## File Structure on HuggingFace

```
v2-crypto-ohlcv-data/
├── klines/
│   ├── AAVEUSDT/
│   │   ├── AAVE_15m.parquet
│   │   └── AAVE_1h.parquet
│   ├── ADAUSDT/
│   │   ├── ADA_15m.parquet
│   │   └── ADA_1h.parquet
│   └── ... (20 more symbols)
```

## Usage

### Manual Update via Colab

Use the Colab script for initial data loading or manual updates when needed.

### Automatic Updates via GitHub Actions

Once configured, the system automatically:
1. Fetches latest klines from Binance API
2. Downloads existing data from HuggingFace
3. Merges and deduplicates data
4. Validates data integrity
5. Uploads updated files back to HuggingFace
6. Commits changes to GitHub

## Monitoring Updates

1. Go to Actions tab in your GitHub repository
2. Click on "Hourly Crypto Data Update" workflow
3. View recent runs and their logs
4. Check HuggingFace dataset for updated files

## Troubleshooting

### HF_TOKEN not set error
- Ensure HF_TOKEN secret is added to GitHub repository
- Verify token has write access to the dataset

### Data merge failures
- Check internet connection
- Verify Binance API is accessible
- Check HuggingFace API status

### Upload errors
- Ensure HF_TOKEN has sufficient permissions
- Verify dataset repository path is correct
- Check available storage space on HuggingFace

## Configuration

Edit `config.py` to:
- Add/remove cryptocurrency symbols
- Change timeframes
- Modify HuggingFace dataset details

## Dependencies

- pandas: Data manipulation and analysis
- pyarrow: Parquet file support
- huggingface-hub: HuggingFace integration
- requests: HTTP requests to Binance API
- numpy: Numerical operations
- python-dotenv: Environment variable handling

## API Limits

- Binance API: 1200 requests per minute (REST)
- HuggingFace: Reasonable rate limits for uploads

## License

MIT License

## Support

For issues or questions:
1. Check GitHub Issues
2. Review logs in GitHub Actions
3. Verify configuration in `config.py`

## Future Enhancements

- Additional timeframes (4h, 8h, 1d)
- Real-time WebSocket data integration
- Data validation and quality checks
- Performance metrics and statistics
- Multi-exchange support
