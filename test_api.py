import requests
import json
from urllib.parse import quote

# 測試 PChome API 的實際響應
url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={quote('遊戲卡')}&offset=0&limit=5"

print(f"查詢 URL: {url}\n")

try:
    response = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }, timeout=10)
    
    print(f"狀態碼: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        
        # 列印完整 JSON（限制深度）
        print("完整 JSON 結構:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        
        print("\n\n頂層鍵值:")
        print(list(data.keys()))
        
        # 檢查各種可能的字段名
        for key in ['prods', 'products', 'prod', 'product', 'items', 'item', 'data', 'result', 'results']:
            if key in data:
                print(f"\n找到字段: {key}")
                print(f"類型: {type(data[key])}")
                if isinstance(data[key], list):
                    print(f"長度: {len(data[key])}")
                    if data[key]:
                        print(f"第一個元素的鍵: {list(data[key][0].keys())}")
except Exception as e:
    print(f"錯誤: {e}")
