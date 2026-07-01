from supabase import create_client, Client


class DatabaseClient:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)

    def get_active_users(self):
        response = (
            self.client.table("users")
            .select("*")
            .is_("dt_date", "null")
            .execute()
        )
        return response.data

    def get_yesterday_balance(self, user_id: str) -> dict:
        response = (
            self.client.table("daily_balances")
            .select("*")
            .eq("user_id", user_id)
            .is_("dt_date", "null")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return {}

    def insert_daily_balance(
        self, user_id: str, date_str: str, market_val: float, unrealized_pnl: float
    ):
        data = {
            "user_id": user_id,
            "date": date_str,
            "total_market_value": market_val,
            "unrealized_pnl": unrealized_pnl,
            "ct_id": "system_bot",
        }
        self.client.table("daily_balances").insert(data).execute()
