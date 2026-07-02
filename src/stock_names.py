import requests

_STOCK_NAMES_CACHE = None

TWSE_STOCKS_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

ETF_NAMES = {
    "0050": "元大台灣50",
    "0051": "元大中型100",
    "0052": "富邦科技",
    "0053": "元大電子",
    "0055": "元大MSCI金融",
    "0056": "元大高股息",
    "00646": "元大S&P500",
    "00940": "元大台灣價值高息",
    "009800": "中信NASDAQ",
    "009816": "凱基台灣TOP50",
    "00773B": "中信優先金融債",
    "00888": "永豐台灣ESG",
}

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
    etf_name = ETF_NAMES.get(stock_no)
    if etf_name:
        return etf_name
    return stock_no
