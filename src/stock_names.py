import requests

_STOCK_NAMES_CACHE = None

TWSE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_P"
TPEX_URL = "https://openapi.tpex.org.tw/v1/opendata/t187ap03_P"

def _fetch_twse():
    resp = requests.get(TWSE_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        print(f"  TWSE API 回傳非陣列: {type(data)}")
        print(f"  內容: {str(data)[:500]}")
        return {}
    if not data:
        print("  TWSE API 回傳空陣列")
        return {}
    sample = data[0]
    print(f"  TWSE API 第一筆 keys: {list(sample.keys())}")
    return {item["公司代號"]: item["公司簡稱"] for item in data}

def _fetch_tpex():
    try:
        resp = requests.get(TPEX_URL, timeout=15)
        resp.raise_for_status()
        return {item["公司代號"]: item["公司簡稱"] for item in resp.json()}
    except Exception:
        return {}

def fetch_all_names():
    names = {}
    try:
        names.update(_fetch_twse())
        names.update(_fetch_tpex())
    except Exception as e:
        print(f"獲取股票名稱失敗: {e}")
    return names

def get_stock_name(stock_no):
    global _STOCK_NAMES_CACHE
    if _STOCK_NAMES_CACHE is None:
        _STOCK_NAMES_CACHE = fetch_all_names()
    return _STOCK_NAMES_CACHE.get(stock_no, stock_no)
