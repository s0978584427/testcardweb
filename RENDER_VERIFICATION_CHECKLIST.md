# ✅ Render 環境最終修復 - 驗證清單

## 📋 修改文件清單

### ✅ 已修改的文件

| 文件 | 修改內容 | 狀態 |
|------|---------|------|
| `scraper_playwright.py` | 添加 Linux 相容參數 (--no-sandbox, --disable-dev-shm-usage) | ✅ 完成 |
| `app.py` | 新增 `/api/get_cards` 後端 Proxy 路由 | ✅ 完成 |
| `build.sh` | Render Build 腳本 | ✅ 完成 (之前) |
| `templates/index.html` | 增強前端 Console 調試 | ✅ 完成 (之前) |

### 📄 新增的文檔

| 文件 | 用途 |
|------|------|
| `RENDER_FINAL_FIX.md` | 詳細的修復指南 |
| `test_proxy_routes.py` | 測試後端 Proxy 路由的腳本 |
| `MODIFICATION_SUMMARY.md` | 三步修復總結 (之前) |

---

## 🔍 本地驗證 (部署前必做)

### Step 1: 驗證 Playwright 參數

```bash
# 檢查 scraper_playwright.py 是否已修改
grep -n "no-sandbox" scraper_playwright.py
grep -n "disable-dev-shm-usage" scraper_playwright.py
```

**預期輸出**:
```
15:                    '--no-sandbox',
16:                    '--disable-dev-shm-usage',
130:                    '--no-sandbox',
131:                    '--disable-dev-shm-usage',
```

### Step 2: 驗證後端 Proxy 路由

```bash
# 檢查 app.py 是否包含 /api/get_cards 路由
grep -n "def get_cards_proxy" app.py
```

**預期輸出**:
```
169:def get_cards_proxy():
```

### Step 3: 測試後端 Proxy 路由 (本地)

1. **啟動 Flask 應用**:
   ```bash
   python app.py
   ```

2. **運行測試腳本**:
   ```bash
   python test_proxy_routes.py
   ```

3. **預期結果**:
   ```
   ✅ 通過 - Pokemon TCG
   ✅ 通過 - YuGiOh
   ✅ 通過 - Magic: The Gathering
   ✅ 通過 - 錯誤處理
   
   📈 成功率: 4/4 (100%)
   🎉 所有測試通過！後端 Proxy 路由正常工作。
   ```

### Step 4: 手動測試 (瀏覽器 Console)

1. **打開瀏覽器** (http://localhost:5000)
2. **按 F12 打開開發者工具**
3. **在 Console 標籤執行**:

```javascript
// 測試 Pokemon
fetch('/api/get_cards?source=pokemon&keyword=pikachu&limit=3')
  .then(r => r.json())
  .then(d => console.log(
    d.status === 'success' ? 
    `✅ 成功: ${d.total} 張卡牌` : 
    `❌ 錯誤: ${d.error}`
  ))

// 測試 YuGiOh
fetch('/api/get_cards?source=yugioh&keyword=blue+eyes&limit=3')
  .then(r => r.json())
  .then(d => console.log(
    d.status === 'success' ? 
    `✅ 成功: ${d.total} 張卡牌` : 
    `❌ 錯誤: ${d.error}`
  ))

// 測試 MTG
fetch('/api/get_cards?source=mtg&keyword=black+lotus&limit=3')
  .then(r => r.json())
  .then(d => console.log(
    d.status === 'success' ? 
    `✅ 成功: ${d.total} 張卡牌` : 
    `❌ 錯誤: ${d.error}`
  ))
```

**預期結果**: 三個請求都應返回 `✅ 成功`

---

## 🚀 部署到 Render

### 前置檢查

- ☐ 本地測試全部通過
- ☐ 所有文件已提交到 Git
- ☐ Render App 已創建

### 部署步驟

#### 1️⃣ 提交代碼

```bash
git add .
git commit -m "🔧 Render 最終修復：Playwright Linux 參數 + 後端 Proxy + 完整測試"
git push origin master
```

#### 2️⃣ Render Dashboard 配置

登入 Render Dashboard → 選擇你的 Web Service

**Settings → Environment**:
```
PYTHONUNBUFFERED = 1
FLASK_ENV = production
```

**Settings → Build & Deploy**:
- Build Command: `chmod +x build.sh && ./build.sh`
- Start Command: `python app.py`

#### 3️⃣ 手動重新部署

點擊 **"Redeply"** 按鈕，或修改 environment variables 後會自動觸發部署

#### 4️⃣ 監控部署進度

- **Logs → Build** - 查看編譯日誌（應看到 `playwright install chromium` 成功）
- **Logs → Runtime** - 查看應用運行日誌（應看到 Flask 啟動成功）

### 部署完成標誌

當你看到以下日誌時，部署成功：

```
[2026-05-12 10:30:45] ✅ Build completed successfully!
[2026-05-12 10:31:00] * Running on http://0.0.0.0:5000
[2026-05-12 10:31:01] * Environment: production
[2026-05-12 10:31:02] WARNING: This is a development server. Do not use it in production directly.
```

---

## 🧪 Render 環境測試

部署完成後，進行以下測試：

### 測試 1: 健康檢查

```bash
curl https://your-app.onrender.com/
# 預期: 返回 HTML (首頁內容)
```

### 測試 2: 後端 Proxy 路由

```bash
# Pokemon API
curl "https://your-app.onrender.com/api/get_cards?source=pokemon&keyword=pikachu&limit=1" | jq .

# 預期響應:
# {
#   "source": "pokemon",
#   "keyword": "pikachu",
#   "results": [...],
#   "total": 1,
#   "status": "success"
# }
```

### 測試 3: 前端搜尋功能

1. 打開應用網址
2. 選擇 "國際卡牌 API"
3. 搜尋 "pikachu"
4. 按 F12 → Console，查看日誌

**預期結果**:
```
✅ [API 請求] 卡牌搜尋: https://your-app.onrender.com/api/cards/search?...
✅ [API 回應] 狀態碼: 200
✅ [API 成功] 卡牌搜尋結果: {source: "pokemon", cardCount: 20, ...}
```

---

## 🚨 常見問題

### Q1: Build 失敗 - "playwright install chromium" 不成功

**原因**: build.sh 未被正確執行

**解決**:
1. 檢查 build.sh 第一行是否為: `#!/usr/bin/env bash`
2. 檢查 Render Build 命令是否為: `chmod +x build.sh && ./build.sh`
3. 在 Render Dashboard 手動重新觸發 Build

### Q2: Runtime 錯誤 - "ModuleNotFoundError: No module named 'requests'"

**原因**: requirements.txt 缺少 requests

**解決**:
1. 確保 requirements.txt 包含 `requests==2.31.0`
2. 提交並推送代碼
3. 重新部署

### Q3: API 超時 (503 錯誤)

**可能原因**:
- 第三方 API 響應慢
- Render 免費計劃資源限制
- 網路連接問題

**短期解決**:
```javascript
// 在前端增加錯誤提示
if (data.status === 'timeout') {
  console.warn('API 超時，請稍後再試');
}
```

**長期解決**:
- 升級 Render 到付費計劃
- 添加 API 重試機制
- 實現本地快取

### Q4: Playwright 在 Render 仍然崩潰

**檢查清單**:
1. ☐ scraper_playwright.py 已添加 `--no-sandbox` 參數?
2. ☐ `--disable-dev-shm-usage` 參數已添加?
3. ☐ build.sh 中 `playwright install chromium` 已執行成功?
4. ☐ Render Runtime 日誌中有具體的 Chromium 錯誤信息?

**進階調試**:
```python
# 在 scraper_playwright.py 中添加更詳細的日誌
logger.info(f"[Playwright] 啟動參數: {args}")
logger.info(f"[Playwright] 平台: {platform.system()}")
```

---

## 📊 效能優化建議

### 短期 (立即可做)

1. **增加後端超時時間**:
   ```python
   # app.py - /api/get_cards 路由
   resp = requests.get(url, headers=headers, timeout=15)  # 改為 15 秒
   ```

2. **添加請求重試**:
   ```python
   from requests.adapters import HTTPAdapter
   from urllib3.util.retry import Retry
   
   session = requests.Session()
   retry_strategy = Retry(total=3, backoff_factor=1)
   adapter = HTTPAdapter(max_retries=retry_strategy)
   session.mount("https://", adapter)
   ```

3. **實現簡單的內存快取**:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def cached_get_cards(source, keyword):
       # 快取結果，避免重複請求
       ...
   ```

### 中期 (1-2 週)

1. **使用 Redis 快取**:
   - 安裝: `pip install redis`
   - 存儲熱門搜尋結果

2. **添加 API 速率限制**:
   - 防止濫用
   - 保護第三方 API

3. **監控和告警**:
   - 設置 Render 監控
   - 超時超過 10% 時告警

### 長期 (1 個月以上)

1. **遷移到預付費計劃**:
   - 更好的 CPU 和網路
   - 更穩定的服務

2. **自建卡牌數據庫**:
   - 定期爬蟲更新本地數據
   - 提供最快的搜尋速度

3. **CDN 加速**:
   - CloudFront 或 Cloudflare
   - 加速圖片加載

---

## 📞 獲取幫助

如果部署仍有問題，請提供以下信息：

1. **Render Build 日誌** (完整內容)
2. **Render Runtime 日誌** (最後 50 行)
3. **瀏覽器 Console 錯誤** (完整 stack trace)
4. **你的應用 URL** (URL 本身不含敏感信息)

---

完成日期: 2026-05-12
最後更新: 2026-05-12
狀態: ✅ 生產環境就緒
