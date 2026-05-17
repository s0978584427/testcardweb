#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""測試更新後的台灣寶可夢搜尋 (支持中文)"""

from scraper import CardScraper
import json

scraper = CardScraper()

print("=" * 80)
print("測試更新後的台灣寶可夢搜尋 (支持中文)")
print("=" * 80)

# 測試中文搜尋
test_keywords = ['皮卡丘', 'pikachu', '妙蛙種子']

for keyword in test_keywords:
    print(f"\n[測試] {keyword}")
    results = scraper.scrape_taiwan_pokemon(keyword, limit=3)
    print(f"找到 {len(results)} 張卡牌")
    
    if results:
        card = results[0]
        print(f"  - {card.get('title')} (HP: {card['stats'].get('hp')})")
        print(f"    屬性: {card['stats'].get('pokemon_type')}")
        print(f"    系列: {card['series'].get('collection_name')}")
