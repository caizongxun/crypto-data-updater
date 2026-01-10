SYMBOLS = [
    'AAVEUSDT', 'ADAUSDT', 'ALGOUSDT', 'ARBUSDT', 'ATOMUSDT',
    'AVAXUSDT', 'BCHUSDT', 'BNBUSDT', 'BTCUSDT', 'DOGEUSDT',
    'DOTUSDT', 'ETCUSDT', 'ETHUSDT', 'FILUSDT', 'LINKUSDT',
    'LTCUSDT', 'MATICUSDT', 'NEARUSDT', 'OPUSDT', 'SOLUSDT',
    'UNIUSDT', 'XRPUSDT', 'MANAUSDT', 'SANDUSDT', 'MKRUSDT',
    'ARUSDT', 'GRTUSDT', 'CROUSDT', 'GALAUSDT', 'SPELLUSDT',
    'FLRUSDT', 'ENSUSDT', 'IMXUSDT', 'YFIIUSDT', 'BATUSDT',
    'COMPUSDT', 'SNXUSDT', 'CRVUSDT', 'BALUSDT', 'DYDXUSDT',
    'KAVAUSDT', 'ZRXUSDT', 'ENJUSDT'
]

TIMEFRAMES = ['15m', '1h']

HF_DATASET_REPO = 'zongowo111/v2-crypto-ohlcv-data'
HF_DATASET_PATH = 'klines'

BINANCE_US_BASE_URL = 'https://api.binance.us/api/v3'

USE_BINANCE_US = True

KLINE_COLUMNS = [
    'open_time',
    'open',
    'high',
    'low',
    'close',
    'volume',
    'close_time',
    'quote_asset_volume',
    'number_of_trades',
    'taker_buy_base_asset_volume',
    'taker_buy_quote_asset_volume',
    'ignore'
]

TIMEFRAME_MAPPING = {
    '15m': '15m',
    '1h': '1h'
}

OPENTIME_COLUMN = 'open_time'
CLOSETIME_COLUMN = 'close_time'

# 歷史數據起始時間
# BTC 在 2013-01-01 開始，但 Binance US 從 2018 開始
# 使用 2017-08-01 作為開始（Binance 國際版開始時間）
START_TIMESTAMP = int(pd.Timestamp('2017-08-01').timestamp() * 1000)  # milliseconds

def get_file_name(symbol: str, timeframe: str) -> str:
    """
    Generate filename for symbol and timeframe.
    Example: BTCUSDT + 15m -> BTC_15m.parquet
    """
    symbol_short = symbol.replace('USDT', '')
    return f"{symbol_short}_{timeframe}.parquet"

import pandas as pd