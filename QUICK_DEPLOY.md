# ⚡ 快速部署指南

## 🚀 一鍵部署命令

### 本地驗證 (部署前必做)

```bash
# 1. 進入項目目錄
cd c:\Users\s0978\Downloads\testcardweb

# 2. 激活虛擬環境
.\.venv\Scripts\Activate.ps1

# 3. 啟動應用
python app.py

# 4. 在另一個 PowerShell 窗口運行測試
python test_proxy_routes.py

# 5. 預期看到: ✅ 所有測試通過！
```

### 推送到 GitHub

```bash
# 1. 添加所有文件
git add .

# 2. 提交代碼
git commit -m "🔧 Render 最終修復：Playwright Linux + 後端 Proxy + 完整測試"

# 3. 推送到 GitHub
git push origin master
```

### Render 部署

1. **登入 Render Dashboard**: https://dashboard.render.com
2. **選擇你的 Web Service**
3. **進入 Settings**:
   - **Build Command**: `chmod +x build.sh && ./build.sh`
   - **Start Command**: `python app.py`
   - **Environment**: `PYTHONUNBUFFERED=1` 和 `FLASK_ENV=production`
4. **點擊 "Redeploy"** 按鈕
5. **等待 3-5 分鐘** 部署完成

### Render 部署監控

```bash
# 在 Render Dashboard 查看:
# Logs → Build    (應看到: ✅ Build completed successfully!)
# Logs → Runtime  (應看到: * Running on http://0.0.0.0:5000)
```

---

## ✅ 驗證清單

### 本地驗證 (5 分鐘)

- [ ] `test_proxy_routes.py` 4/4 測試通過
- [ ] Pokemon API 響應正常
- [ ] YuGiOh API 響應正常
- [ ] MTG API 響應正常
- [ ] 錯誤處理驗證成功

### 代碼檢查 (1 分鐘)

```bash
# 檢查所有修改都已完成
grep -c "no-sandbox" scraper_playwright.py            # 應輸出: 2
grep -c "def get_cards_proxy" app.py                  # 應輸出: 1
test -f build.sh && echo "✅ build.sh 存在"
test -f test_proxy_routes.py && echo "✅ test_proxy_routes.py 存在"
```

### Render 驗證 (3 分鐘，部署後)

```bash
# 使用 curl 測試
curl "https://your-render-app.onrender.com/api/get_cards?source=pokemon&keyword=pikachu&limit=1"

# 預期: JSON 響應，status="success"
```

---

## 📋 必要修改確認

### ✅ scraper_playwright.py
- [x] 第 ~15 行：添加 `--no-sandbox` 參數
- [x] 第 ~16 行：添加 `--disable-dev-shm-usage` 參數
- [x] 第 ~130 行：同樣修改 scrape_shopee_playwright()

### ✅ app.py
- [x] 第 ~169 行：新增 `/api/get_cards` 路由
- [x] 包含 Pokemon、YuGiOh、MTG API 邏輯
- [x] 詳細的錯誤返回

### ✅ build.sh
- [x] 包含 `playwright install chromium`

### ✅ templates/index.html
- [x] 增強 Console 調試日誌

---

## 🆘 常見錯誤快速解決

### 錯誤 1: Build 失敗

```
ERROR: chmod: command not found
```

**原因**: Render 環境不支持 chmod  
**解決**: 改用 `./build.sh` 作為 Build Command（Render 會自動識別）

### 錯誤 2: Playwright 安裝失敗

```
ERROR: playwright install chromium failed
```

**解決**:
1. 檢查 build.sh 是否存在
2. 檢查 requirements.txt 是否包含 playwright
3. Render Dashboard 手動重新啟動 Build

### 錯誤 3: API 返回 500

```json
{
  "error": "搜尋失敗",
  "details": "... 錯誤信息 ..."
}
```

**排查**:
1. 查看 Render Runtime 日誌
2. 確認網路連接
3. 檢查第三方 API 是否在線

### 錯誤 4: 前端搜尋無反應

**排查**:
1. 按 F12 打開 Console
2. 搜尋卡牌
3. 查看 Network 標籤中的 API 請求
4. 查看錯誤信息

---

## 📚 文檔速查

| 文檔 | 用途 | 讀法 |
|------|------|------|
| `COMPLETION_REPORT.md` | 📋 完成報告 | 了解修復概況 |
| `RENDER_FINAL_FIX.md` | 🔧 修復指南 | 深入理解技術細節 |
| `RENDER_VERIFICATION_CHECKLIST.md` | ✅ 驗證清單 | 逐步驗證每個修復 |
| `test_proxy_routes.py` | 🧪 測試腳本 | 自動化測試 API |
| `MODIFICATION_SUMMARY.md` | 📝 修改總結 | 三步修復概要 |

---

## 🎯 成功標誌

### 部署後能看到的現象

```
✅ 應用能正常啟動
✅ 首頁正常加載
✅ 搜尋功能可用
✅ 卡牌詳情正確顯示
✅ 錯誤信息清晰
✅ Console 日誌詳細
```

### 預期性能

| 指標 | 目標 | 備註 |
|------|------|------|
| 首頁加載 | < 2s | 包括 CSS、JS、圖片 |
| API 響應 | < 10s | 第三方 API 可能較慢 |
| 搜尋結果 | 20 個/次 | 可修改 limit 參數 |
| 錯誤處理 | 100% | 所有失敗都有詳細信息 |

---

## 💡 使用技巧

### 測試特定 API

```javascript
// 只測試 Pokemon
fetch('/api/get_cards?source=pokemon&keyword=pikachu&limit=5')
  .then(r => r.json())
  .then(d => console.table(d.results))

// 只測試 YuGiOh
fetch('/api/get_cards?source=yugioh&keyword=blue+eyes&limit=5')
  .then(r => r.json())
  .then(d => console.table(d.results))

// 只測試 MTG
fetch('/api/get_cards?source=mtg&keyword=black+lotus&limit=5')
  .then(r => r.json())
  .then(d => console.table(d.results))
```

### 調整搜尋數量

```javascript
// 獲取 50 個結果（最多）
fetch('/api/get_cards?source=pokemon&keyword=pikachu&limit=50')
```

### 完整的錯誤檢查

```javascript
fetch('/api/get_cards?source=pokemon&keyword=pikachu')
  .then(r => {
    console.log(`Status: ${r.status}`);
    console.log(`Headers:`, r.headers);
    return r.json();
  })
  .then(d => {
    console.log(`Response:`, d);
    if (d.status === 'success') {
      console.log(`✅ 獲取 ${d.total} 張卡牌`);
    } else {
      console.error(`❌ 錯誤: ${d.error}`);
      console.error(`詳情: ${d.details}`);
    }
  })
  .catch(e => console.error(`Network Error: ${e}`))
```

---

## 📞 支援資源

- **Render 文檔**: https://render.com/docs
- **Flask 文檔**: https://flask.palletsprojects.com
- **Playwright 文檔**: https://playwright.dev/python
- **本項目文檔**: 所有 .md 文件在項目根目錄

---

## 🔄 部署更新流程

每次修改後的更新步驟：

```bash
# 1. 本地修改和測試
python app.py
python test_proxy_routes.py

# 2. 推送到 GitHub
git add .
git commit -m "描述你的修改"
git push origin master

# 3. Render 自動重新部署
# (大約 1-2 分鐘)

# 4. 驗證部署結果
curl https://your-app.onrender.com/
```

---

**最後檢查時間**: 2026-05-12  
**狀態**: ✅ 準備就緒  
**預計部署時間**: 5-10 分鐘  
**預計上線時間**: 部署後 3-5 分鐘
