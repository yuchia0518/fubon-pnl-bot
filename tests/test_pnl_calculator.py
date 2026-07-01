from src.pnl_calculator import calculate_daily_pnl


def test_calculate_daily_pnl():
    yesterday_inventory = {
        "2330": {"qty": 1000, "close": 950.0},
        "2317": {"qty": 2000, "close": 200.0},
    }

    today_inventory = {
        "2330": {"qty": 1000, "price": 962.0},
        "2317": {"qty": 1000, "price": 201.0},
    }

    today_transactions = [
        {"symbol": "2317", "side": "sell", "qty": 1000, "price": 200.5, "fee": 142, "tax": 300},
        {"symbol": "2303", "side": "buy", "qty": 1000, "price": 50.0, "fee": 71, "tax": 0},
    ]

    today_inventory["2303"] = {"qty": 1000, "price": 51.0}

    pnl_report = calculate_daily_pnl(yesterday_inventory, today_inventory, today_transactions)

    assert pnl_report["total_pnl"] == 13987
    assert pnl_report["details"]["2330"]["pnl"] == 12000
    assert pnl_report["details"]["2317"]["pnl"] == 1058
    assert pnl_report["details"]["2303"]["pnl"] == 929
