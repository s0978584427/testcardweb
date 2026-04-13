"""
開源卡牌 API 模組
支持 YGOProDeck, PokeAPI, Scryfall
無需爬蟲，官方 API 提供
"""
import requests
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_yugioh_cards(name: str, limit: int = 5) -> List[Dict]:
    """
    從 YGOProDeck API 獲取遊戲王卡牌信息
    API: https://api.ygoprodeckdb.com/v8.0/cardinfo
    """
    try:
        logger.info(f"[YGOProDeck] 搜尋: {name}")
        url = "https://api.ygoprodeckdb.com/v8.0/cardinfo"
        params = {
            'name': name,
            'num': min(limit, 10)  # API 最多返回 10 個
        }
        
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"[YGOProDeck] API 返回狀態碼: {resp.status_code}")
            return []
        
        data = resp.json()
        cards = data.get('data', [])
        
        results = []
        for card in cards[:limit]:
            try:
                card_data = {
                    'title': card.get('name', 'Unknown'),
                    'type': card.get('type', 'Unknown'),
                    'attribute': card.get('attribute', ''),
                    'atk': card.get('atk', 0),
                    'def': card.get('def', 0),
                    'desc': card.get('desc', '')[:200],  # 限制描述長度
                    'img_url': card.get('card_images', [{}])[0].get('image_url', ''),
                    'source': 'yugioh'
                }
                if card_data['img_url']:
                    results.append(card_data)
            except Exception as e:
                logger.debug(f"[YGOProDeck] 卡牌解析失敗: {e}")
                continue
        
        logger.info(f"[YGOProDeck] 成功獲取 {len(results)} 張卡牌")
        return results
    
    except Exception as e:
        logger.error(f"[YGOProDeck] API 呼叫失敗: {e}")
        return []


def get_pokemon_cards(name: str, limit: int = 5) -> List[Dict]:
    """
    從 PokeAPI 獲取寶可夢信息
    API: https://pokeapi.co/api/v2/pokemon
    """
    try:
        logger.info(f"[PokeAPI] 搜尋: {name}")
        
        # 寶可夢 API 不支援直接搜尋，需轉換為英文對應名
        name_en = name.lower().replace('寶可夢', '').replace('pokemon', '')
        
        url = f"https://pokeapi.co/api/v2/pokemon/{name_en}"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code != 200:
            # 嘗試用簡化名稱
            logger.debug(f"[PokeAPI] 精確匹配失敗")
            url = f"https://pokeapi.co/api/v2/pokemon-species/{name_en}"
            resp = requests.get(url, timeout=10)
        
        if resp.status_code != 200:
            logger.warning(f"[PokeAPI] 找不到寶可夢: {name}")
            return []
        
        data = resp.json()
        
        # 獲取圖片 URL
        pokemon_url = f"https://pokeapi.co/api/v2/pokemon/{data.get('id', '')}"
        pokemon_resp = requests.get(pokemon_url, timeout=10)
        pokemon_data = pokemon_resp.json() if pokemon_resp.status_code == 200 else {}
        
        img_url = pokemon_data.get('sprites', {}).get('front_default', '')
        
        result = [{
            'title': data.get('name', 'Unknown').capitalize(),
            'type': 'Pokémon',
            'habitat': data.get('habitat', {}).get('name', 'Unknown'),
            'color': data.get('color', {}).get('name', 'Unknown'),
            'desc': data.get('flavor_text_entries', [{}])[0].get('flavor_text', '')[:200],
            'img_url': img_url,
            'source': 'pokemon'
        }]
        
        logger.info(f"[PokeAPI] 成功獲取 1 隻寶可夢")
        return result if img_url else []
    
    except Exception as e:
        logger.error(f"[PokeAPI] API 呼叫失敗: {e}")
        return []


def get_magic_cards(name: str, limit: int = 5) -> List[Dict]:
    """
    從 Scryfall API 獲取魔法風雲會卡牌信息
    API: https://api.scryfall.com/cards/search
    """
    try:
        logger.info(f"[Scryfall] 搜尋: {name}")
        
        url = "https://api.scryfall.com/cards/search"
        params = {
            'q': f'name:{name}',
            'order': 'released',
            'dir': 'desc',
            'unique': 'prints'
        }
        
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code != 200:
            logger.warning(f"[Scryfall] API 返回狀態碼: {resp.status_code}")
            return []
        
        data = resp.json()
        cards = data.get('data', [])
        
        results = []
        for card in cards[:limit]:
            try:
                card_data = {
                    'title': card.get('name', 'Unknown'),
                    'type': card.get('type_line', 'Unknown'),
                    'mana_cost': card.get('mana_cost', ''),
                    'power': card.get('power', ''),
                    'toughness': card.get('toughness', ''),
                    'text': card.get('oracle_text', '')[:200],
                    'img_url': card.get('image_uris', {}).get('normal', ''),
                    'source': 'mtg'
                }
                if card_data['img_url']:
                    results.append(card_data)
            except Exception as e:
                logger.debug(f"[Scryfall] 卡牌解析失敗: {e}")
                continue
        
        logger.info(f"[Scryfall] 成功獲取 {len(results)} 張卡牌")
        return results
    
    except Exception as e:
        logger.error(f"[Scryfall] API 呼叫失敗: {e}")
        return []


def get_all_card_sources(keyword: str) -> Dict[str, List[Dict]]:
    """
    統一搜索所有卡牌來源
    返回: {
        'yugioh': [...],
        'pokemon': [...],
        'mtg': [...]
    }
    """
    logger.info(f"搜索所有卡牌來源: {keyword}")
    
    results = {
        'yugioh': get_yugioh_cards(keyword),
        'pokemon': get_pokemon_cards(keyword),
        'mtg': get_magic_cards(keyword)
    }
    
    return results


if __name__ == '__main__':
    # 測試卡牌 API
    print("\n=== 測試 YGOProDeck ===")
    yugioh = get_yugioh_cards('青眼白龍')
    for card in yugioh[:2]:
        print(f"遊戲王: {card['title']} - {card['img_url'][:50]}")
    
    print("\n=== 測試 PokeAPI ===")
    pokemon = get_pokemon_cards('皮卡丘')
    for card in pokemon:
        print(f"寶可夢: {card['title']} - {card['img_url'][:50]}")
    
    print("\n=== 測試 Scryfall ===")
    mtg = get_magic_cards('Black Lotus')
    for card in mtg[:2]:
        print(f"魔法風雲會: {card['title']} - {card['img_url'][:50]}")
