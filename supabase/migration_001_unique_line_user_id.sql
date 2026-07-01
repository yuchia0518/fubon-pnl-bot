-- Migration 001: 為 users.line_user_id 增加 UNIQUE 限制，避免重複註冊
-- 
-- 注意：如果目前有重複的 line_user_id，請先手動清理再執行此腳本。
-- 查詢重複資料：SELECT line_user_id, COUNT(*) FROM users GROUP BY line_user_id HAVING COUNT(*) > 1;

ALTER TABLE users ADD CONSTRAINT users_line_user_id_unique UNIQUE (line_user_id);
