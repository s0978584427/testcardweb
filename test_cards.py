from scraper import get_sample_search_results

results = get_sample_search_results('shopee')
print(f'総卡牌数: {len(results)}')
print(f'\n前5張卡牌:')
for i in range(min(5, len(results))):
    print(f'  {i+1}. {results[i]["name"]}')
    
print(f'\n最后5張卡牌:')
for i in range(max(0, len(results)-5), len(results)):
    print(f'  {i+1}. {results[i]["name"]}')
    
# 檢查是否有寶可夢卡牌
pokemon_names = ['皮卡丘', '妙蛙種子', '小火龍', '傑尼龜', '洛奇亞', '鳳王', '火焰龍', '水箭龜']
pokemon_found = [name for name in pokemon_names if any(name in r['name'] for r in results)]
print(f'\n找到的寶可夢卡牌: {pokemon_found}')
