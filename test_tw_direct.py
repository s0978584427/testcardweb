from scraper import CardScraper
import json

scraper = CardScraper()

# 測試 tw-pokemon
print("=== 測試 tw-pokemon 搜尋 ===")
cards = scraper.scrape_taiwan_pokemon('皮卡丘', limit=2)
print(f"找到 {len(cards)} 張卡牌")
if cards:
    print(f"第一張：{json.dumps(cards[0], indent=2, ensure_ascii=False)}")
