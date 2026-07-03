# 使用者自助註冊網站設計規格

## 專案概述

提供一個 LINE Login + GitHub Pages + Supabase Edge Function 的自助註冊網站，
讓親友可以自行填入富邦證券帳密、上傳 CA 憑證，完成註冊即可納入每日盤後損益回報系統。

## 架構

```
USER (手機/電腦)
    │ 點擊「使用 LINE 登入」
    ▼
LINE Login ── 授權回傳 line_user_id + display_name
    │
    ▼
GitHub Pages (website/index.html)
    │ 填表: 富邦帳號、密碼、CA 密碼
    │ 上傳 .p12 → 前端轉 base64
    │ POST JSON → Edge Function URL
    ▼
Supabase Edge Function (Deno / TypeScript)
    │ AES-256-CBC 加密 (與 crypto_utils.py 相容)
    │ upsert into users table
    ▼
Supabase users table
```

## 元件

### 1. LINE Login 頻道

- 在 LINE Developer Console 新增一個 **LINE Login** channel（非 Messaging API channel）
- 設定 Callback URL: `https://<你的帳號>.github.io/fubon-pnl-bot/website/callback.html`
- 登入後取得：`line_user_id`、`display_name`、`picture_url`（頭像）

### 2. 前端頁面 (GitHub Pages)

**使用 PKCE 流程**（靜態網站無法藏 `client_secret`）：
1. 生成 `code_verifier` + `code_challenge`
2. 導向 LINE Login 授權頁（含 `code_challenge`）
3. LINE redirect 回 callback URL 帶 `?code=...`
4. 前端用 `code` + `code_verifier` 向 LINE API 直接換 `access_token`
5. `access_token` 查 Profile API 取得 `user_id` + `display_name`

**檔案位置**: `website/index.html`（單一頁面）

頁面包含：

- **狀態 A - 未登入**: 「使用 LINE 登入」按鈕 + QR Code
- **狀態 B - 已登入**: 註冊表單
  - 名稱（取自 LINE，不可修改）
  - 富邦身分證字號 (`fubon_username`)
  - 富邦密碼 (`fubon_password`)
  - CA 憑證密碼 (`fubon_ca_password`)
  - `.p12` 檔案上傳（前端轉 Base64）
  - 送出按鈕 → POST JSON → Edge Function
  - 顯示成功/失敗訊息
- **頁尾**: LINE 加入好友 QR Code (`https://line.me/R/ti/p/%40659fctvt`)

### 3. Supabase Edge Function

**檔案位置**: `supabase/functions/register/index.ts`

功能：
- 接收 POST 請求，body 包含所有欄位
- 讀取 Supabase Secrets 中的 `MASTER_KEY`
- 對 `fubon_username`、`fubon_password`、`fubon_ca_content`、`fubon_ca_password` 執行 AES-256-CBC 加密
  - 使用 Node.js Web Crypto API 實作，演算法需與 `crypto_utils.py` 相容
  - 加密流程：產生 16 bytes IV → AES-256-CBC 加密 → PKCS7 填補 → IV + ciphertext → Base64
- 將結果 upsert 到 `users` table
  - `on_conflict = "line_user_id"`
  - `ct_id = "setup_web"`

### 4. 加密相容性

Edge Function 的加密輸出必須能被 `crypto_utils.py` 的 `decrypt()` 正確解密。
目前 Python 端使用：
- AES-256-CBC
- PKCS7 填補
- IV 前置於 ciphertext（共 16 + N bytes）
- 整體輸出 Base64
- Master Key 為 32 bytes hex 字串

Deno 的 Web Crypto API 支援 AES-CBC + PKCS7，可完全相容。

### 5. 錯誤處理

- 前端：表單驗證（必填欄位、`.p12` 檔案類型）
- Edge Function：
  - 缺少欄位回傳 `400`
  - `MASTER_KEY` 未設定回傳 `500`
  - 加密失敗回傳 `500`
  - 寫入成功回傳 `200 { success: true }`
  - 寫入失敗回傳 `500 { error: "..." }`

### 6. 部署

- GitHub Pages: 啟用 repo Settings → Pages → source: `main` branch, `/website` 目錄
- Edge Function: 使用 Supabase CLI 部署

### 7. 不在範圍內

- 不實作登入 session / cookie（每註冊一次就要重新 LINE Login）
- 不實作管理員後台
- 不實作修改既有使用者的功能（僅新增/更新）
- 不實作忘記密碼或重設功能

## 檔案清單

| 檔案 | 說明 |
|------|------|
| `website/index.html` | 單一頁面（LINE Login + 表單 + QR Code） |
| `supabase/functions/register/index.ts` | Edge Function 加密 + 寫入 DB |
| `supabase/functions/register/deno.lock` | Deno 鎖定檔 |
