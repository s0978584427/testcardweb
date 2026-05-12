# Render 部署配置指南

## 部署步驟

### 1️⃣ 設置 Build Command 和 Start Command

在 Render Dashboard 中，進入你的 Web Service 設置：

**Settings → Build Command:**
```bash
chmod +x build.sh && ./build.sh
```

**Settings → Start Command:**
```bash
python app.py
```
或者使用 gunicorn（推薦用於生產環境）：
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

### 2️⃣ 關鍵配置項

#### Environment Variables
在 Render Dashboard 設置以下環境變數：
- `FLASK_ENV`: `production`
- `PYTHONUNBUFFERED`: `1`（確保 Python 日誌實時輸出）

---

### 3️⃣ 修復清單

✅ **build.sh** - 已建立
- 自動安裝 Python 依賴
- 安裝 Playwright Chromium 瀏覽器（解決爬蟲崩潰問題）

✅ **app.py** - 已修改
- 增強 `/api/cards/search` 錯誤返回（包含詳細錯誤信息）
- 所有國際 API 請求都通過後端 proxy 轉發

✅ **templates/index.html** - 已修改
- 增強 console.error 日誌輸出
- 詳細的 HTTP 錯誤診斷（404、500、503 等）
- 網路錯誤詳細信息（CORS、連接問題等）

---

### 4️⃣ 故障排查

**當部署失敗時，檢查以下幾點：**

1. **查看 Build 日誌**
   - Render Dashboard → Logs → Build
   - 確認 `playwright install chromium` 是否成功執行

2. **查看運行時日誌**
   - Render Dashboard → Logs → Runtime
   - 使用 `PYTHONUNBUFFERED=1` 確保實時輸出日誌

3. **瀏覽器 Console 診斷**
   - 開啟瀏覽器開發者工具 → Console
   - 搜尋關鍵字，查看詳細的 API 錯誤日誌
   - 查看 Network 標籤檢查 HTTP 請求和響應

4. **常見錯誤及解決方案**
   - **404 錯誤**: API 端點不存在，檢查後端路由
   - **500 錯誤**: 服務器異常，查看 Runtime 日誌中的 `details` 字段
   - **503 錯誤**: 第三方 API 超時，可能需要增加超時時間或重試機制
   - **CORS 錯誤**: 檢查 Flask-CORS 是否正確配置

---

### 5️⃣ 部署後驗證

部署完成後，執行以下測試：

```bash
# 本地測試（部署前）
curl "https://your-render-domain.onrender.com/api/cards/search?keyword=pikachu&source=pokemon&limit=1"

# 瀏覽器中
# 1. 開啟 F12 Developer Tools
# 2. 搜尋 "pikachu"
# 3. 查看 Console 輸出詳細日誌
# 4. 查看 Network 標籤中的 API 響應
```

---

## 文件說明

| 文件 | 用途 |
|------|------|
| `build.sh` | Render Build 腳本，安裝依賴和瀏覽器 |
| `requirements.txt` | Python 依賴項 |
| `app.py` | 後端 Flask 應用（已修改以增強錯誤信息） |
| `templates/index.html` | 前端 HTML（已修改以增強 Console 日誌） |
| `card_apis.py` | 卡牌 API 整合（使用 safe_request 確保 HTTPS） |

---

## 效能優化建議

1. **增加 Render 計畫等級** - 免費計畫可能會因資源限制而超時
2. **設置 API 超時** - 在 `card_apis.py` 中調整 `safe_request()` 的 timeout 參數
3. **實現快取機制** - 為頻繁搜尋的結果添加 Redis 快取
4. **背景任務** - 使用 APScheduler 預加載熱門卡牌數據

---

## 相關文檔

- [Render 官方文檔](https://render.com/docs)
- [Flask 部署指南](https://flask.palletsprojects.com/deployment/)
- [Playwright 文檔](https://playwright.dev/python/)
