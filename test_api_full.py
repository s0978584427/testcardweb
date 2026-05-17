import json
import requests

# 測試 pokemon-en 路由
print('=== 測試 pokemon-en 英文版本 ===')
resp = requests.get('http://localhost:5000/api/get_cards?source=pokemon-en&keyword=Pikachu&limit=1')
if resp.status_code == 200:
    data = resp.json()
    if data['results']:
        card = data['results'][0]
        print(f"卡牌: {card.get('name')}")
        print(f"來源: {card.get('source')}")
        img_url = card.get('image_url', '')
        print(f"圖片: {img_url[:50] if img_url else 'N/A'}...")
        skills = card.get('skills', [])
        print(f"技能數量: {len(skills)}")
        if skills:
            print(f"第一個技能: {skills[0]['name']} - {skills[0]['effect'][:50]}...")
else:
    print(f'失敗: {resp.status_code}')

print()

# 測試 tw-pokemon 路由
print('=== 測試 tw-pokemon 繁中版本 ===')
resp = requests.get('http://localhost:5000/api/get_cards?source=tw-pokemon&keyword=皮卡丘&limit=1')
if resp.status_code == 200:
    data = resp.json()
    if data['results']:
        card = data['results'][0]
        print(f"卡牌: {card.get('name')}")
        print(f"來源: {card.get('source')}")
        print(f"屬性: {card.get('type')}")
        img_url = card.get('image_url', '')
        print(f"圖片: {img_url[:50] if img_url else 'N/A'}...")
        skills = card.get('skills', [])
        print(f"技能數量: {len(skills)}")
        if skills:
            print(f"第一個技能: {skills[0]['name']} - {skills[0]['effect'][:50]}...")
else:
    print(f'失敗: {resp.status_code}')
