#!/usr/bin/env python3
# 快速測試腳本
from models import init_db
from scraper import scrape_cards

print("初始化資料庫...")
init_db()

print("爬取卡牌...")
cards = scrape_cards()

print(f"✅ 成功爬取 {len(cards)} 張卡牌")
if cards:
    for i, card in enumerate(cards[:3], 1):
        print(f"  {i}. {card['name']} - NT${card['price']}")
