# Render 環境最終修復指南

## 🎯 三大修復要點

### 1️⃣ Playwright Linux 相容參數（已完成 ✅）

**文件**: `scraper_playwright.py`

修改了以下函數的 `browser.launch()` 參數：
- `scrape_ruten_playwright()`
- `scrape_shopee_playwright()`

**新增參數**:
```python
browser = p.chromium.launch(
    headless=True,
    args=[
        '--no-sandbox',                    # ✅ Linux 必需 - 禁用沙箱
        '--disable-dev-shm-usage',        # ✅ Linux 必需 - 避免共享內存不足
        '--disable-gpu',                  # ✅ 禁用 GPU (雲端環境無 GPU)
        '--single-process',               # Render 環境優化
    ]
)
```

**影響**: 確保 Playwright 在 Render 的 Docker/Linux 環境中能正常啟動瀏覽器。

---

### 2️⃣ 後端 Proxy 路由（已完成 ✅）

**文件**: `app.py`

新增路由: `/api/get_cards` (約 300 行代碼)

**關鍵優勢**:
- ✅ 前端不直接請求 pokemontcg.io、ygoprodeck.com、scryfall.com
- ✅ 後端使用 Python `requests` 庫轉發，避免 CORS 問題
- ✅ 規避 Render IP 被第三方 API 封鎖
- ✅ 詳細的錯誤返回（包含 HTTP 狀態碼和具體原因）

**使用方式**:

前端調用:
```javascript
fetch('/api/get_cards?source=pokemon&keyword=pikachu&limit=20')
  .then(r => r.json())
  .then(data => {
    if (data.status === 'success') {
      console.log('✅ 卡牌獲取成功:', data.results);
    } else {
      console.error('❌ API 錯誤:', data.error, data.details);
    }
  })
```

**支持的來源**:
- `pokemon` - pokemontcg.io
- `yugioh` - ygoprodeck.com  
- `mtg` - scryfall.com

**錯誤返回範例**:
```json
{
  "error": "Pokemon TCG API 請求超時 (>= 10s)",
  "status": "timeout",
  "source": "pokemon"
}
```

---

### 3️⃣ 環境變數檢查（已驗證 ✅）

檢查結果：**程式碼不依賴任何 API Key**

- ✅ pokemontcg.io - 無需 API Key（公開 API）
- ✅ ygoprodeck.com - 無需 API Key（公開 API）
- ✅ scryfall.com - 無需 API Key（公開 API）

如果將來需要添加 API Key（例如升級後付費 API），請在 Render Dashboard 設定:
```
POKEMON_API_KEY=your_key_here
YUGIOH_API_KEY=your_key_here
MTG_API_KEY=your_key_here
```

然後在 `app.py` 中使用：
```python
import os
pokemon_key = os.environ.get('POKEMON_API_KEY')
```

---

## 🚀 部署到 Render

### Step 1: 提交代碼

```bash
git add .
git commit -m "🔧 Render 最終修復：Playwright Linux 相容 + 後端 Proxy + 詳細錯誤"
git push origin master
```

### Step 2: Render Dashboard 配置

進入 Web Service → Settings，確認以下配置：

| 項目 | 值 |
|------|-----|
| **Build Command** | `chmod +x build.sh && ./build.sh` |
| **Start Command** | `python app.py` |
| **PYTHONUNBUFFERED** | `1` |
| **FLASK_ENV** | `production` |

### Step 3: 監控部署日誌

#### Build 階段（3-5 分鐘）
```
📦 Installing Python dependencies...
🌐 Installing Playwright Chromium browser for Render environment...
[1000s | Downloading Chromium... | 100% ]
✅ Build completed successfully!
```

如果看到:
- ❌ `playwright install chromium` 失敗 → 檢查 build.sh 是否正確
- ❌ `pip install` 失敗 → 檢查 requirements.txt 依賴

#### Runtime 階段（啟動應用）
```
 * Running on http://0.0.0.0:5000
 * Environment: production
```

如果看到:
- ❌ `ModuleNotFoundError` → 某個依賴未安裝
- ❌ `Address already in use` → 埠口佔用（不常見）

### Step 4: 測試 API

#### 使用 Chrome DevTools Console

```javascript
// 測試 Pokemon 卡牌
fetch('/api/get_cards?source=pokemon&keyword=pikachu&limit=5')
  .then(r => r.json())
  .then(data => console.log(JSON.stringify(data, null, 2)))
  .catch(e => console.error('❌ 錯誤:', e))

// 測試 YuGiOh 卡牌
fetch('/api/get_cards?source=yugioh&keyword=blue+eyes&limit=5')
  .then(r => r.json())
  .then(data => console.log(JSON.stringify(data, null, 2)))
  .catch(e => console.error('❌ 錯誤:', e))

// 測試 MTG 卡牌
fetch('/api/get_cards?source=mtg&keyword=black+lotus&limit=5')
  .then(r => r.json())
  .then(data => console.log(JSON.stringify(data, null, 2)))
  .catch(e => console.error('❌ 錯誤:', e))
```

#### 預期成功回應

```json
{
  "source": "pokemon",
  "keyword": "pikachu",
  "results": [
    {
      "id": "sv04pt-25",
      "title": "Pikachu",
      "source": "pokemon",
      "img_url": "https://images.pokemontcg.io/sv04pt/25_hires.png",
      "img_large": "https://images.pokemontcg.io/sv04pt/25_hires.png",
      "set": "Pokémon 151",
      "rarity": "Common",
      "hp": "40"
    },
    ...
  ],
  "total": 5,
  "status": "success",
  "timestamp": "2026-05-12T10:30:45.123456"
}
```

---

## 🔍 故障排查

### 症狀 1: Build 失敗

**日誌信息**:
```
ERROR: playwright install chromium failed
```

**解決**:
1. 檢查 build.sh 是否存在且可執行
2. 檢查 requirements.txt 是否包含 playwright
3. 手動重新啟動 Render Build

### 症狀 2: API 返回 500 錯誤

**前端看到**:
```json
{
  "error": "Pokemon TCG API 請求失敗: ...",
  "status": "api_error"
}
```

**排查步驟**:
1. 查看 Render Runtime 日誌，找出具體錯誤
2. 確認 Playwright 已正確安裝
3. 檢查網路連接（Render 能否訪問外部 API）

### 症狀 3: API 超時（503 錯誤）

**前端看到**:
```json
{
  "error": "Pokemon TCG API 請求超時 (>= 10s)",
  "status": "timeout"
}
```

**可能原因**:
- 第三方 API 響應慢
- Render 的網路連接不穩定
- 免費計劃資源限制

**解決**:
1. 增加超時時間：修改 app.py 的 `timeout=10` → `timeout=15`
2. 升級 Render 計劃（付費版有更好的網路和 CPU）
3. 添加重試機制

### 症狀 4: 前端 Console 看到 CORS 錯誤

**如果有的話** - 說明 Flask-CORS 配置有問題

**檢查**:
```python
# app.py 確保已配置 CORS
from flask_cors import CORS
CORS(app, resources={r"/api/*": {...}})
```

---

## 📊 修復前後對比

| 項目 | 修復前 ❌ | 修復後 ✅ |
|------|----------|----------|
| **Playwright 啟動** | Docker 環境崩潰 | 正常運行 (--no-sandbox) |
| **API 請求方式** | 前端直接請求 (CORS 問題) | 後端 Proxy (安全) |
| **IP 封鎖風險** | 高 (所有用戶共享 IP) | 低 (集中轉發) |
| **錯誤信息** | 無詳細信息 | 詳細的錯誤描述和狀態碼 |
| **超時處理** | 無 | 明確區分 timeout/connection_error/api_error |
| **環境變數支持** | 無 | 預留接口 (POKEMON_API_KEY 等) |

---

## 📝 相關文件

- ✅ `build.sh` - Render Build 腳本
- ✅ `scraper_playwright.py` - 已添加 Linux 相容參數
- ✅ `app.py` - 新增 `/api/get_cards` 路由
- ✅ `requirements.txt` - 依賴清單
- ✅ `MODIFICATION_SUMMARY.md` - 修改總結

---

## 🎓 關鍵概念解釋

### 為什麼需要 `--no-sandbox`?

在 Linux Docker 容器中，Chromium 無法正常使用沙箱機制，必須禁用以避免崩潰。
```bash
--no-sandbox       # 禁用 Chromium 沙箱
```

### 為什麼需要 `--disable-dev-shm-usage`?

Render 的 `/dev/shm` (共享內存) 容量有限。禁用此參數可避免內存不足導致 Chromium 崩潰。
```bash
--disable-dev-shm-usage  # 使用磁盤而非內存快取
```

### 為什麼後端需要 Proxy?

1. **CORS 問題**: 瀏覽器會阻止跨域請求
2. **IP 封鎖**: 第三方 API 可能因大量請求而封鎖 Render IP
3. **數據安全**: 後端可以驗證和過濾響應

---

修改日期: 2026-05-12
狀態: ✅ 完成
