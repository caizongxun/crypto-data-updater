import pandas as pd

# 38 種可用的幣種（移除了 DYDXUSDT, YFIIUSDT, FLRUSDT, CROUSDT, ARUSDT）
SYMBOLS = [
    'AAVEUSDT', 'ADAUSDT', 'ALGOUSDT', 'ARBUSDT', 'ATOMUSDT',
    'AVAXUSDT', 'BCHUSDT', 'BNBUSDT', 'BTCUSDT', 'DOGEUSDT',
    'DOTUSDT', 'ETCUSDT', 'ETHUSDT', 'FILUSDT', 'LINKUSDT',
    'LTCUSDT', 'MATICUSDT', 'NEARUSDT', 'OPUSDT', 'SOLUSDT',
    'UNIUSDT', 'XRPUSDT', 'MANAUSDT', 'SANDUSDT', 'MKRUSDT',
    'GRTUSDT', 'GALAUSDT', 'SPELLUSDT', 'ENSUSDT', 'IMXUSDT',
    'BATUSDT', 'COMPUSDT', 'SNXUSDT', 'CRVUSDT', 'BALUSDT',
    'KAVAUSDT', 'ZRXUSDT', 'ENJUSDT'
]

TIMEFRAMES = ['15m', '1h']

# 分組設定 - 每組 10 個幣種 (最後一組 8 個)
GROUP_SIZE = 10

# 產生分組
def get_symbol_groups():
    """
    將 38 個幣種分成 4 組 (最後一組 8 個)
    Group 0: SYMBOLS[0:10]   (AAVEUSDT ~ DOGEUSDT)
    Group 1: SYMBOLS[10:20]  (DOTUSDT ~ SOLUSDT)
    Group 2: SYMBOLS[20:30]  (UNIUSDT ~ IMXUSDT)
    Group 3: SYMBOLS[30:38]  (BATUSDT ~ ENJUSDT)
    """
    groups = []
    for i in range(0, len(SYMBOLS), GROUP_SIZE):
        groups.append(SYMBOLS[i:i+GROUP_SIZE])
    return groups

SYMBOL_GROUPS = get_symbol_groups()
TOTAL_GROUPS = len(SYMBOL_GROUPS)

HF_DATASET_REPO = 'zongowo111/v2-crypto-ohlcv-data'
HF_DATASET_PATH = 'klines'

BINANCE_US_BASE_URL = 'https://api.binance.us/api/v3'

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

START_TIMESTAMP = int(pd.Timestamp('2017-08-01').timestamp() * 1000)

def get_file_name(symbol: str, timeframe: str) -> str:
    """
    Generate filename for symbol and timeframe.
    Example: BTCUSDT + 15m -> BTC_15m.parquet
    """
    symbol_short = symbol.replace('USDT', '')
    return f"{symbol_short}_{timeframe}.parquet"

def get_group_for_hour(hour: int) -> int:
    """
    根據小時取得對應的分組
    hour 0-4 對應 Group 0-4 (然後迴圈)
    """
    return hour % TOTAL_GROUPS

def get_symbols_for_hour(hour: int):
    """
    根據小時取得該時段要更新的幣種
    """
    group_idx = get_group_for_hour(hour)
    return SYMBOL_GROUPS[group_idx]
