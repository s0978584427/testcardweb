# Card Lens

Card Lens 是官方卡牌圖鑑與相機影像辨識系統，支援：

- 台灣繁中 Pokemon TCG
- 日本官方 Pokemon TCG
- 國際英文 Pokemon TCG API
- Yu-Gi-Oh! API
- OpenCV ORB 卡圖辨識與永久特徵快取

## 啟動

```powershell
.\.venv\Scripts\python.exe app.py
```

開啟 <http://127.0.0.1:5000/>。

## API

### 搜尋官方卡牌

```text
GET /api/cards/search?keyword=皮卡丘&source=tw-pokemon&page=1&limit=50
```

`source` 可使用 `all`、`tw-pokemon`、`pokemon-jp`、`pokemon` 或 `yugioh`。

### 相機辨識

```text
POST /api/identify
Content-Type: application/json

{"image": "data:image/jpeg;base64,..."}
```

## 資料

- `data/pokemon_tw.json`：繁中官方卡牌快取
- `data/pokemon_jp.json`：日版官方卡牌快取
- `data/features_cache.pkl`：ORB 特徵永久快取

卡牌欄位由 `card_schema.py` 統一，官方資料抓取與分頁由 `official_pokemon.py` 處理。
