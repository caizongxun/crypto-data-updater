SYMBOLS = [
    'AAVEUSDT', 'ADAUSDT', 'ALGOUSDT', 'ARBUSDT', 'ATOMUSDT',
    'AVAXUSDT', 'BCHUSDT', 'BNBUSDT', 'BTCUSDT', 'DOGEUSDT',
    'DOTUSDT', 'ETCUSDT', 'ETHUSDT', 'FILUSDT', 'LINKUSDT',
    'LTCUSDT', 'MATICUSDT', 'NEARUSDT', 'OPUSDT', 'SOLUSDT',
    'UNIUSDT', 'XRPUSDT'
]

TIMEFRAMES = ['15m', '1h']

HF_DATASET_REPO = 'zongowo111/v2-crypto-ohlcv-data'
HF_DATASET_PATH = 'klines'

BINANCE_BASE_URL = 'https://api.binance.com/api/v3'

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