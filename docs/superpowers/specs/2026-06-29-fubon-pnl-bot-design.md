# 台灣富邦證券每日盤後損益回報系統設計規格書

> **文件狀態**：已批准 (Approved)
> **日期**：2026-06-29
> **專案**：Fubon Daily P&L Bot (亲友共用版)

---

## 1. 系統概述 (Overview)
本系統是一個專為富邦證券設計的「每日盤後損益回報 Bot」。系統每日定時自動透過富邦 Neo API 登入，下載多位親友的持股與當日交易紀錄，以「交易修正損益計算法」計算精準的每日損益與累積未實現損益，並透過 LINE 官方帳號個別推播至親友的手機。

## 2. 技術棧 (Tech Stack)
*   **程式語言**：Python 3.10+
*   **券商 API**：富邦 Neo API (`fubon-neo`)
*   **資料庫**：Supabase (PostgreSQL - 免費雲端版，透過 `supabase-py` 連線)
*   **執行環境**：GitHub Actions (排程執行虛擬環境，完全免費)
*   **通訊管道**：LINE Messaging API (LINE 官方帳號 Bot，輕用量免費方案，透過 `line-bot-sdk-python`)
*   **加密套件**：`cryptography` (用於 AES-256-CBC 憑證與密碼加密)

## 3. 安全與隱私保護 (Security & Credentials Management)
由於下單憑證與密碼極為敏感，系統採用**記憶體瞬時解密機制**：
1.  **儲存端**：使用對稱密鑰 (AES-256-CBC) 將使用者的身份證字號、密碼、CA 憑證檔內容 (轉為 Base64) 以及憑證密碼加密，存放於 Supabase 的 `users` 表中。
2.  **執行端**：
    *   解密金鑰 (Master Key，32 字元) 僅存於 **GitHub Secrets**。
    *   GitHub Actions 啟動時，臨時從 Supabase 下載加密數據，並在**記憶體中進行解密**。
    *   憑證檔會被動態寫入虛擬機的臨時目錄中 (`/tmp` 或 `C:\Users\Willy\AppData\Local\Temp`)，並在執行結束後，隨著 GitHub Actions 虛擬機的銷毀而**完全抹除，不留任何痕跡**。

## 4. 資料庫架構 (Database Schema)

### Table 1: `users` (親友帳號與加密憑證表)
| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `id` | UUID (PK) | 唯一識別碼，預設為 `gen_random_uuid()` |
| `name` | VARCHAR | 親友稱呼 (例如：小明) |
| `line_user_id` | VARCHAR | LINE User ID (用於推送訊息) |
| `fubon_username` | TEXT | 加密後的身份證字號 (AES-256) |
| `fubon_password` | TEXT | 加密後的富邦密碼 (AES-256) |
| `fubon_ca_content` | TEXT | 加密後的憑證檔案 Base64 字串 (AES-256) |
| `fubon_ca_password`| TEXT | 加密後的憑證密碼 (AES-256) |
| `ct_id` | VARCHAR | 建立者識別碼 (Create ID) |
| `ct_date` | TIMESTAMP | 建立時間 (Create Date，預設為 `NOW()`) |
| `md_id` | VARCHAR | 修改者識別碼 (Modify ID) |
| `md_date` | TIMESTAMP | 修改時間 (Modify Date) |
| `dt_id` | VARCHAR | 刪除者識別碼 (Delete ID) |
| `dt_date` | TIMESTAMP | 刪除時間 (Delete Date，用於軟刪除) |

### Table 2: `daily_balances` (資產歷史紀錄表)
| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `id` | BIGINT (PK) | 唯一識別碼，自動遞增 |
| `user_id` | UUID (FK) | 關聯至 `users.id` |
| `date` | DATE | 交易日期 |
| `total_market_value`| NUMERIC | 當日持股總市值 |
| `unrealized_pnl` | NUMERIC | 當日累積未實現損益 |
| `holdings_json` | JSONB | 當日庫存快照 (用於次日比對計算每日損益) |
| `ct_id` | VARCHAR | 建立者識別碼 (Create ID) |
| `ct_date` | TIMESTAMP | 建立時間 (Create Date，預設為 `NOW()`) |
| `md_id` | VARCHAR | 修改者識別碼 (Modify ID) |
| `md_date` | TIMESTAMP | 修改時間 (Modify Date) |
| `dt_id` | VARCHAR | 刪除者識別碼 (Delete ID) |
| `dt_date` | TIMESTAMP | 刪除時間 (Delete Date，用於軟刪除) |

## 5. 核心邏輯：交易修正損益計算法 (Core P&L Logic)
為了避免買賣干擾每日損益，公式如下：
*   **每日總純損益 = 續抱股損益 + 新買入股損益 + 已賣出股損益**
    1.  **續抱股損益** = `(今日收盤價 - 昨日收盤價) * 昨日持股股數`
    2.  **新買入股損益** = `(今日收盤價 - 買入成交價) * 買入股數 - 手續費`
    3.  **已賣出股損益** = `(賣出成交價 - 昨日收盤價) * 賣出股數 - 手續費與稅`

## 6. 排程與自動化 (Workflow)
*   **Cron 設定**：`cron: "35 6 * * 1-5"` (對應台灣時間每週一至週五的 **14:35**)。
*   **執行流程**：
    1. 啟動 GitHub Actions。
    2. 調用開源 API 檢查今日是否為台灣股市交易日。若休市則立即結束。
    3. 連線至 Supabase 讀取加密用戶清單，迴圈為每位用戶解密憑證與帳密。
    4. 登入富邦 Neo API，查詢當日庫存、成交明細。
    5. 比對昨日 Supabase 的餘額數據，計算交易修正後的每日損益。
    6. 將今日餘額更新至 Supabase。
    7. 發送繁體中文損益報表至用戶的 LINE。
