"""
國際卡牌 API 整合系統 - v2.0
支持：寶可夢 TCG (pokemontcg.io)、遊戲王 (ygoprodeck.com)、MTG (scryfall.com)

統一格式：
{
    'id': str,                    # 卡牌唯一識別碼
    'title': str,                 # 卡牌名稱
    'source': str,                # 來源: 'pokemon', 'yugioh', 'mtg'
    'img_url': str,               # 卡面圖 URL
    'price': float | str,         # 卡牌價格 (USD)
    'stats': {                    # 卡牌屬性
        'type': str,              # 卡牌類型
        'rarity': str,            # 稀有度
        'set': str,               # 系列名稱
        'attribute': str,         # (YuGiOh) 屬性
        'level': int,             # (YuGiOh) 等級
        'atk': int,               # (YuGiOh/MTG) 攻擊力
        'def': int,               # (YuGiOh) 防禦力
        'mana_cost': str,         # (MTG) 法力費
        'abilities': list,        # (Pokémon) 能力
        'hp': int,                # (Pokémon) 血量
    },
    'series': list,               # 發行版本清單 [{'name': str, 'set_id': str, 'release_date': str, 'price': float}]
    'description': str,           # 卡牌描述
}
"""
import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== 統一 User-Agent - 模擬現代瀏覽器 =====
BROWSER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# ===== 安全的 API 請求包裝 =====
def safe_request(url: str, method: str = 'GET', timeout: int = 10, **kwargs) -> Optional[requests.Response]:
    """
    安全的 HTTP 請求包裝 - 包含日誌和錯誤處理
    
    Args:
        url: 請求 URL（強制 HTTPS）
        method: HTTP 方法 (GET, POST 等)
        timeout: 超時秒數
        **kwargs: 其他 requests 參數
    
    Returns:
        Response 對象或 None (如果失敗)
    """
    # 確保使用 HTTPS
    if url.startswith('http://'):
        url = url.replace('http://', 'https://', 1)
        logger.info(f"🔒 自動轉換為 HTTPS: {url}")
    
    # 添加默認 User-Agent
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    if 'User-Agent' not in kwargs['headers']:
        kwargs['headers']['User-Agent'] = BROWSER_USER_AGENT
    
    try:
        logger.debug(f"📡 API 請求: {method} {url}")
        resp = requests.request(method, url, timeout=timeout, **kwargs)
        
        if resp.status_code == 200:
            logger.debug(f"✅ 請求成功: {url}")
        else:
            logger.warning(f"⚠️ API 返回 {resp.status_code}: {url}")
            logger.debug(f"響應內容: {resp.text[:200]}")  # 前 200 字元
        
        return resp
    
    except requests.exceptions.Timeout:
        logger.error(f"❌ 超時 (>= {timeout}s): {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ 連線失敗: {url} - {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ 未知錯誤 [{type(e).__name__}]: {url} - {str(e)}")
        return None




# ============================================================================
# 寶可夢 TCG API (pokemontcg.io)
# ============================================================================

def get_pokemon_tcg_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    """
    從 pokemontcg.io 獲取寶可夢卡牌
    文檔: https://docs.pokemontcg.io/
    
    Args:
        keyword: 搜尋關鍵字
        limit: 每頁結果數 (最多 20)
        page: 頁碼 (1-based)
    
    Returns:
        {'cards': [...], 'total': int, 'pages': int}
    """
    try:
        logger.info(f"🔍 [Pokémon TCG] 搜尋: '{keyword}', 頁碼: {page}")
        
        # 查詢參數：搜尋卡牌名稱
        query = f'q=name:"{keyword}"'
        
        # 計算分頁
        offset = (page - 1) * limit
        
        url = f'https://api.pokemontcg.io/v2/cards?{query}&pageSize={limit}&pageOffset={offset}'
        
        resp = safe_request(url)
        if not resp or resp.status_code != 200:
            logger.error(f"❌ [Pokémon TCG] 搜尋失敗: {resp.status_code if resp else '無回應'}")
            return {'cards': [], 'total': 0, 'pages': 0}
        
        data = resp.json()
        cards = data.get('data', [])
        total = data.get('totalCount', 0)
        pages = (total + limit - 1) // limit  # 計算總頁數
        
        results = []
        for card in cards[:limit]:
            try:
                # 取得集合名稱
                set_data = card.get('set', {})
                set_name = set_data.get('name', 'Unknown Set')
                rarity = card.get('rarity', 'Unknown')
                
                # 提取圖片 URL
                images = card.get('images', {})
                img_url = images.get('large', '') or images.get('small', '')
                img_large = images.get('large', '')
                
                # 如果沒有圖片 URL，使用空字符串（仍然返回卡牌）
                if not img_url:
                    logger.debug(f"[Pokémon TCG] 卡牌 {card.get('name')} 無圖片 URL")
                
                # 構建卡牌數據
                card_data = {
                    'id': card.get('id', ''),
                    'title': card.get('name', 'Unknown'),
                    'source': 'pokemon',
                    'img_url': img_url,
                    'img_large': img_large,
                    'price': 0.0,  # pokemontcg.io 不提供價格
                    'stats': {
                        'type': 'Pokémon Card',
                        'rarity': rarity,
                        'set': set_name,
                        'hp': card.get('hp', ''),
                        'types': [t if isinstance(t, str) else t.get('name', '') for t in card.get('types', [])],
                        'card_number': card.get('number', ''),
                    },
                    'series': [],  # TODO: 如需發行版本，需額外查詢
                    'description': f"{set_name} - {rarity}",
                }
                
                # 總是返回卡牌，即使沒有圖片 URL
                results.append(card_data)
            except Exception as e:
                logger.debug(f"[Pokémon TCG] 卡牌解析失敗: {e}")
                continue
        
        logger.info(f"[Pokémon TCG] 成功獲取 {len(results)} 張卡牌 (共 {total} 筆)")
        return {
            'cards': results,
            'total': total,
            'pages': pages,
            'current_page': page
        }
    
    except Exception as e:
        logger.error(f"[Pokémon TCG] 查詢失敗: {e}")
        return {'cards': [], 'total': 0, 'pages': 0}


# ============================================================================
# 遊戲王 API (ygoprodeck.com) - 新版本
# ============================================================================

def get_yugioh_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    """
    從 ygoprodeck.com 獲取遊戲王卡牌
    API: https://db.ygoprodeck.com/api/v7/cardinfo.php
    
    智能搜尋策略：
    1. 精確搜尋 (name 參數) - 用於完整的卡牌名稱
    2. 格式轉換 - 自動添加連字號（e.g., "Blue Eyes" → "Blue-Eyes"）
    3. 模糊搜尋 (fname 參數) - 用於部分名稱搜尋
    4. 單詞搜尋 - 如果多詞搜尋失敗，嘗試第一個單詞
    
    Args:
        keyword: 搜尋關鍵字
        limit: 每頁結果數
        page: 頁碼 (1-based)
    
    Returns:
        {'cards': [...], 'total': int, 'pages': int}
    """
    try:
        logger.info(f"🔍 [YuGiOh] 搜尋: '{keyword}', 頁碼: {page}")
        
        url = 'https://db.ygoprodeck.com/api/v7/cardinfo.php'
        
        # 搜尋策略清單
        search_strategies = []
        
        # 策略 1: 自動添加連字號（英文單詞用連字號連接）
        # 例如: "Blue Eyes White Dragon" → "Blue-Eyes White Dragon"
        if ' ' in keyword and '-' not in keyword:
            words = keyword.split()
            if len(words) >= 2:
                # 優先嘗試在前兩個單詞之間添加連字號
                hyphenated = '-'.join(words[:2]) + (' ' + ' '.join(words[2:]) if len(words) > 2 else '')
                search_strategies.append(('name', hyphenated, f'連字號格式: {hyphenated}'))
        
        # 策略 2: 原始關鍵字精確搜尋
        search_strategies.append(('name', keyword, f'精確搜尋: {keyword}'))
        
        # 策略 3: 原始關鍵字模糊搜尋
        search_strategies.append(('fname', keyword, f'模糊搜尋: {keyword}'))
        
        # 策略 4: 只用第一個單詞搜尋（如果有多個單詞）
        if ' ' in keyword:
            first_word = keyword.split()[0]
            search_strategies.append(('fname', first_word, f'第一個單詞: {first_word}'))
        
        # 執行搜尋策略
        cards = []
        for param_name, search_keyword, description in search_strategies:
            logger.debug(f"[YuGiOh] {description}")
            
            params = {param_name: search_keyword}
            resp = safe_request(url, params=params)
            
            if resp and resp.status_code == 200:
                try:
                    data = resp.json()
                    cards = data.get('data', []) if isinstance(data, dict) else data if isinstance(data, list) else []
                    
                    if cards:
                        logger.info(f"✅ [YuGiOh] 找到結果: {description} 返回 {len(cards)} 張卡牌")
                        break
                except Exception as e:
                    logger.debug(f"⚠️ [YuGiOh] JSON 解析失敗: {e}")
                    continue
        
        # 如果還是沒找到，記錄警告
        if not cards:
            logger.warning(f"❌ [YuGiOh] 未找到卡牌: {keyword}")
        
        # 計算分頁
        offset = (page - 1) * limit
        total = len(cards)
        paginated_cards = cards[offset:offset + limit]
        pages = (total + limit - 1) // limit if total > 0 else 1
        
        results = []
        all_prices = {}
        
        for card in paginated_cards:
            try:
                # 提取價格信息
                card_sets = card.get('card_sets', [])
                prices = []
                price_usd = 0.0
                
                for card_set in card_sets[:5]:  # 只顯示最近 5 個版本
                    set_name = card_set.get('set_name', '')
                    set_price = card_set.get('set_price', '0')
                    
                    try:
                        price_val = float(set_price) if set_price else 0.0
                    except:
                        price_val = 0.0
                    
                    if not price_usd or price_val > price_usd:
                        price_usd = price_val
                    
                    prices.append({
                        'name': set_name,
                        'set_id': card_set.get('set_code', ''),
                        'release_date': card_set.get('set_rarity_code', ''),
                        'price': price_val
                    })
                
                # 構建卡牌數據
                card_data = {
                    'id': str(card.get('id', '')),
                    'title': card.get('name', 'Unknown'),
                    'source': 'yugioh',
                    'img_url': card.get('card_images', [{}])[0].get('image_url', ''),
                    'img_large': card.get('card_images', [{}])[0].get('image_url_cropped', '') or card.get('card_images', [{}])[0].get('image_url', ''),
                    'price': price_usd,
                    'stats': {
                        'type': card.get('type', 'Unknown'),
                        'attribute': card.get('attribute', ''),
                        'level': card.get('level', 0),
                        'atk': card.get('atk', 0),
                        'def': card.get('def', 0),
                        'race': card.get('race', ''),
                    },
                    'series': prices,
                    'description': card.get('desc', '')[:300],
                }
                
                # 總是返回卡牌，即使沒有圖片 URL
                results.append(card_data)
            except Exception as e:
                logger.debug(f"[YuGiOh] 卡牌解析失敗: {e}")
                continue
        
        logger.info(f"[YuGiOh] 成功獲取 {len(results)} 張卡牌 (共 {total} 筆, 第 {page} 頁)")
        return {
            'cards': results,
            'total': total,
            'pages': pages,
            'current_page': page
        }
    
    except Exception as e:
        logger.error(f"[YuGiOh] 查詢失敗: {e}")
        return {'cards': [], 'total': 0, 'pages': 0}


# ============================================================================
# MTG API (scryfall.com) - 升級版本
# ============================================================================

def get_magic_cards(keyword: str, limit: int = 20, page: int = 1) -> Dict:
    """
    從 Scryfall API 獲取 MTG 卡牌
    API: https://api.scryfall.com/cards/search
    
    Args:
        keyword: 搜尋關鍵字
        limit: 每頁結果數 (最多 175)
        page: 頁碼 (1-based)
    
    Returns:
        {'cards': [...], 'total': int, 'pages': int}
    """
    try:
        logger.info(f"🔍 [MTG - Scryfall] 搜尋: '{keyword}', 頁碼: {page}")
        
        # 計算分頁
        offset = (page - 1) * limit
        
        # 搜尋翻譯: name: "keyword"（不用模糊搜尋符號）
        url = 'https://api.scryfall.com/cards/search'
        params = {
            'q': f'"{keyword}"',  # 簡單搜索
            'unique': 'prints',  # 去除重複列印版本
            'order': 'released',
            'dir': 'desc',
        }
        
        resp = safe_request(url, params=params)
        if not resp or resp.status_code != 200:
            logger.error(f"❌ [MTG] 搜尋失敗: {resp.status_code if resp else '無回應'}")
            return {'cards': [], 'total': 0, 'pages': 0}
        
        data = resp.json()
        all_cards = data.get('data', [])
        
        # 手動分頁
        paginated_cards = all_cards[offset:offset + limit]
        total = len(all_cards)
        pages = (total + limit - 1) // limit
        
        results = []
        for card in paginated_cards:
            try:
                # 取得價格
                prices = card.get('prices', {})
                price_usd = prices.get('usd', None)
                if price_usd:
                    try:
                        price_usd = float(price_usd)
                    except:
                        price_usd = 0.0
                else:
                    price_usd = 0.0
                
                # 取得圖片
                img_url = card.get('image_uris', {}).get('normal', '')
                img_large = card.get('image_uris', {}).get('large', '') or img_url
                
                # 構建卡牌數據
                card_data = {
                    'id': card.get('id', ''),
                    'title': card.get('name', 'Unknown'),
                    'source': 'mtg',
                    'img_url': img_url,
                    'img_large': img_large,
                    'price': price_usd,
                    'stats': {
                        'type': card.get('type_line', 'Unknown'),
                        'mana_cost': card.get('mana_cost', ''),
                        'power': card.get('power', ''),
                        'toughness': card.get('toughness', ''),
                        'rarity': card.get('rarity', 'Unknown'),
                        'set': card.get('set_name', 'Unknown'),
                    },
                    'series': [{
                        'name': card.get('set_name', 'Unknown'),
                        'set_id': card.get('set', ''),
                        'release_date': card.get('released_at', ''),
                        'price': price_usd
                    }],
                    'description': card.get('oracle_text', '')[:300],
                }
                
                # 總是返回卡牌，即使沒有圖片 URL
                results.append(card_data)
            except Exception as e:
                logger.debug(f"[MTG] 卡牌解析失敗: {e}")
                continue
        
        logger.info(f"[MTG] 成功獲取 {len(results)} 張卡牌 (共 {total} 筆)")
        return {
            'cards': results,
            'total': total,
            'pages': pages,
            'current_page': page
        }
    
    except Exception as e:
        logger.error(f"[MTG] 查詢失敗: {e}")
        return {'cards': [], 'total': 0, 'pages': 0}


# ============================================================================
# 統一搜尋介面（保持向後兼容邊）
# ============================================================================

def get_all_card_sources(keyword: str) -> Dict[str, List[Dict]]:
    """
    舊版本：統一搜索所有卡牌來源（無分頁）
    返回: {
        'yugioh': [...],
        'pokemon': [...],
        'mtg': [...]
    }
    """
    logger.info(f"搜索所有卡牌來源: {keyword}")
    
    yugioh_result = get_yugioh_cards(keyword, limit=5, page=1)
    pokemon_result = get_pokemon_tcg_cards(keyword, limit=5, page=1)
    mtg_result = get_magic_cards(keyword, limit=5, page=1)
    
    return {
        'yugioh': yugioh_result.get('cards', []),
        'pokemon': pokemon_result.get('cards', []),
        'mtg': mtg_result.get('cards', [])
    }


def search_all_cards_paginated(keyword: str, limit: int = 20, page: int = 1) -> Dict[str, Dict]:
    """
    新版本：同時搜尋所有平台（支援分頁）
    
    Returns:
        {
            'pokemon': {'cards': [...], 'total': int, 'pages': int},
            'yugioh': {'cards': [...], 'total': int, 'pages': int},
            'mtg': {'cards': [...], 'total': int, 'pages': int}
        }
    """
    return {
        'pokemon': get_pokemon_tcg_cards(keyword, limit, page),
        'yugioh': get_yugioh_cards(keyword, limit, page),
        'mtg': get_magic_cards(keyword, limit, page)
    }


if __name__ == '__main__':
    # 測試
    print("\n=== 測試寶可夢 TCG ===")
    pokemon = get_pokemon_tcg_cards('Pikachu', limit=3)
    print(f"找到 {pokemon['total']} 筆結果，顯示 {len(pokemon['cards'])} 張卡牌")
    if pokemon['cards']:
        print(f"First card: {pokemon['cards'][0]['title']}")
    
    print("\n=== 測試遊戲王 ===")
    yugioh = get_yugioh_cards('Blue Eyes', limit=3)
    print(f"找到 {len(yugioh['cards'])} 張卡牌")
    if yugioh['cards']:
        print(f"First card: {yugioh['cards'][0]['title']}")
    
    print("\n=== 測試 MTG ===")
    mtg = get_magic_cards('Black Lotus', limit=3)
    print(f"找到 {mtg['total']} 筆結果，顯示 {len(mtg['cards'])} 張卡牌")
    if mtg['cards']:
        print(f"First card: {mtg['cards'][0]['title']}")
    
    print("\n=== 測試 PokeAPI ===")
    pokemon = get_pokemon_cards('皮卡丘')
    for card in pokemon:
        print(f"寶可夢: {card['title']} - {card['img_url'][:50]}")
    
    print("\n=== 測試 Scryfall ===")
    mtg = get_magic_cards('Black Lotus')
    for card in mtg[:2]:
        print(f"魔法風雲會: {card['title']} - {card['img_url'][:50]}")
