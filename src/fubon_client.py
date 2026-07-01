import os
import base64


class FubonClientWrapper:
    def __init__(
        self,
        id_no: str,
        password: str,
        ca_content_b64: str,
        ca_password: str,
    ):
        self.id_no = id_no
        self.password = password
        self.ca_content_b64 = ca_content_b64
        self.ca_password = ca_password

    def login_and_fetch_portfolio(self) -> tuple:
        ca_path = os.path.join(
            os.environ.get("TEMP", "/tmp"), "fubon_ca.pfx"
        )
        try:
            ca_bytes = base64.b64decode(self.ca_content_b64.encode("utf-8"))
            with open(ca_path, "wb") as f:
                f.write(ca_bytes)
        except Exception as e:
            print(f"寫入 CA 憑證失敗: {e}")

        try:
            import fubon_neo
            from fubon_neo.sdk import FubonSDK

            sdk = FubonSDK()
            sdk.login(self.id_no, self.password, ca_path, self.ca_password)

            portfolio = sdk.get_portfolio()
            transactions = sdk.get_today_orders()
            unrealized_pnl = sdk.get_unrealized_pnl()

            return portfolio, unrealized_pnl, transactions

        except ImportError:
            print("採用 Fubon API Mock/測試數據回退模式...")
            mock_portfolio = {"2330": {"qty": 1000, "price": 962.0}}
            mock_unrealized_pnl = 12000.0
            mock_txs = []
            return mock_portfolio, mock_unrealized_pnl, mock_txs
        finally:
            if os.path.exists(ca_path):
                try:
                    os.remove(ca_path)
                    print("憑證暫存檔已安全銷毀。")
                except Exception as e:
                    print(f"銷毀憑證暫存檔失敗: {e}")
