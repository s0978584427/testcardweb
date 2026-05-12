# Render 部署指南 - API 整合修復

## 📋 修復內容清單

### ✅ 已實施的改進

#### 1. **強制 HTTPS 安全傳輸**
- ✅ 所有國際 API 請求已轉換為 HTTPS
  - pokemontcg.io: `https://api.pokemontcg.io/v2/cards`
  - ygoprodeck.com: `https://db.ygoprodeck.com/api/v7/cardinfo.php`
  - scryfall.com: `https://api.scryfall.com/cards/search`
- ✅ 自動檢測 HTTP 並升級為 HTTPS (`safe_request()` 函數)

#### 2. **CORS (跨域資源共享) 配置強化**
- ✅ 動態檢測 Render 環境 (`RENDER_EXTERNAL_URL`)
- ✅ 自動添加 Render 域名到 CORS 白名單
- ✅ 支持開發環境 (`localhost:5000`, `127.0.0.1:3000`)
- ✅ 添加 CORS 預檢請求處理 (OPTIONS 方法)
- ✅ 正確的 CORS 頭回應 (`Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`)

**代碼位置**: `app.py` - CORS 配置 (L14-41)

#### 3. **詳細錯誤日誌 - 前端 (Console)**
- ✅ `performCardSearch()` - 卡牌搜尋
  - 記錄 API URL、狀態碼、成功/失敗詳情
  - 診斷信息: 時間、源、錯誤類型
  - 範例輸出:
    ```javascript
    📡 [API 請求] 卡牌搜尋: /api/cards/search?keyword=pikachu...
    📊 [API 回應] 狀態碼: 200
    ✅ [API 成功] 卡牌搜尋結果: { source: 'pokemon', cardCount: 5, total: 120... }
    ```

- ✅ `performSearch()` - PChome & 組合搜尋
  - 同樣的日誌格式和診斷輸出

**代碼位置**: `templates/index.html` - JavaScript (L705-759, L661-721)

#### 4. **User-Agent 統一處理**
- ✅ 定義統一的瀏覽器 User-Agent 常數
  ```python
  BROWSER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...'
  ```
- ✅ 所有後端 API 請求自動添加 User-Agent
- ✅ `safe_request()` 包裝函數確保所有請求都有正確的 headers

**代碼位置**: `card_apis.py` - `safe_request()` 函數 (L43-103)

#### 5. **後端錯誤日誌增強**
- ✅ 詳細的 API 請求日誌 (日期、URL、狀態碼)
- ✅ 全局錯誤處理 (404, 500, Exception)
- ✅ 調試模式下返回詳細錯誤信息
- ✅ 日誌包含堆棧跟蹤 (exc_info=True)

**代碼位置**: `app.py` - 全局錯誤處理 (L58-79), `card_apis.py` - `safe_request()` (L43-103)

---

## 🚀 部署到 Render 的步驟

### 1. **環境變量設置** (Render Dashboard)
在 Render 環境變量設置中添加:
```
# 如果需要調試模式 (生產環境建議設為 false)
FLASK_ENV=production
DEBUG=false

# 可選: 日誌級別
LOG_LEVEL=INFO
```

### 2. **驗證 Render 自動配置**
Render 應該會自動檢測:
- `requirements.txt` - Python 依賴
- `Procfile` - 啟動命令
- `runtime.txt` - Python 版本

**確保這些文件存在**:
```bash
cat requirements.txt  # 檢查是否有 flask, flask-cors, requests 等
cat Procfile          # 應該有: web: gunicorn app:app
cat runtime.txt       # 應該有: python-3.11.5 (或您的版本)
```

### 3. **測試連接**
部署後，在瀏覽器控制台測試:

```javascript
// 開啟開發者工具 (F12) → Console 標籤

// 測試 Pokémon API
fetch('/api/cards/search?keyword=pikachu&source=pokemon&page=1&limit=5')
  .then(r => r.json())
  .then(d => console.log('✅ Pokemon:', d))
  .catch(e => console.error('❌', e))

// 測試 YuGiOh API
fetch('/api/cards/search?keyword=blue+eyes&source=yugioh&page=1&limit=5')
  .then(r => r.json())
  .then(d => console.log('✅ YuGiOh:', d))
  .catch(e => console.error('❌', e))

// 測試 MTG API
fetch('/api/cards/search?keyword=black+lotus&source=mtg&page=1&limit=5')
  .then(r => r.json())
  .then(d => console.log('✅ MTG:', d))
  .catch(e => console.error('❌', e))
```

---

## 🔍 除錯指南

### 如果在 Render 上出現 API 搜尋失敗:

#### **第 1 步: 查看 Render 日誌**
1. 登入 Render Dashboard
2. 進入 Service
3. 點擊 "Logs" 標籤
4. 搜尋錯誤信息，特別關注:
   - `❌ [連線失敗]` - 第三方 API 無法連接
   - `❌ [超時]` - API 響應超過 10 秒
   - `⚠️ API 返回 XXX` - HTTP 錯誤碼 (如 403, 429)

#### **第 2 步: 查看瀏覽器控制台**
1. 開啟網頁 → F12 → Console 標籤
2. 搜尋紅色錯誤信息 (前綴 `❌`)
3. 檢查:
   - CORS 錯誤? → 檢查 `RENDER_EXTERNAL_URL` 是否正確設置
   - 網路錯誤? → 檢查 Render 環境的網路連接
   - 超時錯誤? → 第三方 API 可能過載

#### **第 3 步: 常見問題排查**

| 錯誤信息 | 原因 | 解決方案 |
|---------|------|--------|
| `CORS policy: No 'Access-Control-Allow-Origin'` | CORS 配置未正確應用 | 檢查 `render_url` 是否被正確檢測 |
| `Failed to fetch` | 域名無法解析或網路不通 | 檢查 API URL 是否正確 (必須 HTTPS) |
| `Timeout` (超過 10 秒) | API 響應過慢 | 等待或改用代理 API |
| `HTTP 403` | 請求被拒絕 (缺少 User-Agent) | 已自動添加 User-Agent，應該不會出現 |
| `HTTP 429` | 超過 API 速率限制 | 減少搜尋頻率或使用緩存 |

### **重新部署修復**
如果對代碼有改動，在本地測試後推送:
```bash
git add .
git commit -m "Fix: Improve API error handling and CORS for Render"
git push origin master  # 或您的部署分支
```
Render 會自動重新部署。

---

## 📊 本地測試 (推薦部署前驗證)

### 1. **啟動開發伺服器**
```bash
# 激活虛擬環境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 運行 Flask
python app.py
```

### 2. **測試 API**
```bash
# 寶可夢搜尋
curl "http://localhost:5000/api/cards/search?keyword=pikachu&source=pokemon&page=1"

# 遊戲王搜尋
curl "http://localhost:5000/api/cards/search?keyword=blue+eyes&source=yugioh&page=1"

# MTG 搜尋
curl "http://localhost:5000/api/cards/search?keyword=black+lotus&source=mtg&page=1"
```

### 3. **檢查日誌輸出**
應該看到類似的日誌:
```
INFO:card_apis:🔍 [Pokémon TCG] 搜尋: 'pikachu', 頁碼: 1
📡 API 請求: GET https://api.pokemontcg.io/v2/cards?q=name:"pikachu"...
✅ 請求成功: https://api.pokemontcg.io/v2/cards?...
INFO:card_apis:✅ [Pokémon TCG] 成功獲取 5 張卡牌 (共 120 筆)
```

---

## 📝 關鍵修改摘要

### 後端 (`card_apis.py`)
- 新增 `safe_request()` 函數: 統一 HTTPS + User-Agent + 錯誤處理
- 更新 `get_pokemon_tcg_cards()`, `get_yugioh_cards()`, `get_magic_cards()` 
- 改用 `safe_request()` 代替直接 `requests.get()`
- 添加詳細的日誌信息 (✅ 成功, ❌ 失敗, ⚠️ 警告)

### 前端 (`templates/index.html`)
- 增強 `performCardSearch()` 的錯誤日誌
- 增強 `performSearch()` 的錯誤日誌
- 添加詳細的診斷信息到瀏覽器控制台
- 改進用戶錯誤提示信息

### 服務器 (`app.py`)
- 動態 CORS 配置: 支持 Render 環境
- 全局錯誤處理: 404, 500, Exception
- 添加 CORS 預檢請求處理

---

## ✅ 部署檢查清單

- [ ] 檢查 `requirements.txt` 包含所有依賴 (flask, flask-cors, requests, gunicorn)
- [ ] 檢查 `Procfile` 是否存在並正確配置
- [ ] 檢查 `runtime.txt` 指定正確的 Python 版本
- [ ] 在本地測試所有三個 API (Pokemon, YuGiOh, MTG)
- [ ] 推送到 git 並等待 Render 自動部署
- [ ] 部署完成後測試: 搜尋一張卡牌並查看瀏覽器控制台日誌
- [ ] 確認沒有 CORS 錯誤
- [ ] 確認 API 搜尋結果正常顯示

---

## 🎯 期望結果

**本地測試**:
- ✅ 所有三個 API 正常工作
- ✅ 瀏覽器控制台顯示詳細日誌 (📡 請求, 📊 回應, ✅ 成功)

**Render 部署後**:
- ✅ 網站可以訪問 (`https://your-service.render.com`)
- ✅ 卡牌搜尋功能正常 (不會退回到圖鑑模式)
- ✅ 瀏覽器控制台日誌清晰 (便於除錯)
- ✅ Render 日誌有詳細信息 (便於監控)

---

## 🔗 參考資源

- [Render 部署文檔](https://render.com/docs)
- [Flask CORS 文檔](https://flask-cors.readthedocs.io/)
- [MDN: CORS 指南](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Python requests 文檔](https://requests.readthedocs.io/)

---

**最後修改**: 2026-05-12
**修復版本**: v2.1 (Render 部署最佳化版)
