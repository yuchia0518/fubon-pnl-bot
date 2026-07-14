import json
import os

_STOCK_NAMES_CACHE = None

_STATIC_FILE = os.path.join(os.path.dirname(__file__), "stock_names_data.json")

ETF_SYMBOLS = {
    "0050", "0051", "0052", "0053", "0055", "0056",
    "00646", "00710B", "00727B", "00741B", "00773B",
    "00888", "00940", "00945B", "00953B", "009800",
    "00981B", "00981D", "009816", "00988B", "00989B", "00990B",
}

def fetch_all_names():
    names = {}
    try:
        with open(_STATIC_FILE, "r", encoding="utf-8") as f:
            names = json.load(f)
    except Exception:
        pass
    print(f"  股票名稱快取載入 {len(names)} 筆")
    return names

def get_stock_name(stock_no):
    global _STOCK_NAMES_CACHE
    if _STOCK_NAMES_CACHE is None:
        _STOCK_NAMES_CACHE = fetch_all_names()
    return _STOCK_NAMES_CACHE.get(stock_no, stock_no)
