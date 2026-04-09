from scraper import get_sample_search_results

all_cards = get_sample_search_results('shopee')
pokemon_cards = [c for c in all_cards if c.get('image', '').startswith('https://raw.githubusercontent.com/PokeAPI')]

print("完整的寶可夢卡牌列表 (24 張):")
print("=" * 50)
for i, card in enumerate(pokemon_cards, 1):
    pokemon_id = card['image'].split('/')[-1].split('.')[0]
    print(f"{i:2d}. {card['name'].replace(' - 初版', '').replace(' - 重版', '').replace(' - 特別版', ''):15s} (#{pokemon_id})")
