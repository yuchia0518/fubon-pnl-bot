import requests

_STOCK_NAMES_CACHE = None

TWSE_STOCKS_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

def _fetch_json(url, label):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or not data:
            return {}
        return data
    except Exception:
        return {}

def _fetch_yahoo_name(stock_no):
    """Fallback: query Yahoo Finance for a single stock name."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock_no}.TW"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        return meta.get("shortName") or meta.get("longName") or None
    except Exception as e:
        print(f"  Yahoo Finance 查詢 {stock_no} 失敗: {e}")
        return None

def fetch_all_names():
    names = {}

    stocks = _fetch_json(TWSE_STOCKS_URL, "上市股票")
    for item in stocks:
        code = item.get("公司代號")
        name = item.get("公司簡稱")
        if code and name:
            names[code] = name

    print(f"  股票名稱快取載入 {len(names)} 筆")
    return names

def get_stock_name(stock_no):
    global _STOCK_NAMES_CACHE
    if _STOCK_NAMES_CACHE is None:
        _STOCK_NAMES_CACHE = fetch_all_names()
    name = _STOCK_NAMES_CACHE.get(stock_no)
    if name:
        return name
    yahoo_name = _fetch_yahoo_name(stock_no)
    if yahoo_name:
        _STOCK_NAMES_CACHE[stock_no] = yahoo_name
        return yahoo_name
    return stock_no

def get_stock_name(stock_no):
    global _STOCK_NAMES_CACHE
    if _STOCK_NAMES_CACHE is None:
        _STOCK_NAMES_CACHE = fetch_all_names()
    return _STOCK_NAMES_CACHE.get(stock_no, stock_no)
