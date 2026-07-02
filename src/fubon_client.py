import os
import base64
import subprocess
from datetime import date
from src.stock_names import get_stock_name


class FubonClientWrapper:
    def __init__(self, id_no, password, ca_content_b64, ca_password):
        self.id_no = id_no
        self.password = password
        self.ca_content_b64 = ca_content_b64
        self.ca_password = ca_password
        self.sdk = None
        self.account = None

    def _write_ca_file(self, ca_path):
        ca_bytes = base64.b64decode(self.ca_content_b64.encode("utf-8"))
        with open(ca_path, "wb") as f:
            f.write(ca_bytes)

    def _cleanup_ca(self, ca_path):
        if os.path.exists(ca_path):
            try:
                os.remove(ca_path)
            except Exception as e:
                print(f"銷毀憑證暫存檔失敗: {e}")

    def login_and_fetch_portfolio(self) -> tuple:
        ca_dir = os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp"
        ca_path = os.path.join(ca_dir, "fubon_ca.p12")
        print(f"CA 憑證路徑: {ca_path}")

        try:
            self._write_ca_file(ca_path)
            ca_size = os.path.getsize(ca_path)
            print(f"CA 憑證已寫入，大小: {ca_size} bytes, 存在: {os.path.exists(ca_path)}")
            if ca_size < 100:
                print(f"⚠️ CA 憑證檔案過小，可能內容不完整")
                print(f"Base64 原始內容長度: {len(self.ca_content_b64)}")
        except Exception as e:
            print(f"寫入 CA 憑證失敗: {e}")
            return False, *self._mock_data()

        try:
            from fubon_neo.sdk import FubonSDK

            # Verify .p12 with openssl before SDK login
            try:
                verify = subprocess.run(
                    ["openssl", "pkcs12", "-in", ca_path, "-noout",
                     "-passin", f"pass:{self.ca_password}"],
                    capture_output=True, text=True, timeout=15
                )
                if verify.returncode == 0:
                    print("✅ openssl 驗證 .p12 成功")
                else:
                    print(f"⚠️ openssl 驗證 .p12 失敗: {verify.stderr.strip()}")
                    print(f"   可能 Base64 內容不正確或密碼錯誤")
            except FileNotFoundError:
                print("openssl 未安裝，跳過驗證")
            except Exception as ve:
                print(f"openssl 驗證異常: {ve}")

            self.sdk = FubonSDK()
            accounts = self.sdk.login(
                self.id_no, self.password, ca_path, self.ca_password
            )

            if not accounts.is_success or not accounts.data:
                print(f"富邦登入失敗: {accounts.message}")
                return False, *self._mock_data()

            self.account = accounts.data[0]
            print(f"✅ 登入成功: {self.account.name} ({self.account.account})")

            # 1. Get portfolio inventory
            inventory_result = self.sdk.accounting.inventories(self.account)
            portfolio = {}
            if inventory_result.is_success and inventory_result.data:
                for inv in inventory_result.data:
                    stock_no = inv.stock_no
                    name = get_stock_name(stock_no)
                    portfolio[stock_no] = {
                        "qty": inv.today_qty,
                        "lastday_qty": inv.lastday_qty,
                        "buy_filled_qty": inv.buy_filled_qty,
                        "sell_filled_qty": inv.sell_filled_qty,
                        "stock_name": name,
                    }
                    print(f"  {stock_no} → {name}")

            # 2. Get unrealized P&L details for current prices
            pnl_result = self.sdk.accounting.unrealized_gains_and_loses(self.account)
            unrealized_pnl_total = 0.0
            if pnl_result.is_success and pnl_result.data:
                for item in pnl_result.data:
                    stock_no = item.stock_no
                    pnl = item.unrealized_profit - item.unrealized_loss
                    unrealized_pnl_total += pnl
                    if stock_no in portfolio and item.today_qty > 0:
                        # Try known price field names
                        price = None
                        for fld in ['current_price', 'market_price', 'closing_price', 'price']:
                            val = getattr(item, fld, None)
                            if val is not None:
                                try:
                                    price = round(float(val), 2)
                                    print(f"  使用 {fld}={val}")
                                    break
                                except (ValueError, TypeError):
                                    continue
                        if price is None:
                            price = round(item.cost_price + (pnl / item.today_qty), 2)
                        portfolio[stock_no]["price"] = price
                        portfolio[stock_no]["cost_price"] = item.cost_price

            # 3. Try to get today's filled orders
            transactions = []
            try:
                today = date.today().strftime("%Y%m%d")
                deal_result = self.sdk.accounting.deal_list(
                    self.account, today, today
                )
                if deal_result.is_success and deal_result.data:
                    for d in deal_result.data:
                        side = "buy" if d.buy_sell.name == "Buy" else "sell"
                        transactions.append({
                            "symbol": d.stock_no,
                            "side": side,
                            "qty": d.filled_qty,
                            "price": float(d.filled_price),
                            "fee": 0,
                            "tax": 0,
                        })
            except AttributeError:
                print("deal_list not available, skipping today's transactions")

            return True, portfolio, unrealized_pnl_total, transactions

        except ImportError:
            print("採用 Fubon API Mock/測試數據回退模式...")
            return False, *self._mock_data()
        finally:
            self._cleanup_ca(ca_path)

    def _mock_data(self):
        mock_portfolio = {"2330": {"qty": 1000, "price": 962.0}}
        mock_unrealized_pnl = 12000.0
        mock_txs = []
        return mock_portfolio, mock_unrealized_pnl, mock_txs
