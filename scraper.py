from __future__ import annotations

import json
import logging
import re
import time
from typing import Dict, List
from urllib.parse import quote

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Accept": "application/json,text/plain,*/*",
}

PCHOME_API = "https://ecshweb.pchome.com.tw/search/v3.3/all/results"

# 只保留比較像卡牌商品的關鍵字
CARD_INCLUDE_KEYWORDS = [
    "卡", "卡牌", "cards", "card", "ptcg", "pokemon card", "pokemon cards",
    "寶可夢卡", "寶可夢集換式卡牌", "遊戲王卡", "yugioh card", "yu-gi-oh card",
    "mtg", "magic card", "魔法風雲會", "牌組", "補充包", "擴充包", "集換式卡牌",
    "tcg", "trading card", "trainer box", "booster", "starter deck",
]

# 這些常見非卡牌詞直接排除
CARD_EXCLUDE_KEYWORDS = [
    "卡套", "卡盒", "卡磚", "卡冊", "卡夾", "卡片收納", "收納盒", "展示架",
    "保護套", "牌套", "桌墊", "mat", "滑鼠墊", "海報", "吊飾", "公仔", "模型",
    "玩偶", "衣服", "短袖", "外套", "書", "小說", "貼紙", "手機殼", "鑰匙圈",
]


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _looks_like_card_product(name: str, keyword: str) -> bool:
    name_norm = _normalize_text(name)
    keyword_norm = _normalize_text(keyword)

    # 商品名先排除明顯周邊
    if any(bad.lower() in name_norm for bad in CARD_EXCLUDE_KEYWORDS):
        return False

    # 使用者搜尋字本身若已經含卡牌意圖，放寬一點，但仍要求商品名像卡牌
    include_hit = any(good.lower() in name_norm for good in CARD_INCLUDE_KEYWORDS)

    # 常見「單卡編號 / 稀有度 / 卡種」模式
    pattern_hit = bool(re.search(r"\b(ex|gx|vmax|vstar|sr|sar|ur|ar|chr|csr)\b", name_norm))

    # 若關鍵字本身含卡牌意圖，且商品名至少含「卡」或卡牌關鍵字，就保留
    query_card_intent = any(good.lower() in keyword_norm for good in CARD_INCLUDE_KEYWORDS)
    if query_card_intent and (include_hit or "卡" in name_norm or pattern_hit):
        return True

    # 一般情況下，商品名稱必須明確像卡牌商品
    return include_hit or pattern_hit



def search_pchome_api(keyword: str, page: int = 1) -> List[Dict]:
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    page = max(1, int(page))
    offset = (page - 1) * 20
    params = {
        "q": keyword,
        "offset": offset,
        "limit": 20,
        "sort": "sale/dc",
    }

    try:
        session = _build_session()
        logger.info("查詢 PChome API: %s (頁 %s)", keyword, page)
        response = session.get(PCHOME_API, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error("PChome API 請求失敗: %s", e)
        return []
    except json.JSONDecodeError as e:
        logger.error("PChome API JSON 解析失敗: %s", e)
        return []

    prods = data.get("prods", [])
    if not isinstance(prods, list):
        return []

    results: List[Dict] = []
    for prod in prods:
        if not isinstance(prod, dict):
            continue

        product_id = str(prod.get("Id") or prod.get("id") or "").strip()
        name = str(prod.get("name") or "").strip()
        price_raw = prod.get("price", 0)
        pic_s = str(prod.get("picS") or "").strip()

        if not name:
            continue

        # 新增：只保留像卡牌的商品
        if not _looks_like_card_product(name, keyword):
            continue

        try:
            price = int(price_raw) if price_raw not in (None, "") else 0
        except (TypeError, ValueError):
            price = 0

        image_url = f"https://cs-a.ecimg.tw{pic_s}" if pic_s else ""
        product_url = f"https://24h.pchome.com.tw/prod/{product_id}" if product_id else (
            f"https://24h.pchome.com.tw/search/?q={quote(keyword)}"
        )

        results.append(
            {
                "product_id": f"pchome_{product_id}" if product_id else f"pchome_{len(results)}",
                "platform": "pchome",
                "name": name,
                "price": price,
                "image": image_url,
                "shop": "24h PChome",
                "rating": 4.5,
                "url": product_url,
                "description": name,
            }
        )

    logger.info("PChome 第 %s 頁: 卡牌過濾後取得 %s 個商品", page, len(results))
    return results



def search_pchome(keyword: str, pages: int = 1) -> List[Dict]:
    results: List[Dict] = []
    pages = max(1, int(pages))

    for page_num in range(1, pages + 1):
        page_results = search_pchome_api(keyword, page=page_num)
        if not page_results:
            break
        results.extend(page_results)
        time.sleep(0.2)

    logger.info("PChome 共取得 %s 個卡牌商品", len(results))
    return results



def search_shopee(keyword: str, pages: int = 1) -> List[Dict]:
    logger.info("Shopee 搜尋目前未啟用: %s", keyword)
    return []



def search_ruten(keyword: str, pages: int = 1) -> List[Dict]:
    logger.info("Ruten 搜尋目前未啟用: %s", keyword)
    return []



def search_yahoo(keyword: str, pages: int = 1) -> List[Dict]:
    logger.info("Yahoo 搜尋目前未啟用: %s", keyword)
    return []



def search_cards_multi_platform(keyword: str) -> Dict[str, List[Dict]]:
    return {
        "shopee": search_shopee(keyword, pages=1),
        "ruten": search_ruten(keyword, pages=1),
        "yahoo": search_yahoo(keyword, pages=1),
        "pchome": search_pchome(keyword, pages=1),
    }



def get_sample_search_results(platform: str) -> List[Dict]:
    return [
        {
            "product_id": f"sample_{platform}_0",
            "platform": platform,
            "name": "青眼白龍卡牌",
            "price": 500,
            "image": "https://images.ygoprodeck.com/images/cards/89631139.jpg",
            "shop": f"{platform.upper()} 示例",
            "rating": 4.5,
            "url": "#",
            "description": "青眼白龍卡牌",
        }
    ]



def scrape_cards() -> List[Dict]:
    return search_pchome("遊戲卡 寶可夢卡", pages=1)



def test_pchome_api() -> None:
    logger.info("=" * 60)
    logger.info("PChome API 測試")
    logger.info("=" * 60)
    for keyword in ["ptcg", "寶可夢卡", "青眼白龍卡"]:
        products = search_pchome_api(keyword, page=1)
        logger.info("關鍵字 %s -> %s 筆", keyword, len(products))
        for prod in products[:3]:
            logger.info("%s | %s | %s", prod["name"], prod["price"], prod["image"])


if __name__ == "__main__":
    test_pchome_api()
