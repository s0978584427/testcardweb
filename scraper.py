"""
卡牌價格監控系統 - 爬蟲模組（精准版）
使用 PChome 官方 API 和真實電商平台數據
"""
import requests
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import quote
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局會話設置
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

# ============================================================================
# PChome 真實 API 爬蟲 (官方搜尋 API - JSON 格式)
# ============================================================================

def search_pchome_api(keyword: str, page: int = 1) -> List[Dict]:
    """
    使用 PChome 官方搜尋 API 獲取準確的商品數據
    
    API 文檔: https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={keyword}
    返回 JSON 格式的商品列表
    """
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        # PChome 官方搜尋 API
        offset = (page - 1) * 20
        url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={quote(keyword)}&offset={offset}&limit=20"
        
        logger.info(f"查詢 PChome API: {keyword} (頁 {page})")
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"PChome API 返回狀態碼: {response.status_code}")
            return []
        
        data = response.json()
        products = []
        
        # 提取商品數組 (prods 是官方返回的字段名)
        prods = data.get('prods', [])
        
        if not prods:
            logger.info(f"PChome 第 {page} 頁: 無商品")
            return []
        
        for prod in prods:
            try:
                # 提取必要字段 (注意: API 使用大寫 Id)
                product_id = prod.get('Id', '')
                name = prod.get('name', '')
                price = prod.get('price', 0)
                pic_s = prod.get('picS', '')  # 圖片後綴
                
                # 驗證必要字段
                if not name or not product_id:
                    logger.debug(f"跳過: 缺少基本信息")
                    continue
                
                # 拼接完整圖片 URL
                image_url = ''
                if pic_s:
                    image_url = f'https://cs-a.ecimg.tw{pic_s}'
                
                # 確保 price 是整數
                try:
                    price = int(price) if price else 0
                except (ValueError, TypeError):
                    price = 0
                
                product = {
                    'product_id': f'pchome_{product_id}',
                    'platform': 'pchome',
                    'name': name,
                    'price': price,  # 整數價格
                    'image': image_url,  # 完整圖片 URL
                    'shop': '24h PChome',
                    'rating': 4.5,  # API 沒有評分字段
                    'url': f'https://24h.pchome.com.tw/prod/{product_id}',
                    'description': name
                }
                
                products.append(product)
                logger.debug(f"✓ 商品: {name[:40]} | 價格: {price}元 | 圖片: {image_url[:60]}...")
                
            except Exception as e:
                logger.debug(f"解析商品失敗: {e}")
                continue
        
        logger.info(f"PChome 第 {page} 頁: 成功獲取 {len(products)} 個商品")
        return products
    
    except requests.RequestException as e:
        logger.error(f"PChome API 請求失敗: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"PChome API JSON 解析失敗: {e}")
        return []
    except Exception as e:
        logger.error(f"PChome 搜索錯誤: {e}")
        return []


def test_pchome_api():
    """
    測試函數：列印前三筆真實數據到終端機
    用來驗證數據是否準確
    """
    logger.info("=" * 70)
    logger.info("PChome API 數據測試")
    logger.info("=" * 70)
    
    test_keywords = ['遊戲卡', '寶可夢卡', '青眼白龍']
    
    for keyword in test_keywords:
        logger.info(f"\n搜尋: {keyword}")
        logger.info("-" * 70)
        
        products = search_pchome_api(keyword, page=1)
        
        if not products:
            logger.warning(f"未獲取到 {keyword} 的商品")
            continue
        
        # 列印前三筆
        for i, prod in enumerate(products[:3], 1):
            logger.info(f"\n【第 {i} 筆】")
            logger.info(f"  商品名稱: {prod['name']}")
            logger.info(f"  價格: {prod['price']} 元")
            logger.info(f"  圖片 URL: {prod['image']}")
            logger.info(f"  商品 ID: {prod['product_id']}")
            logger.info(f"  商品連結: {prod['url']}")
        
        time.sleep(0.5)  # 避免過度請求
    
    logger.info("\n" + "=" * 70)
    logger.info("測試完成")
    logger.info("=" * 70)


# ============================================================================
# 搜索函數 (多平台支持)
# ============================================================================

def search_pchome(keyword: str, pages: int = 3) -> List[Dict]:
    """
    搜索 PChome 商品 - 使用官方 API
    """
    results = []
    
    for page_num in range(1, pages + 1):
        try:
            page_results = search_pchome_api(keyword, page=page_num)
            if page_results:
                results.extend(page_results)
            else:
                # 無商品表示已到盡頭
                break
            
            time.sleep(0.3)  # 避免過度請求
        except Exception as e:
            logger.warning(f"第 {page_num} 頁失敗: {e}")
            break
    
    logger.info(f"PChome 共取得 {len(results)} 個商品")
    return results


def search_shopee(keyword: str, pages: int = 1) -> List[Dict]:
    """蝦皮搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"蝦皮搜索: {keyword} (待實現)")
    return []


def search_ruten(keyword: str, pages: int = 1) -> List[Dict]:
    """露天搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"露天搜索: {keyword} (待實現)")
    return []


def search_yahoo(keyword: str, pages: int = 1) -> List[Dict]:
    """Yahoo搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"Yahoo搜索: {keyword} (待實現)")
    return []


def search_cards_multi_platform(keyword: str) -> Dict[str, List[Dict]]:
    """
    在多個平台搜索卡牌
    返回格式: {'shopee': [...], 'ruten': [...], 'yahoo': [...], 'pchome': [...]}
    """
    results = {
        'shopee': [],
        'ruten': [],
        'yahoo': [],
        'pchome': search_pchome(keyword, pages=2)  # 獲取前 40 個商品
    }
    
    return results


# ============================================================================
# 示例卡牌列表 (備用)
# ============================================================================

def get_sample_search_results(platform: str) -> List[Dict]:
    """
    獲取示例卡牌列表 (備用)
    包含遊戲王和寶可夢卡牌的官方圖片
    """
    # 遊戲王卡牌
    yugioh_cards = [
        ('青眼白龍', 'https://images.ygoprodeck.com/images/cards/89631139.jpg'),
        ('黑魔法師', 'https://images.ygoprodeck.com/images/cards/16732705.jpg'),
        ('藍眼白龍', 'https://images.ygoprodeck.com/images/cards/70095154.jpg'),
        ('青眼白龍 終極龍', 'https://images.ygoprodeck.com/images/cards/70630755.jpg'),
    ]
    
    # 寶可夢卡牌
    pokemon_cards = [
        ('皮卡丘', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png'),
        ('妙蛙種子', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png'),
        ('小火龍', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png'),
        ('傑尼龜', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png'),
    ]
    
    base_cards = yugioh_cards + pokemon_cards
    
    platform_data = {
        'shopee': [
            {
                'product_id': f'sample_shopee_{i}',
                'name': f'{card[0]} - 示例',
                'price': 500 + (i * 50),
                'platform': 'shopee',
                'url': f'https://shopee.tw/search?keyword={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.5
            }
            for i, card in enumerate(base_cards)
        ],
        'ruten': [
            {
                'product_id': f'sample_ruten_{i}',
                'name': f'{card[0]} - 示例',
                'price': 450 + (i * 45),
                'platform': 'ruten',
                'url': f'https://www.ruten.com.tw/find/?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.3
            }
            for i, card in enumerate(base_cards)
        ],
        'yahoo': [
            {
                'product_id': f'sample_yahoo_{i}',
                'name': f'{card[0]} - 示例',
                'price': 600 + (i * 55),
                'platform': 'yahoo',
                'url': f'https://tw.bid.yahoo.com/search?p={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.6
            }
            for i, card in enumerate(base_cards)
        ],
        'pchome': [
            {
                'product_id': f'sample_pchome_{i}',
                'name': f'{card[0]} - 示例',
                'price': 550 + (i * 52),
                'platform': 'pchome',
                'url': f'https://24h.pchome.com.tw/search?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.4
            }
            for i, card in enumerate(base_cards)
        ]
    }
    
    return platform_data.get(platform, [])


# ============================================================================
# 主要爬蟲函數 (相容舊版 API)
# ============================================================================

def scrape_cards() -> List[Dict]:
    """爬取卡牌數據"""
    return search_pchome('遊戲卡 寶可夢卡', pages=2)


if __name__ == '__main__':
    # 運行測試
    test_pchome_api()
"""
卡牌價格監控系統 - 爬蟲模組（精准版）
使用 PChome 官方 API 和真實電商平台數據
"""
import requests
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import quote
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局會話設置
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

# ============================================================================
# PChome 真實 API 爬蟲 (官方搜尋 API - JSON 格式)
# ============================================================================

def search_pchome_api(keyword: str, page: int = 1) -> List[Dict]:
    """
    使用 PChome 官方搜尋 API 獲取準確的商品數據
    
    API 文檔: https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={keyword}
    返回 JSON 格式的商品列表
    """
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        # PChome 官方搜尋 API
        offset = (page - 1) * 20
        url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={quote(keyword)}&offset={offset}&limit=20"
        
        logger.info(f"查詢 PChome API: {keyword} (頁 {page})")
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"PChome API 返回狀態碼: {response.status_code}")
            return []
        
        data = response.json()
        products = []
        
        # 提取商品數組 (prods 是官方返回的字段名)
        prods = data.get('prods', [])
        
        if not prods:
            logger.info(f"PChome 第 {page} 頁: 無商品")
            return []
        
        for prod in prods:
            try:
                # 提取必要字段 (注意: API 使用大寫 Id)
                product_id = prod.get('Id', '')
                name = prod.get('name', '')
                price = prod.get('price', 0)
                pic_s = prod.get('picS', '')  # 圖片後綴
                
                # 驗證必要字段
                if not name or not product_id:
                    logger.debug(f"跳過: 缺少基本信息")
                    continue
                
                # 拼接完整圖片 URL
                image_url = ''
                if pic_s:
                    image_url = f'https://cs-a.ecimg.tw{pic_s}'
                
                # 確保 price 是整數
                try:
                    price = int(price) if price else 0
                except (ValueError, TypeError):
                    price = 0
                
                product = {
                    'product_id': f'pchome_{product_id}',
                    'platform': 'pchome',
                    'name': name,
                    'price': price,  # 整數價格
                    'image': image_url,  # 完整圖片 URL
                    'shop': '24h PChome',
                    'rating': 4.5,  # API 沒有評分字段
                    'url': f'https://24h.pchome.com.tw/prod/{product_id}',
                    'description': name
                }
                
                products.append(product)
                logger.debug(f"✓ 商品: {name[:40]} | 價格: {price}元 | 圖片: {image_url[:60]}...")
                
            except Exception as e:
                logger.debug(f"解析商品失敗: {e}")
                continue
        
        logger.info(f"PChome 第 {page} 頁: 成功獲取 {len(products)} 個商品")
        return products
    
    except requests.RequestException as e:
        logger.error(f"PChome API 請求失敗: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"PChome API JSON 解析失敗: {e}")
        return []
    except Exception as e:
        logger.error(f"PChome 搜索錯誤: {e}")
        return []


def test_pchome_api():
    """
    測試函數：列印前三筆真實數據到終端機
    用來驗證數據是否準確
    """
    logger.info("=" * 70)
    logger.info("PChome API 數據測試")
    logger.info("=" * 70)
    
    test_keywords = ['遊戲卡', '寶可夢卡', '青眼白龍']
    
    for keyword in test_keywords:
        logger.info(f"\n搜尋: {keyword}")
        logger.info("-" * 70)
        
        products = search_pchome_api(keyword, page=1)
        
        if not products:
            logger.warning(f"未獲取到 {keyword} 的商品")
            continue
        
        # 列印前三筆
        for i, prod in enumerate(products[:3], 1):
            logger.info(f"\n【第 {i} 筆】")
            logger.info(f"  商品名稱: {prod['name']}")
            logger.info(f"  價格: {prod['price']} 元")
            logger.info(f"  圖片 URL: {prod['image']}")
            logger.info(f"  商品 ID: {prod['product_id']}")
            logger.info(f"  商品連結: {prod['url']}")
        
        time.sleep(0.5)  # 避免過度請求
    
    logger.info("\n" + "=" * 70)
    logger.info("測試完成")
    logger.info("=" * 70)


# ============================================================================
# 搜索函數 (多平台支持)
# ============================================================================

def search_pchome(keyword: str, pages: int = 3) -> List[Dict]:
    """
    搜索 PChome 商品 - 使用官方 API
    """
    results = []
    
    for page_num in range(1, pages + 1):
        try:
            page_results = search_pchome_api(keyword, page=page_num)
            if page_results:
                results.extend(page_results)
            else:
                # 無商品表示已到盡頭
                break
            
            time.sleep(0.3)  # 避免過度請求
        except Exception as e:
            logger.warning(f"第 {page_num} 頁失敗: {e}")
            break
    
    logger.info(f"PChome 共取得 {len(results)} 個商品")
    return results


def search_shopee(keyword: str, pages: int = 1) -> List[Dict]:
    """蝦皮搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"蝦皮搜索: {keyword} (待實現)")
    return []


def search_ruten(keyword: str, pages: int = 1) -> List[Dict]:
    """露天搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"露天搜索: {keyword} (待實現)")
    return []


def search_yahoo(keyword: str, pages: int = 1) -> List[Dict]:
    """Yahoo搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"Yahoo搜索: {keyword} (待實現)")
    return []


def search_cards_multi_platform(keyword: str) -> Dict[str, List[Dict]]:
    """
    在多個平台搜索卡牌
    返回格式: {'shopee': [...], 'ruten': [...], 'yahoo': [...], 'pchome': [...]}
    """
    results = {
        'shopee': [],
        'ruten': [],
        'yahoo': [],
        'pchome': search_pchome(keyword, pages=2)  # 獲取前 40 個商品
    }
    
    return results


# ============================================================================
# 示例卡牌列表 (備用)
# ============================================================================

def get_sample_search_results(platform: str) -> List[Dict]:
    """
    獲取示例卡牌列表 (備用)
    包含遊戲王和寶可夢卡牌的官方圖片
    """
    # 遊戲王卡牌
    yugioh_cards = [
        ('青眼白龍', 'https://images.ygoprodeck.com/images/cards/89631139.jpg'),
        ('黑魔法師', 'https://images.ygoprodeck.com/images/cards/16732705.jpg'),
        ('藍眼白龍', 'https://images.ygoprodeck.com/images/cards/70095154.jpg'),
        ('青眼白龍 終極龍', 'https://images.ygoprodeck.com/images/cards/70630755.jpg'),
    ]
    
    # 寶可夢卡牌
    pokemon_cards = [
        ('皮卡丘', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png'),
        ('妙蛙種子', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png'),
        ('小火龍', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png'),
        ('傑尼龜', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png'),
    ]
    
    base_cards = yugioh_cards + pokemon_cards
    
    platform_data = {
        'shopee': [
            {
                'product_id': f'sample_shopee_{i}',
                'name': f'{card[0]} - 示例',
                'price': 500 + (i * 50),
                'platform': 'shopee',
                'url': f'https://shopee.tw/search?keyword={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.5
            }
            for i, card in enumerate(base_cards)
        ],
        'ruten': [
            {
                'product_id': f'sample_ruten_{i}',
                'name': f'{card[0]} - 示例',
                'price': 450 + (i * 45),
                'platform': 'ruten',
                'url': f'https://www.ruten.com.tw/find/?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.3
            }
            for i, card in enumerate(base_cards)
        ],
        'yahoo': [
            {
                'product_id': f'sample_yahoo_{i}',
                'name': f'{card[0]} - 示例',
                'price': 600 + (i * 55),
                'platform': 'yahoo',
                'url': f'https://tw.bid.yahoo.com/search?p={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.6
            }
            for i, card in enumerate(base_cards)
        ],
        'pchome': [
            {
                'product_id': f'sample_pchome_{i}',
                'name': f'{card[0]} - 示例',
                'price': 550 + (i * 52),
                'platform': 'pchome',
                'url': f'https://24h.pchome.com.tw/search?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.4
            }
            for i, card in enumerate(base_cards)
        ]
    }
    
    return platform_data.get(platform, [])


# ============================================================================
# 主要爬蟲函數 (相容舊版 API)
# ============================================================================

def scrape_cards() -> List[Dict]:
    """爬取卡牌數據"""
    return search_pchome('遊戲卡 寶可夢卡', pages=2)


if __name__ == '__main__':
    # 運行測試
    test_pchome_api()
