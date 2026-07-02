from google import genai
from src.stock_names import ETF_NAMES

FEE_RATE = 0.004418


def generate_ai_summary(
    user_name: str,
    pnl_report: dict,
    total_market_val: float,
    total_unrealized_pnl: float,
    api_key: str,
) -> str | None:
    if not api_key:
        return None

    details = pnl_report.get("details", {})
    total_pnl = pnl_report.get("total_pnl", 0)
    has_data = any(
        d["qty"] > 0 or d["yesterday_qty"] > 0 for d in details.values()
    )
    if not has_data:
        return None

    stock_changes = []
    etf_changes = []
    for sym, d in details.items():
        if d["qty"] <= 0 and d["yesterday_qty"] <= 0:
            continue
        mv = int(d["qty"] * d["today_price"] * (1 - FEE_RATE))
        yesterday_mv = int(d["yesterday_qty"] * d["yesterday_price"] * (1 - FEE_RATE))
        diff = mv - yesterday_mv
        sign = "+" if diff >= 0 else ""
        line = f"{d['stock_name']}({sym})：市值變動 {sign}{diff} 元，持有 {d['qty']} 股，收盤價 {d['today_price']} 元"
        if sym in ETF_NAMES:
            etf_changes.append((abs(diff), line))
        else:
            stock_changes.append((abs(diff), line))

    stock_changes.sort(reverse=True)
    etf_changes.sort(reverse=True)
    top_changes = [line for _, line in (stock_changes[:3] + etf_changes[:3])]

    print("  正在呼叫 Gemini API...", flush=True)
    prompt = f"""你是一個資產摘要助手。根據以下今日庫存數據，用口語的繁體中文產出 1~3 句摘要。只描述數字呈現的事實，不預測未來、不給投資建議。

用戶：{user_name}
今日資產總額（已扣費用）：{total_market_val:,} 元
今日損益（與昨日比）：{total_pnl:+,} 元
累積未實現損益：{total_unrealized_pnl:+,} 元

主要變動標的：
{' '.join(top_changes)}

規則：
- 先說整體損益，再加 1~2 句 highlight 主要變動
- 不要用「可能、或許、建議」等推測性用語
- 最多 3 句"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        print(f"  Gemini 回覆: {text[:80]}...", flush=True)
        return text
    except Exception as e:
        print(f"AI 摘要生成失敗: {e}", flush=True)
        return None
