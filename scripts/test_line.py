import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
user_id = os.environ.get("LINE_USER_ID", "").strip()
msg = os.environ.get("MSG", "🧪 測試訊息")

print(f"發送至: {user_id}")
print(f"訊息內容: {msg}")

api = LineBotApi(token)
api.push_message(user_id, TextSendMessage(text=msg))
print("✅ 成功推送！")
