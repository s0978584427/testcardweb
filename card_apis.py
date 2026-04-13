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
        name_en = name.lower().replace('寶可夢', '').replace('pokemon', '').strip()
        
        # 通用搜尋 - 如果搜尋詞為空或是通用詞，返回熱門寶可夢
        if not name_en or name_en == '':
            popular_pokemon = ['pikachu', 'charizard', 'dragonite', 'alakazam', 'blastoise']
            results = []
            for poke_name in popular_pokemon:
                try:
                    url = f"https://pokeapi.co/api/v2/pokemon/{poke_name}"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        pokemon_data = resp.json()
                        img_url = pokemon_data.get('sprites', {}).get('front_default', '')
                        if not img_url:
                            img_url = pokemon_data.get('sprites', {}).get('other', {}).get('official-artwork', {}).get('front_default', '')
                        if img_url:
                            results.append({
                                'title': pokemon_data.get('name', poke_name).capitalize(),
                                'type': 'Pokémon',
                                'id': pokemon_data.get('id', 0),
                                'desc': 'Popular Pokémon',
                                'img_url': img_url,
                                'source': 'pokemon'
                            })
                        if len(results) >= limit:
                            break
                except:
                    continue
            
            if results:
                logger.info(f"[PokeAPI] 返回 {len(results)} 隻熱門寶可夢")
                return results
            return []
        
        # 具體搜尋
        url = f"https://pokeapi.co/api/v2/pokemon/{name_en}"
        resp = requests.get(url, timeout=10)
        
        pokemon_data = None
        if resp.status_code == 200:
            pokemon_data = resp.json()
        else:
            # 嘗試用物種搜尋，然後找到對應的 pokemon
            logger.debug(f"[PokeAPI] 直接搜尋失敗，嘗試物種...")
            url = f"https://pokeapi.co/api/v2/pokemon-species/{name_en}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                species_data = resp.json()
                # 從物種找到對應的 pokemon
                varieties = species_data.get('varieties', [])
                if varieties:
                    pokemon_url = varieties[0].get('pokemon', {}).get('url', '')
                    if pokemon_url:
                        pokemon_resp = requests.get(pokemon_url, timeout=10)
                        if pokemon_resp.status_code == 200:
                            pokemon_data = pokemon_resp.json()
        
        if not pokemon_data:
            logger.warning(f"[PokeAPI] 找不到寶可夢: {name}")
            return []
        
        # 獲取圖片 URL
        img_url = pokemon_data.get('sprites', {}).get('front_default', '')
        
        if not img_url:
            # 嘗試使用官方圖集
            img_url = pokemon_data.get('sprites', {}).get('other', {}).get('official-artwork', {}).get('front_default', '')
        
        if not img_url:
            logger.warning(f"[PokeAPI] {name_en} 沒有圖片")
            return []
        
        # 安全獲取 flavor_text_entries
        flavor_text = ''
        flavor_entries = pokemon_data.get('flavor_text_entries', [])
        if flavor_entries and isinstance(flavor_entries, list):
            flavor_text = flavor_entries[0].get('flavor_text', '')
        
        # 如果來自 pokemon-species，獲取更好的描述
        species_data_check = None
        species_url = pokemon_data.get('species', {}).get('url', '')
        if species_url:
            try:
                species_resp = requests.get(species_url, timeout=5)
                if species_resp.status_code == 200:
                    species_data_check = species_resp.json()
                    if not flavor_text and species_data_check.get('flavor_text_entries'):
                        flavor_text = species_data_check['flavor_text_entries'][0].get('flavor_text', '')
            except:
                pass
        
        result = [{
            'title': pokemon_data.get('name', name_en).capitalize(),
            'type': 'Pokémon',
            'id': pokemon_data.get('id', 0),
            'height': pokemon_data.get('height', 0) / 10,  # 轉換為公尺
            'weight': pokemon_data.get('weight', 0) / 10,  # 轉換為公斤
            'desc': flavor_text[:200] if flavor_text else 'A Pokémon',
            'img_url': img_url,
            'source': 'pokemon'
        }]
        
        logger.info(f"[PokeAPI] 成功獲取: {pokemon_data.get('name', name_en)}")
        return result
    
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
        
        if not name or len(name.strip()) < 2:
            # 通用搜尋 - 返回熱門 MTG 卡牌
            popular_cards = ['black lotus', 'blue eyes white dragon', 'forest', 'mountain']
            results = []
            for card_name in popular_cards:
                try:
                    url = "https://api.scryfall.com/cards/search"
                    params = {
                        'q': f'name:"{card_name}"',
                        'order': 'released',
                        'dir': 'desc',
                        'unique': 'prints'
                    }
                    resp = requests.get(url, params=params, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        cards = data.get('data', [])
                        if cards:
                            card = cards[0]
                            results.append({
                                'title': card.get('name', card_name),
                                'type': card.get('type_line', 'Card'),
                                'mana_cost': card.get('mana_cost', ''),
                                'text': card.get('oracle_text', '')[:200],
                                'img_url': card.get('image_uris', {}).get('normal', ''),
                                'source': 'mtg'
                            })
                        if len(results) >= limit:
                            break
                except:
                    continue
            
            if results:
                logger.info(f"[Scryfall] 返回 {len(results)} 張熱門卡牌")
                return results
            return []
        
        # 具體搜尋
        url = "https://api.scryfall.com/cards/search"
        params = {
            'q': f'name:{name}',
            'order': 'released',
            'dir': 'desc',
            'unique': 'prints'
        }
        
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code != 200:
            # 嘗試模糊搜尋
            logger.debug(f"[Scryfall] 精確搜尋失敗，嘗試模糊搜尋...")
            params['q'] = name
            resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code != 200:
            logger.warning(f"[Scryfall] API 返回狀態碼: {resp.status_code}")
            return []
        
        data = resp.json()
        cards = data.get('data', [])
        
        results = []
        for card in cards[:limit]:
            try:
                img_url = card.get('image_uris', {}).get('normal', '')
                if not img_url and 'card_faces' in card:
                    # 雙面卡
                    img_url = card['card_faces'][0].get('image_uris', {}).get('normal', '')
                
                if img_url:
                    card_data = {
                        'title': card.get('name', 'Unknown'),
                        'type': card.get('type_line', 'Unknown'),
                        'mana_cost': card.get('mana_cost', ''),
                        'power': card.get('power', ''),
                        'toughness': card.get('toughness', ''),
                        'text': card.get('oracle_text', '')[:200],
                        'img_url': img_url,
                        'source': 'mtg'
                    }
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
