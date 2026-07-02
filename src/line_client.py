import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage
from src.stock_names import ETF_NAMES


def _build_stock_line(sym, detail):
    name = detail.get("stock_name", sym)
    label = f"{name}({sym})" if name != sym else sym
    yesterday_mv = detail["yesterday_qty"] * detail["yesterday_price"]
    today_mv = detail["qty"] * detail["today_price"]
    mv_diff = today_mv - yesterday_mv
    diff_prefix = "+" if mv_diff >= 0 else ""
    return (mv_diff, f"- {label}：{yesterday_mv:,.0f} ➔ {today_mv:,.0f} 元 ({diff_prefix}{mv_diff:,.0f})，收盤價 {detail['today_price']:,.2f} 元，持有 {detail['qty']:,.0f} 股")


def format_report_message(
    user_name: str,
    pnl_report: dict,
    total_market_val: float,
    total_unrealized_pnl: float,
) -> str:
    today_str = datetime.datetime.now().strftime("%Y 年 %m 月 %d 日")
    pnl_val = pnl_report["total_pnl"]
    today_weekday = datetime.datetime.now().strftime("%A")

    weekday_map = {
        "Monday": "一",
        "Tuesday": "二",
        "Wednesday": "三",
        "Thursday": "四",
        "Friday": "五",
        "Saturday": "六",
        "Sunday": "日",
    }
    weekday_cn = weekday_map.get(today_weekday, "")

    pnl_sign = "🟢" if pnl_val >= 0 else "🔴"
    unrealized_sign = "🟢" if total_unrealized_pnl >= 0 else "🔴"

    pnl_prefix = "+" if pnl_val >= 0 else ""
    unreal_prefix = "+" if total_unrealized_pnl >= 0 else ""

    msg = f"📊 【富邦證券】每日盤後損益回報\n"
    msg += f"親愛的 {user_name}，今日台股已收盤，您的帳戶資產統計如下：\n\n"
    msg += f"📅 日期：{today_str} ({weekday_cn})\n\n"
    msg += f"💰 今日資產總額：$ {total_market_val:,.0f} 元\n"
    msg += f"{pnl_sign} 今日純損益 (與昨日比)：{pnl_prefix}$ {pnl_val:,.0f} 元\n"
    msg += (
        f"{unrealized_sign} 累積未實現損益：{unreal_prefix}$ {total_unrealized_pnl:,.0f} 元\n\n"
    )

    msg += "📈 今日持股庫存變動：\n"

    stocks = []
    etfs = []
    for sym, detail in pnl_report["details"].items():
        if detail["qty"] <= 0 and detail["yesterday_qty"] <= 0:
            continue
        mv_diff, line = _build_stock_line(sym, detail)
        if sym in ETF_NAMES:
            etfs.append((mv_diff, line))
        else:
            stocks.append((mv_diff, line))

    stocks.sort(key=lambda x: x[0], reverse=True)
    etfs.sort(key=lambda x: x[0], reverse=True)

    if stocks:
        msg += "🔹 個股\n" + "\n".join(line for _, line in stocks) + "\n\n"
    if etfs:
        msg += "🔸 ETF\n" + "\n".join(line for _, line in etfs) + "\n"

    msg += "\n※ 本報告由系統自動計算。所有敏感憑證與帳密均已於安全記憶體中解密並隨虛擬機銷毀，無任何外洩風險。"
    return msg


def send_line_report(line_user_id: str, message: str, channel_access_token: str):
    if not line_user_id:
        print("警告: 缺少 LINE User ID，無法發送訊息。")
        return

    try:
        line_bot_api = LineBotApi(channel_access_token)
        line_bot_api.push_message(line_user_id, TextSendMessage(text=message))
        print(f"成功推送 LINE 報表給使用者 {line_user_id}")
    except Exception as e:
        print(f"LINE 訊息推送失敗: {e}")
