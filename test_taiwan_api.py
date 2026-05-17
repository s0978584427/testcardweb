#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""測試台灣官方寶可夢 API"""

import requests
import json

print("=" * 80)
print("尋找台灣官方寶可夢 API 端點")
print("=" * 80)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

# 嘗試不同的 API 端點
api_urls = [
    "https://asia.pokemon-card.com/api/v1/card/search",
    "https://asia.pokemon-card.com/tw/api/card-search",
    "https://asia.pokemon-card.com/tw/api/cards",
    "https://api.pokemon-card.com/tw/search",
    "https://asia.pokemon-card.com/tw/card-search/api",
]

for url in api_urls:
    try:
        print(f"\n[嘗試] {url}")
        
        # POST 請求
        payload = {"keyword": "pikachu", "page": 1, "limit": 5}
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"  狀態碼: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Content-Type: {resp.headers.get('content-type')}")
            if 'json' in resp.headers.get('content-type', ''):
                data = resp.json()
                print(f"  ✓ JSON 回應: {list(data.keys())[:5]}")
    except Exception as e:
        print(f"  ✗ 失敗: {str(e)[:50]}")

print("\n" + "=" * 80)
print("替代方案：使用 pokemontcg.io API (英文名稱)")
print("=" * 80)

try:
    url = 'https://api.pokemontcg.io/v2/cards?q=name:"pikachu"&pageSize=5'
    print(f"\n[嘗試] {url}")
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"狀態碼: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        cards = data.get('data', [])
        print(f"✓ 找到 {len(cards)} 張卡牌")
        if cards:
            print(f"  第一張: {cards[0].get('name')} ({cards[0].get('set', {}).get('name')})")
except Exception as e:
    print(f"✗ 失敗: {e}")

