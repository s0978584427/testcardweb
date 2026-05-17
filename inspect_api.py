import requests
import json

url = 'https://api.pokemontcg.io/v2/cards?q=name:pikachu&pageSize=1'
resp = requests.get(url)
data = resp.json()
card = data['data'][0]

# 打印關鍵字段
print("卡片 ID:", card.get('id'))
print("名稱:", card.get('name'))
print("圖片:", card.get('images', {}).get('large'))
print("\n攻擊技能:")
attacks = card.get('attacks', [])
for attack in attacks[:3]:
    print(f"  - {attack.get('name')}: {attack.get('damage')} | {attack.get('text', '無效果')}")

print("\nHP:", card.get('hp'))
print("類型:", card.get('types'))
print("系列:", card.get('set', {}).get('name'))
