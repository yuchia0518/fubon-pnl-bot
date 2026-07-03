# 使用者自助註冊網站 實作計畫

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推薦）或 superpowers:executing-plans 逐任務實現此計畫。步驟使用复选框（`- [ ]`）語法來追蹤進度。

**目標：** 建立一個 LINE Login + GitHub Pages + Supabase Edge Function 的自助註冊網站，讓親友自行填寫富邦帳密、上傳 CA 憑證後即可納入每日盤後損益系統。

**架構：** 前端為單一靜態頁面（`website/index.html`），透過 PKCE 流程與 LINE Login 整合，取得 `line_user_id` + `display_name` 後顯示註冊表單。表單送出後 POST JSON 到 Supabase Edge Function，後端執行 AES-256-CBC 加密後 upsert 到 `users` table。

**技術棧：** HTML/CSS/JS（前端）、Deno + TypeScript（Edge Function）、Supabase（資料庫）、LINE Login（認證）

---

## 檔案清單

| 檔案 | 類型 | 職責 |
|------|------|------|
| `website/index.html` | 創建 | 單一頁面：LINE Login + 註冊表單 + QR Code |
| `supabase/functions/register/index.ts` | 創建 | Edge Function：AES 加密 + Supabase upsert |
| `supabase/functions/register/deno.json` | 創建 | Deno 設定（匯入映射） |
| `website/style.css` | 創建 | 頁面樣式（可選，也可 inline） |

---

### 任務 1：實作 Edge Function — AES 加密工具

**檔案：**
- 創建：`supabase/functions/register/index.ts`

此任務實作與 Python `crypto_utils.py` 相容的 AES-256-CBC 加密。

```python
# Python decrypt 預期格式：
# key = bytes.fromhex(MASTER_KEY)  # 32 bytes
# combined = base64_decode(input)   # IV(16) + ciphertext(N)
# iv = combined[:16]
# ciphertext = combined[16:]
# AES-CBC decrypt + PKCS7 unpad → plaintext
```

- [ ] **步驟 1：建立 `supabase/functions/register/index.ts`**

```typescript
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

// AES-256-CBC encrypt, output compatible with Python crypto_utils.decrypt()
async function encrypt(plainText: string, masterKeyHex: string): Promise<string> {
  const keyBytes = hexToBytes(masterKeyHex);
  const key = await crypto.subtle.importKey(
    "raw", keyBytes, { name: "AES-CBC" }, false, ["encrypt"]
  );
  const iv = crypto.getRandomValues(new Uint8Array(16));
  const encoded = new TextEncoder().encode(plainText);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-CBC", iv }, key, encoded);
  // Combine iv + ciphertext
  const combined = new Uint8Array(iv.length + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.length);
  return btoa(String.fromCharCode(...combined));
}

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

// For testing: verify the output can be decrypted by Python
// echo "encrypt('test', MASTER_KEY)" | deno run -
```

- [ ] **步驟 2：加入 main handler + Supabase 寫入**

```typescript
import { createClient } from "npm:@supabase/supabase-js@2";

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const mk = Deno.env.get("MASTER_KEY");
  if (!mk) {
    return new Response(JSON.stringify({ error: "MASTER_KEY not set" }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const body = await req.json();
    const { name, line_user_id, fubon_username, fubon_password, fubon_ca_content, fubon_ca_password } = body;

    if (!name || !line_user_id || !fubon_username || !fubon_password || !fubon_ca_content || !fubon_ca_password) {
      return new Response(JSON.stringify({ error: "Missing required fields" }), {
        status: 400, headers: { "Content-Type": "application/json" },
      });
    }

    const supaUrl = Deno.env.get("SUPABASE_URL")!;
    const supaKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supaUrl, supaKey);

    const encrypted = {
      fubon_username: await encrypt(fubon_username, mk),
      fubon_password: await encrypt(fubon_password, mk),
      fubon_ca_content: await encrypt(fubon_ca_content, mk),
      fubon_ca_password: await encrypt(fubon_ca_password, mk),
    };

    const { data, error } = await supabase
      .from("users")
      .upsert({
        name,
        line_user_id,
        ...encrypted,
        ct_id: "setup_web",
      }, { onConflict: "line_user_id" })
      .select();

    if (error) throw error;

    return new Response(JSON.stringify({ success: true, user: data }), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }
});
```

- [ ] **步驟 3：建立 `supabase/functions/register/deno.json`**

```json
{
  "imports": {
    "@supabase/supabase-js": "npm:@supabase/supabase-js@2"
  }
}
```

- [ ] **步驟 4：Commit**

```bash
git add supabase/functions/register/index.ts supabase/functions/register/deno.json
git commit -m "feat: add Edge Function for user registration"
```

---

### 任務 2：前端頁面 — LINE Login + 註冊表單

**檔案：**
- 創建：`website/index.html`

- [ ] **步驟 1：建立 `website/index.html`**

單一頁面，包含三個狀態：
1. **未登入**：LINE Login 按鈕 + QR Code
2. **已登入**：註冊表單（自動帶入名稱）
3. **已送出**：成功/失敗訊息

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>富邦 P&L  Bot - 註冊</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }
.container { max-width: 480px; width: 100%; padding: 24px; }
.card { background: white; border-radius: 16px; padding: 32px 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 16px; }
h1 { font-size: 24px; margin-bottom: 8px; text-align: center; }
p.subtitle { color: #666; text-align: center; margin-bottom: 24px; font-size: 14px; }
.btn-line { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 14px; background: #06C755; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; text-decoration: none; }
.btn-line:hover { background: #05b84c; }
.btn-line img { width: 24px; height: 24px; }
.btn-submit { width: 100%; padding: 14px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
.btn-submit:hover { background: #1558b0; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.form-group input { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; }
.form-group input:focus { outline: none; border-color: #1a73e8; }
.form-group .hint { font-size: 12px; color: #888; margin-top: 2px; }
.qr-section { text-align: center; margin-top: 16px; }
.qr-section img { width: 160px; height: 160px; }
.qr-section p { font-size: 13px; color: #666; margin-top: 8px; }
.hidden { display: none; }
.msg { padding: 12px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
.msg.success { background: #e6f4ea; color: #1e7e34; }
.msg.error { background: #fce8e6; color: #c5221f; }
.user-info { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; padding: 12px; background: #f8f9fa; border-radius: 8px; }
.user-info img { width: 48px; height: 48px; border-radius: 50%; }
.user-info .name { font-weight: 600; }
.user-info .sub { font-size: 13px; color: #666; }
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <h1>📊 富邦 P&amp;L Bot</h1>
    <p class="subtitle">每日盤後自動回報損益</p>

    <!-- 狀態 A: 未登入 -->
    <div id="state-login">
      <a id="lineLoginBtn" class="btn-line" href="#">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.477 2 2 5.973 2 10.855c0 2.84 1.635 5.38 4.176 7.065-.246.93-.804 2.894-.92 3.342-.147.572.212.48.46.354.17-.087 2.514-1.658 3.773-2.567A12.06 12.06 0 0012 19.71c5.523 0 10-3.973 10-8.855S17.523 2 12 2z"/></svg>
        使用 LINE 登入
      </a>
      <div class="qr-section">
        <img src="https://qr-official.line.me/sid/L/659fctvt.png" alt="LINE QR">
        <p>加入好友後，點上方按鈕註冊</p>
      </div>
    </div>

    <!-- 狀態 B: 已登入 -->
    <div id="state-form" class="hidden">
      <div class="user-info" id="userInfo"></div>
      <div id="formMsg"></div>
      <form id="registerForm">
        <div class="form-group">
          <label>名稱</label>
          <input type="text" id="inputName" readonly>
        </div>
        <div class="form-group">
          <label>富邦身分證字號</label>
          <input type="text" id="inputUsername" placeholder="請輸入身分證字號" required>
        </div>
        <div class="form-group">
          <label>富邦密碼</label>
          <input type="password" id="inputPassword" placeholder="請輸入密碼" required>
        </div>
        <div class="form-group">
          <label>CA 憑證密碼</label>
          <input type="password" id="inputCaPwd" placeholder="預設為身分證字號" required>
          <div class="hint">富邦證券 CA 憑證的密碼</div>
        </div>
        <div class="form-group">
          <label>CA 憑證檔案 (.p12)</label>
          <input type="file" id="inputCaFile" accept=".p12" required>
          <div class="hint">請上傳富邦證券下載的 CA 憑證</div>
        </div>
        <button type="submit" class="btn-submit" id="btnSubmit">送出註冊</button>
      </form>
    </div>

    <!-- 狀態 C: 成功 -->
    <div id="state-success" class="hidden">
      <div class="msg success">✅ 註冊成功！明日即可收到盤後報表。</div>
    </div>
  </div>
</div>

<script>
// === LINE Login PKCE ===
const CHANNEL_ID = ''; // 使用者填入
const REDIRECT_URI = window.location.origin + window.location.pathname;
const SCOPE = 'profile openid';

function generateCodeVerifier() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  let verifier = '';
  const array = new Uint8Array(64);
  crypto.getRandomValues(array);
  for (const v of array) verifier += chars[v % chars.length];
  return verifier;
}

async function generateCodeChallenge(verifier) {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

// Handle callback from LINE
async function handleCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const storedVerifier = sessionStorage.getItem('code_verifier');

  if (code && storedVerifier) {
    try {
      // Exchange code for token
      const tokenRes = await fetch('https://api.line.me/oauth2/v2.1/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'authorization_code',
          code,
          redirect_uri: REDIRECT_URI,
          client_id: CHANNEL_ID,
          code_verifier: storedVerifier,
        }),
      });
      const tokenData = await tokenRes.json();
      if (!tokenData.access_token) throw new Error('Token exchange failed');

      // Get user profile
      const profileRes = await fetch('https://api.line.me/v2/profile', {
        headers: { Authorization: `Bearer ${tokenData.access_token}` },
      });
      const profile = await profileRes.json();

      sessionStorage.setItem('line_user_id', profile.userId);
      sessionStorage.setItem('line_display_name', profile.displayName);
      if (profile.pictureUrl) sessionStorage.setItem('line_picture', profile.pictureUrl);

      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    } catch (e) {
      document.getElementById('formMsg').innerHTML = '<div class="msg error">LINE 登入失敗: ' + e.message + '</div>';
    }
  }
  sessionStorage.removeItem('code_verifier');
}

// Init LINE Login button
function initLineLogin() {
  const btn = document.getElementById('lineLoginBtn');
  btn.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!CHANNEL_ID) { alert('LINE Login Channel ID 尚未設定'); return; }
    const verifier = generateCodeVerifier();
    sessionStorage.setItem('code_verifier', verifier);
    const challenge = await generateCodeChallenge(verifier);
    const authUrl = 'https://access.line.me/oauth2/v2.1/authorize?' + new URLSearchParams({
      response_type: 'code',
      client_id: CHANNEL_ID,
      redirect_uri: REDIRECT_URI,
      scope: SCOPE,
      state: 'register',
      code_challenge: challenge,
      code_challenge_method: 'S256',
    });
    window.location.href = authUrl;
  });
}

// Show form if logged in
function showFormIfLoggedIn() {
  const userId = sessionStorage.getItem('line_user_id');
  if (userId) {
    document.getElementById('state-login').classList.add('hidden');
    document.getElementById('state-form').classList.remove('hidden');
    document.getElementById('inputName').value = sessionStorage.getItem('line_display_name') || '';

    const pic = sessionStorage.getItem('line_picture');
    const name = sessionStorage.getItem('line_display_name') || userId;
    document.getElementById('userInfo').innerHTML = pic
      ? '<img src="' + pic + '" alt=""><div><div class="name">' + name + '</div><div class="sub">已透過 LINE 認證</div></div>'
      : '<div><div class="name">' + name + '</div><div class="sub">已透過 LINE 認證</div></div>';
  }
}

// Handle form submit
document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('btnSubmit');
  btn.disabled = true;
  btn.textContent = '送出中...';

  const fileInput = document.getElementById('inputCaFile');
  const file = fileInput.files[0];
  if (!file) { alert('請選擇 CA 憑證檔案'); btn.disabled = false; btn.textContent = '送出註冊'; return; }

  const reader = new FileReader();
  reader.onload = async () => {
    const base64Content = reader.result.split(',')[1];
    const payload = {
      name: document.getElementById('inputName').value,
      line_user_id: sessionStorage.getItem('line_user_id'),
      fubon_username: document.getElementById('inputUsername').value,
      fubon_password: document.getElementById('inputPassword').value,
      fubon_ca_content: base64Content,
      fubon_ca_password: document.getElementById('inputCaPwd').value,
    };

    try {
      const res = await fetch('https://<PROJECT>.supabase.co/functions/v1/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        document.getElementById('state-form').classList.add('hidden');
        document.getElementById('state-success').classList.remove('hidden');
      } else {
        document.getElementById('formMsg').innerHTML = '<div class="msg error">註冊失敗: ' + (data.error || '未知錯誤') + '</div>';
      }
    } catch (e) {
      document.getElementById('formMsg').innerHTML = '<div class="msg error">網路錯誤: ' + e.message + '</div>';
    }
    btn.disabled = false;
    btn.textContent = '送出註冊';
  };
  reader.readAsDataURL(file);
});

// Init
(async () => {
  await handleCallback();
  initLineLogin();
  showFormIfLoggedIn();
})();
</script>
</body>
</html>
```

> **注意**：`CHANNEL_ID` 和 `https://<PROJECT>.supabase.co/functions/v1/register` 這兩個值需要在部署前填入。

- [ ] **步驟 2：Commit**

```bash
git add website/index.html
git commit -m "feat: add registration website with LINE Login"
```

---

### 任務 3：部署前設定

**檔案：**
- 修改：`website/index.html`

- [ ] **步驟 1：使用者自行建立 LINE Login Channel**

使用者需前往 [LINE Developers Console](https://developers.line.biz/console/) 操作：
1. 新增一個 Provider（或沿用既有 Provider）
2. 新增 **LINE Login** channel
3. 取得 **Channel ID**
4. 在 Channel 設定 → **Callback URL** 填入 GitHub Pages 網址，例如：
   `https://yuchia0518.github.io/fubon-pnl-bot/website/index.html`
5. 註記：不需要 `Client Secret`（PKCE 流程不需要）

- [ ] **步驟 2：將 Channel ID 填入前端**

使用者將步驟 1 取得的 Channel ID 填入 `website/index.html` 中的 `CHANNEL_ID` 變數。

- [ ] **步驟 3：部署 Edge Function**

使用者需安裝 [Supabase CLI](https://supabase.com/docs/guides/cli)，然後執行：

```bash
supabase login
supabase link --project-ref <PROJECT_REF>
supabase secrets set MASTER_KEY=<實際的 MASTER KEY>
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<實際的 service_role key>
supabase functions deploy register
```

邊峰函數 URL 為：`https://<PROJECT_REF>.supabase.co/functions/v1/register`

- [ ] **步驟 4：將 Edge Function URL 填入前端**

使用者將步驟 3 的 URL 填入 `website/index.html` 中的 `fetch()` 調用。

- [ ] **步驟 5：啟用 GitHub Pages**

1. 前往 GitHub repo → Settings → Pages
2. Source: `Deploy from a branch`
3. Branch: `main`, folder: `/website`
4. 完成後網站網址：`https://yuchia0518.github.io/fubon-pnl-bot/website/`

- [ ] **步驟 6：Commit 最終設定**

```bash
git add website/index.html
git commit -m "chore: configure LINE Login Channel ID and Edge Function URL"
git push
```
