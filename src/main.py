import os
import sys
import traceback
import datetime
from dotenv import load_dotenv
from src.crypto_utils import decrypt
from src.db_client import DatabaseClient
from src.fubon_client import FubonClientWrapper
from src.pnl_calculator import calculate_daily_pnl
from src.line_client import format_report_message, send_line_report


def main():
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    master_key = os.environ.get("MASTER_KEY")
    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

    if not all([supabase_url, supabase_key, master_key]):
        print("錯誤: 缺少環境變數，請確認 SUPABASE_URL, SUPABASE_KEY 與 MASTER_KEY。")
        return

    db = DatabaseClient(supabase_url, supabase_key)
    users = db.get_active_users()
    print(f"找到 {len(users)} 位活躍親友，開始進行損益結算...")

    today_str = datetime.date.today().isoformat()

    for u in users:
        print(f"👉 正在處理: {u['name']}")
        try:
            fubon_user = decrypt(u["fubon_username"], master_key)
            fubon_pass = decrypt(u["fubon_password"], master_key)
            fubon_ca = decrypt(u["fubon_ca_content"], master_key)
            fubon_ca_pass = decrypt(u["fubon_ca_password"], master_key)

            fubon_api = FubonClientWrapper(
                fubon_user, fubon_pass, fubon_ca, fubon_ca_pass
            )
            today_inv, total_unrealized_pnl, today_txs = (
                fubon_api.login_and_fetch_portfolio()
            )

            today_inv = today_inv or {}
            today_txs = today_txs or []

            y_bal = db.get_yesterday_balance(u["id"])
            yesterday_inv = {}
            if y_bal and "holdings_json" in y_bal:
                yesterday_inv = y_bal["holdings_json"] or {}
            yesterday_inv = yesterday_inv or {}

            pnl_report = calculate_daily_pnl(
                yesterday_inv, today_inv, today_txs
            )

            total_market_val = sum(
                item["qty"] * item["price"] for item in today_inv.values()
            )

            print(f"     今日市值: {total_market_val}, 未實現損益: {total_unrealized_pnl}")
            print(f"     每日損益: {pnl_report}")

            msg = format_report_message(
                u["name"], pnl_report, total_market_val, total_unrealized_pnl
            )
            print(f"     正在推送 LINE 給: {u['line_user_id']}")
            send_line_report(u["line_user_id"], msg, line_token)

            db.insert_daily_balance(
                u["id"], today_str, total_market_val, total_unrealized_pnl
            )
            print(f"     ✅ {u['name']} 處理完成")

        except Exception as e:
            traceback.print_exc()
            print(f"處理親友 {u['name']} 時發生錯誤: {e}")


if __name__ == "__main__":
    main()
