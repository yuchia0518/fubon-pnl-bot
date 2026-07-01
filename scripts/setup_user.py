import os
from supabase import create_client
from src.crypto_utils import encrypt


def main():
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    mk = os.environ["MASTER_KEY"]

    data = {
        "name": os.environ["NAME"],
        "line_user_id": os.environ["LINE_USER_ID"],
        "fubon_username": encrypt(os.environ["FUBON_USERNAME"], mk),
        "fubon_password": encrypt(os.environ["FUBON_PASSWORD"], mk),
        "fubon_ca_content": encrypt(os.environ["FUBON_CA_CONTENT"], mk),
        "fubon_ca_password": encrypt(os.environ["FUBON_CA_PASSWORD"], mk),
        "ct_id": "setup_bot",
    }

    result = supabase.table("users").insert(data).execute()
    print("✅ 已成功寫入使用者:", result.data)


if __name__ == "__main__":
    main()
