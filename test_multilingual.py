import json
from scraper import CardScraper

scraper = CardScraper()

# 測試繁中版本
print("=== 繁中版本 (scrape_taiwan_pokemon) ===")
tw_results = scraper.scrape_taiwan_pokemon('皮卡丘', limit=2)
if tw_results:
    print(json.dumps(tw_results[0], indent=2, ensure_ascii=False))
else:
    print("無結果")

print("\n=== 英文版本 (scrape_pokemon_en) ===")
en_results = scraper.scrape_pokemon_en('Pikachu', limit=2)
if en_results:
    print(json.dumps(en_results[0], indent=2, ensure_ascii=False))
else:
    print("無結果")
