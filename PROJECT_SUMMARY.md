<!-- 項目初始化完成提示 -->

# 🎉 卡牌價格監控系統 - 項目已完成

## ✅ 已創建的文件列表

### 核心程序文件
```
✅ app.py                 - Flask Web 應用主程式 (257 行)
✅ models.py              - SQLAlchemy 資料庫模型 (88 行)
✅ scraper.py             - 網頁爬蟲模組 (240 行)
✅ requirements.txt       - Python 依賴項清單 (14 行)
```

### 前端文件
```
✅ templates/index.html   - Bootstrap 5 前端頁面 (450+ 行)
   - 深色模式設計
   - 響應式卡牌網格布局
   - Chart.js 價格圖表
   - 實時統計面板
```

### 輔助文件
```
✅ README.md              - 詳細使用指南
✅ test_system.py         - 完整性測試腳本
✅ run.bat                - Windows 快速啟動腳本
✅ run.sh                 - Linux/Mac 快速啟動腳本
✅ .env.example           - 環境變量示例
```

## 🚀 快速啟動指南

### 方法 1: 使用快速啟動腳本（推薦）

**Windows:**
```bash
run.bat
```

**Linux/Mac:**
```bash
chmod +x run.sh
./run.sh
```

### 方法 2: 手動啟動

```bash
# 1. 創建虛擬環境
python -m venv venv

# 2. 激活虛擬環境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 運行應用
python app.py
```

### 方法 3: 進行完整性測試

```bash
# 激活虛擬環境後
python test_system.py
```

## 📊 系統架構圖

```
┌─────────────────────────────────────────────────────┐
│              前端 (Bootstrap 5 + Chart.js)            │
│  ┌─────────────────────────────────────────────────┐ │
│  │  卡牌網格  │  統計面板  │  更新按鈕  │  圖表模態窗  │ │
│  └─────────────────────────────────────────────────┘ │
└────────────────┬────────────────────────────────────┘
                 │ (REST API)
┌────────────────▼────────────────────────────────────┐
│              後端 (Flask)                             │
│  ┌──────────────────────────────────────────────────┐│
│  │ GET /api/cards           - 獲取所有卡牌          ││
│  │ GET /api/cards/<id>      - 獲取單個卡牌          ││
│  │ GET /api/cards/<id>/... - 獲取價格歷史           ││
│  │ GET /api/stats           - 獲取統計信息          ││
│  │ POST /update             - 觸發爬蟲更新          ││
│  └──────────────────────────────────────────────────┘│
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼──────────┐  ┌──▼──────────────────┐
│  爬蟲 (Scraper)  │  │  資料庫 (SQLite)    │
│                  │  │                     │
│ BeautifulSoup4   │  │ Cards 表 (卡牌)     │
│ + Requests       │  │ Price_History (價格)│
└──────────┬───────┘  └──────────────────┬──┘
           │                             │
           └─────────────┬───────────────┘
                         │
                    目標網站
        https://www.catfootprint.com/
```

## 💾 資料庫設計

### Cards 表 (卡牌表)
| 欄位 | 型態 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| name | VARCHAR(255) | 卡牌名稱（唯一） |
| description | TEXT | 卡牌描述 |
| image_url | VARCHAR(500) | 卡牌圖片 URL |
| current_price | FLOAT | 當前價格 |
| last_updated | DATETIME | 最後更新時間 |
| created_at | DATETIME | 創建時間 |

### Price_History 表 (價格歷史表)
| 欄位 | 型態 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| card_id | INTEGER | 卡牌 ID（外鍵） |
| price | FLOAT | 價格 |
| recorded_at | DATETIME | 記錄時間 |

## 🎯 主要功能

### 已實現的功能
- ✅ **自動爬蟲** - 定期抓取卡牌價格和信息
- ✅ **價格追蹤** - 完整的價格歷史記錄
- ✅ **互動圖表** - Chart.js 展示價格趨勢
- ✅ **RESTful API** - 完整的後端 API
- ✅ **深色模式界面** - Bootstrap 5 現代化設計
- ✅ **響應式設計** - 支持各種屏幕尺寸
- ✅ **實時統計** - 卡牌數、歷史記錄、平均價格
- ✅ **中文支持** - 完整的繁體中文界面

### 可擴展方向
- 🔄 配置爬蟲選擇器支持多個網站
- 📧 新增郵件通知功能（價格變動提醒）
- 📱 開發移動應用程序
- 🔐 添加用戶認證系統
- 🌐 部署到雲平台（Heroku, AWS, 阿里雲等）

## 📈 數據流程

```
1. 用戶訪問 http://localhost:5000
   ↓
2. Flask 加載 index.html 前端頁面
   ↓
3. 前端 JavaScript 發送 AJAX 請求到 /api/endpoints
   ↓
4. 後端 API 從資料庫查詢數據並響應 JSON
   ↓
5. 前端使用 Chart.js 和 Bootstrap 渲染界面
   ↓
6. 用戶點擊「更新卡牌」按鈕
   ↓
7. 觸發 /update 端點
   ↓
8. 爬蟲執行爬取最新數據
   ↓
9. 資料庫更新（新增卡牌、價格歷史）
   ↓
10. 前端自動刷新展示最新數據
```

## 🔌 API 文檔

### GET /api/cards
獲取所有卡牌
```json
{
  "response": [
    {
      "id": 1,
      "name": "藍眼白龍",
      "description": "傳說中的強力卡牌",
      "image_url": "https://...",
      "current_price": 1500,
      "last_updated": "2024-01-15T10:30:00",
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

### GET /api/stats
獲取統計信息
```json
{
  "total_cards": 5,
  "price_history_count": 25,
  "average_price": 1000.0
}
```

### GET /api/cards/{id}/price-history?days=30
獲取卡牌價格歷史
```json
{
  "card_id": 1,
  "card_name": "藍眼白龍",
  "history": [
    {
      "date": "2024-01-15 10:30",
      "price": 1500
    }
  ]
}
```

## 🐛 運行時提示

### 首次運行
- 應用會自動創建 `cards.db` SQLite 資料庫
- 資料庫會自動創建所需的表
- 初始爬蟲會加載示例卡牌數據

### 運行環境
- **Python 版本：** 3.8+
- **默認地址：** http://localhost:5000
- **調試模式：** 已啟用（自動重載）

### 常見命令
```bash
# 進入項目目錄
cd c:\Users\s0978\Downloads\testcardweb

# 查看日誌
# 在控制台中查看實時運行日誌

# 停止服務
# 在終端按 Ctrl+C

# 重置資料庫
# 刪除 cards.db 文件，重新運行即可自動創建
```

## 🔒 安全性說明

### 開發環境（已配置）
- Debug 模式已啟用
- CORS 已啟用（允許所有源）
- 本地數據庫存儲

### 生產環境建議
```python
# 修改 app.py
app.run(debug=False, host='127.0.0.1', port=5000)

# 使用 Gunicorn 運行
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📞 技術支援

如遇問題，請按以下步驟排查：

1. **檢查 Python 版本**
   ```bash
   python --version
   ```

2. **驗證依賴安裝**
   ```bash
   pip list | grep Flask
   ```

3. **查看應用日誌**
   - 所有錯誤信息會顯示在終端

4. **重置資料庫**
   ```bash
   del cards.db  # 或 rm cards.db
   python app.py
   ```

## 📋 項目清單

- [x] 後端 Flask 應用框架
- [x] SQLite 資料庫設計和初始化
- [x] 網頁爬蟲模組（BeautifulSoup + Requests）
- [x] RESTful API 端點設計
- [x] 前端 HTML + CSS + JavaScript
- [x] Bootstrap 5 深色模式
- [x] Chart.js 價格圖表
- [x] 響應式設計
- [x] 錯誤處理和日誌
- [x] 完整性測試工具
- [x] 快速啟動腳本
- [x] 詳細文檔

## 🎓 學習資源

本項目展示了以下技術：
- Flask Web 框架和路由
- SQLAlchemy ORM 和資料庫設計
- BeautifulSoup 和 Requests 網頁爬蟲
- RESTful API 設計
- Bootstrap CSS 框架
- Chart.js 數據可視化
- JavaScript 非同步編程（AJAX）
- SQLite 資料庫

## 📝 更新日誌

- **v1.0.0** - 初始版本
  - 完整項目框架
  - 爬蟲和 API 實現
  - 前端界面設計

---

**開發環境完全配置！** 🚀

立即開始使用：
```bash
cd c:\Users\s0978\Downloads\testcardweb
python app.py
```

然後訪問：**http://localhost:5000**

祝您使用愉快！😊
