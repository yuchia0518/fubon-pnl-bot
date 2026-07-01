-- ============================================================
-- Supabase 資料表建立腳本
-- 專案：富邦證券每日盤後損益回報系統
-- 注意：請在 Supabase Dashboard > SQL Editor 中執行此腳本
-- ============================================================

-- 啟用 UUID 擴充功能
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- Table 1: users (親友帳號與加密憑證表)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    line_user_id VARCHAR(255) NOT NULL UNIQUE,
    fubon_username TEXT NOT NULL,
    fubon_password TEXT NOT NULL,
    fubon_ca_content TEXT NOT NULL,
    fubon_ca_password TEXT NOT NULL,

    -- 稽核欄位 (CT = Create, MD = Modify, DT = Delete)
    ct_id VARCHAR(100) NOT NULL DEFAULT 'system',
    ct_date TIMESTAMP NOT NULL DEFAULT NOW(),
    md_id VARCHAR(100),
    md_date TIMESTAMP,
    dt_id VARCHAR(100),
    dt_date TIMESTAMP
);

-- 建立索引：快速查找未被軟刪除的活躍用戶
CREATE INDEX IF NOT EXISTS idx_users_active ON users (dt_date)
    WHERE dt_date IS NULL;

-- 建立索引：依據 LINE User ID 查詢
CREATE INDEX IF NOT EXISTS idx_users_line_id ON users (line_user_id);


-- ============================================================
-- Table 2: daily_balances (資產歷史紀錄表)
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_balances (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_market_value NUMERIC(15, 2) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(15, 2) NOT NULL DEFAULT 0,
    holdings_json JSONB,

    -- 稽核欄位 (CT = Create, MD = Modify, DT = Delete)
    ct_id VARCHAR(100) NOT NULL DEFAULT 'system',
    ct_date TIMESTAMP NOT NULL DEFAULT NOW(),
    md_id VARCHAR(100),
    md_date TIMESTAMP,
    dt_id VARCHAR(100),
    dt_date TIMESTAMP
);

-- 建立索引：快速查詢特定用戶最近一筆資產紀錄
CREATE INDEX IF NOT EXISTS idx_balances_user_date ON daily_balances (user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_balances_active ON daily_balances (dt_date)
    WHERE dt_date IS NULL;


-- ============================================================
-- Row Level Security (RLS) 策略
-- 此 Bot 使用 service_role 金鑰進行後端存取，
-- service_role 可自動繞過 RLS，因此以下策略設為開放。
-- 若未來改為使用 anon 金鑰，請調整策略條件。
-- ============================================================

-- 啟用 RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_balances ENABLE ROW LEVEL SECURITY;

-- 允許所有操作 (供 service_role 背景服務使用)
CREATE POLICY "Allow all for users" ON users
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all for daily_balances" ON daily_balances
    FOR ALL
    USING (true)
    WITH CHECK (true);


-- ============================================================
-- 備註說明
-- ============================================================
-- holdings_json 格式範例 (JSONB):
-- {
--   "2330": {"qty": 1000, "close": 962.0},
--   "2317": {"qty": 2000, "close": 200.5}
-- }
--
-- fubon_* 欄位存放的是經過 AES-256-CBC 加密後的密文 (Base64 字串)，
-- 請勿在此存放明文帳密或憑證。
