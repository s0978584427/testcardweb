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
    從 PokeAPI 獲取寶可夢信息和卡牌數據
    API: https://pokeapi.co/api/v2/pokemon
    返回: 寶可夢的屬性、能力、進化等卡牌相關信息
    """
    try:
        logger.info(f"[PokeAPI] 搜尋: {name}")
        
        # 寶可夢 API 不支援直接搜尋，需轉換為英文對應名
        # 檢查是否是通用詞搜尋
        is_generic = any(word in name.lower() for word in ['pokemon', '寶可夢', 'pocket monster'])
        
        def build_pokemon_card(pokemon_data: dict, pokemon_name: str = '') -> dict:
            """構建寶可夢卡牌數據"""
            img_url = pokemon_data.get('sprites', {}).get('front_default', '')
            if not img_url:
                img_url = pokemon_data.get('sprites', {}).get('other', {}).get('official-artwork', {}).get('front_default', '')
            
            # 提取屬性 (types)
            types = []
            for type_info in pokemon_data.get('types', []):
                type_name = type_info.get('type', {}).get('name', '')
                if type_name:
                    types.append(type_name.capitalize())
            
            # 提取能力 (abilities)
            abilities = []
            for ability_info in pokemon_data.get('abilities', []):
                ability_name = ability_info.get('ability', {}).get('name', '')
                is_hidden = ability_info.get('is_hidden', False)
                if ability_name:
                    abilities.append({
                        'name': ability_name.replace('-', ' ').title(),
                        'is_hidden': is_hidden
                    })
            
            # 提取基礎數據 (stats)
            stats = {}
            for stat_info in pokemon_data.get('stats', []):
                stat_name = stat_info.get('stat', {}).get('name', '').upper()
                stat_value = stat_info.get('base_stat', 0)
                if stat_name:
                    stats[stat_name] = stat_value
            
            # 獲取物種信息（進化、特性等）
            species_info = {}
            try:
                species_url = pokemon_data.get('species', {}).get('url', '')
                if species_url:
                    species_resp = requests.get(species_url, timeout=5)
                    if species_resp.status_code == 200:
                        species_data = species_resp.json()
                        # 進化鏈
                        evolution_chain_url = species_data.get('evolution_chain', {}).get('url', '')
                        if evolution_chain_url:
                            species_info['generation'] = species_data.get('generation', {}).get('name', '')
                            species_info['habitat'] = species_data.get('habitat', {}).get('name', '')
                            
                            # 簡略的進化信息
                            try:
                                evo_resp = requests.get(evolution_chain_url, timeout=5)
                                if evo_resp.status_code == 200:
                                    evo_data = evo_resp.json()
                                    evo_chain = evo_data.get('chain', {})
                                    evolutions = []
                                    
                                    # 遞歸提取進化鏈
                                    def extract_evolution(chain):
                                        if chain.get('species'):
                                            evolutions.append(chain['species'].get('name', '').title())
                                        for evo in chain.get('evolves_to', []):
                                            extract_evolution(evo)
                                    
                                    extract_evolution(evo_chain)
                                    if evolutions:
                                        species_info['evolution_line'] = ' → '.join(evolutions)
                            except:
                                pass
            except:
                pass
            
            card_data = {
                'title': pokemon_data.get('name', pokemon_name).capitalize(),
                'id': pokemon_data.get('id', 0),
                'type': 'Pokémon Card',
                'types': types if types else ['Normal'],
                'height': f"{pokemon_data.get('height', 0) / 10:.1f}m",  # 公尺
                'weight': f"{pokemon_data.get('weight', 0) / 10:.1f}kg",  # 公斤
                'abilities': abilities[:3],  # 最多 3 個能力
                'stats': stats,  # HP, ATK, DEF, SP.ATK, SP.DEF, SPEED
                'generation': species_info.get('generation', 'Unknown'),
                'habitat': species_info.get('habitat', 'Unknown'),
                'evolution_line': species_info.get('evolution_line', 'N/A'),
                'img_url': img_url,
                'source': 'pokemon'
            }
            return card_data
        
        if is_generic or not name or len(name.strip()) < 2:
            # 通用搜尋或空搜尋 - 返回熱門寶可夢
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
                            card = build_pokemon_card(pokemon_data, poke_name)
                            results.append(card)
                        if len(results) >= limit:
                            break
                except:
                    continue
            
            if results:
                logger.info(f"[PokeAPI] 返回 {len(results)} 隻熱門寶可夢卡牌")
                return results
            return []
        
        # 具體搜尋 - 移除多餘詞彙
        name_en = name.lower()
        for word in ['寶可夢', 'pokemon']:
            name_en = name_en.replace(word, '').strip()
        
        if not name_en or len(name_en) < 2:
            # 如果移除後沒有內容，返回熱門寶可夢
            return get_pokemon_cards('pokemon', limit)
        
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
        
        result = [build_pokemon_card(pokemon_data, name_en)]
        
        logger.info(f"[PokeAPI] 成功獲取: {pokemon_data.get('name', name_en)} 卡牌信息")
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
