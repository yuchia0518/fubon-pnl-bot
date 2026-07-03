import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from supabase import create_client
from src.crypto_utils import encrypt


def main():
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    mk = os.environ["MASTER_KEY"]
    line_user_id = os.environ["LINE_USER_ID"]

    data = {
        "name": os.environ["NAME"],
        "line_user_id": line_user_id,
        "fubon_username": encrypt(os.environ["FUBON_USERNAME"], mk),
        "fubon_password": encrypt(os.environ["FUBON_PASSWORD"], mk),
        "fubon_ca_content": encrypt(os.environ["FUBON_CA_CONTENT"], mk),
        "fubon_ca_password": encrypt(os.environ["FUBON_CA_PASSWORD"], mk),
        "ct_id": "setup_bot",
    }

    existing = supabase.table("users").select("id").eq("line_user_id", line_user_id).execute()
    if existing.data:
        result = supabase.table("users").update(data).eq("line_user_id", line_user_id).execute()
        print("✅ 已更新使用者:", result.data)
    else:
        result = supabase.table("users").insert(data).execute()
        print("✅ 已寫入新使用者:", result.data)


if __name__ == "__main__":
    main()
