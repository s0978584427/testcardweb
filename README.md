# 卡牌價格監控系統 - 使用指南

## 📋 項目說明

一個完整的卡牌價格監控系統，包括：
- **後端**：Flask Web 框架，提供 RESTful API
- **資料庫**：SQLite，存儲卡牌信息和價格歷史
- **爬蟲**：BeautifulSoup 和 Requests，自動抓取卡牌數據
- **前端**：Bootstrap 5 深色模式 + Chart.js 價格圖表

## 🚀 快速開始

### 1. 環境準備

```bash
# 進入項目目錄
cd testcardweb

# 創建虛擬環境（推薦使用 Python 3.8+）
python -m venv venv

# 激活虛擬環境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 運行應用

```bash
python app.py
```

應用將在 `http://localhost:5000` 上運行

### 4. 首次運行

- 首次運行時，應用會自動創建 SQLite 資料庫
- 系統會自動載入示例卡牌數據（因為目標網站為資訊型網站）
- 點擊「更新卡牌」按鈕可手動觸發爬蟲抓取最新數據

## 📁 文件結構

```
testcardweb/
├── app.py                 # Flask 主應用程式
├── models.py              # 資料庫模型定義
├── scraper.py             # 網頁爬蟲邏輯
├── requirements.txt       # Python 依賴項
├── cards.db               # SQLite 資料庫（自動生成）
├── README.md              # 本文件
└── templates/
    └── index.html         # 前端 HTML 頁面
```

## 🎯 主要功能

### 前端功能
- ✅ 深色模式界面，支持中文顯示
- ✅ 響應式網格布局，展示所有卡牌信息
- ✅ 實時價格顯示和卡牌圖片預覽
- ✅ 點擊卡牌查看價格歷史折線圖
- ✅ 統計信息面板（卡牌總數、價格記錄、平均價格）
- ✅ 一鍵更新按鈕，觸發爬蟲更新資料

### API 端點

| 路由 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 首頁 - HTML 前端 |
| `/api/cards` | GET | 獲取所有卡牌 |
| `/api/cards/<id>` | GET | 獲取單個卡牌詳情 |
| `/api/cards/<id>/price-history` | GET | 獲取卡牌價格歷史 |
| `/api/stats` | GET | 獲取統計信息 |
| `/update` | POST/GET | 觸發爬蟲更新 |

## 🔧 自定義爬蟲

如果要爬取不同網站的卡牌數據，修改 `scraper.py` 中的選擇器：

```python
# 在 _extract_card_info() 方法中修改 CSS 選擇器
name_elem = container.find('h3', class_='your-card-name-class')
price_elem = container.find('span', class_='your-price-class')
img_elem = container.find('img', class_='your-image-class')
```

## 📊 數據庫結構

### Cards 表
```
- id (主鍵)
- name (卡牌名稱，唯一)
- description (描述)
- image_url (圖片鏈接)
- current_price (當前價格)
- last_updated (最後更新時間)
- created_at (創建時間)
```

### Price_History 表
```
- id (主鍵)
- card_id (外鍵，關聯 Cards)
- price (價格)
- recorded_at (記錄時間)
```

## 🌐 生產環境部署

使用 Gunicorn 運行：

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📝 日誌

應用運行時會輸出日誌到控制台，包括：
- 請求信息
- 爬蟲進度
- 資料庫操作
- 錯誤信息

## 🐛 常見問題

### Q: 運行時出現「ModuleNotFoundError」
**A:** 確保已激活虛擬環境並安裝所有依賴：
```bash
pip install -r requirements.txt
```

### Q: 資料庫被鎖定
**A:** 刪除 `cards.db` 文件，重新運行即可自動創建

### Q: 爬蟲無法獲取數據
**A:** 某些網站使用 JavaScript 動態加載內容。可考慮使用 Selenium 替代 BeautifulSoup

### Q: 圖片無法顯示
**A:** 檢查 URL 是否正確，或使用佔位圖服務如 `https://via.placeholder.com/`

## 🔐 安全建議

生產環境時：
1. 設置 `app.run(debug=False)`
2. 配置適當的 CORS 政策
3. 使用環境變量存儲敏感信息
4. 定期備份資料庫

## 📞 支持

如有問題或建議，請檢查日誌輸出或查看代碼注釋。

---

**版本**: 1.0.0  
**最後更新**: 2024 年 4 月
