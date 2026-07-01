import os
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
old = os.environ["OLD_ID"]
new = os.environ["NEW_ID"]

result = (
    supabase.table("users")
    .update({"line_user_id": new, "md_id": "admin"})
    .eq("line_user_id", old)
    .execute()
)
print(f"✅ 已更新: {result.data}")
