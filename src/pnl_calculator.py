def calculate_daily_pnl(yesterday_inv: dict, today_inv: dict, transactions: list) -> dict:
    """
    yesterday_inv: { "2330": {"qty": 1000, "close": 950.0} }
    today_inv:     { "2330": {"qty": 1000, "price": 962.0} }
    transactions:  [ {"symbol": "2317", "side": "sell", "qty": 1000, "price": 200.5, "fee": 142, "tax": 300} ]
    """
    buys = {}
    sells = {}

    for tx in transactions:
        sym = tx["symbol"]
        side = tx["side"]
        if side == "buy":
            buys.setdefault(sym, []).append(tx)
        elif side == "sell":
            sells.setdefault(sym, []).append(tx)

    all_symbols = set(
        list(yesterday_inv.keys())
        + list(today_inv.keys())
        + list(buys.keys())
        + list(sells.keys())
    )

    total_pnl = 0
    details = {}

    for sym in all_symbols:
        y_qty = yesterday_inv.get(sym, {}).get("qty", 0)
        y_close = yesterday_inv.get(sym, {}).get("close", 0.0)

        t_qty = today_inv.get(sym, {}).get("qty", 0)
        t_close = today_inv.get(sym, {}).get("price", 0.0)

        sym_pnl = 0

        # New buys
        buy_records = buys.get(sym, [])
        total_bought_qty = sum(b["qty"] for b in buy_records)
        for b in buy_records:
            sym_pnl += (t_close - b["price"]) * b["qty"] - b["fee"]

        # Sells
        sell_records = sells.get(sym, [])
        total_sold_qty = sum(s["qty"] for s in sell_records)
        for s in sell_records:
            sym_pnl += (s["price"] - y_close) * s["qty"] - s["fee"] - s["tax"]

        # Holdings (yesterday inventory minus what was sold today)
        hold_qty = y_qty - total_sold_qty
        if hold_qty > 0:
            sym_pnl += (t_close - y_close) * hold_qty

        total_pnl += sym_pnl
        details[sym] = {
            "pnl": int(round(sym_pnl)),
            "today_price": t_close,
            "yesterday_price": y_close,
            "qty": t_qty,
        }

    return {"total_pnl": int(round(total_pnl)), "details": details}
