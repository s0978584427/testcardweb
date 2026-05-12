#!/usr/bin/env python3
"""
測試後端 Proxy 路由 - /api/get_cards
用於驗證在本地或 Render 環境中是否正常工作
"""
import requests
import json
import sys
from datetime import datetime

# 設定測試 URL
BASE_URL = "http://localhost:5000"  # 本地測試
# BASE_URL = "https://your-render-app.onrender.com"  # Render 環境

def print_header(title):
    """打印標題"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def test_pokemon_api():
    """測試 Pokemon TCG API 代理"""
    print_header("測試 1: Pokemon TCG API (pokemontcg.io)")
    
    url = f"{BASE_URL}/api/get_cards"
    params = {
        'source': 'pokemon',
        'keyword': 'pikachu',
        'limit': 5
    }
    
    print(f"📡 請求: {url}")
    print(f"📋 參數: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        print(f"✅ 狀態碼: {response.status_code}")
        print(f"📊 回應:")
        print(f"   - 來源: {data.get('source')}")
        print(f"   - 關鍵字: {data.get('keyword')}")
        print(f"   - 結果數: {data.get('total')}")
        print(f"   - 狀態: {data.get('status')}")
        
        if data.get('status') == 'success' and data.get('results'):
            print(f"\n📋 卡牌示例:")
            for i, card in enumerate(data.get('results')[:2], 1):
                print(f"   {i}. {card.get('title')}")
                print(f"      - ID: {card.get('id')}")
                print(f"      - 稀有度: {card.get('rarity')}")
                print(f"      - 圖片: {card.get('img_url')[:50]}...")
        else:
            print(f"\n❌ 錯誤: {data.get('error')}")
            print(f"   詳情: {data.get('details')}")
        
        return data.get('status') == 'success'
    
    except Exception as e:
        print(f"❌ 請求失敗: {str(e)}")
        return False

def test_yugioh_api():
    """測試 YuGiOh API 代理"""
    print_header("測試 2: YuGiOh API (ygoprodeck.com)")
    
    url = f"{BASE_URL}/api/get_cards"
    params = {
        'source': 'yugioh',
        'keyword': 'blue eyes',
        'limit': 5
    }
    
    print(f"📡 請求: {url}")
    print(f"📋 參數: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        print(f"✅ 狀態碼: {response.status_code}")
        print(f"📊 回應:")
        print(f"   - 來源: {data.get('source')}")
        print(f"   - 關鍵字: {data.get('keyword')}")
        print(f"   - 結果數: {data.get('total')}")
        print(f"   - 狀態: {data.get('status')}")
        
        if data.get('status') == 'success' and data.get('results'):
            print(f"\n📋 卡牌示例:")
            for i, card in enumerate(data.get('results')[:2], 1):
                print(f"   {i}. {card.get('title')}")
                print(f"      - ID: {card.get('id')}")
                print(f"      - 屬性: {card.get('attribute')}")
        else:
            print(f"\n❌ 錯誤: {data.get('error')}")
            print(f"   詳情: {data.get('details')}")
        
        return data.get('status') == 'success'
    
    except Exception as e:
        print(f"❌ 請求失敗: {str(e)}")
        return False

def test_mtg_api():
    """測試 MTG API 代理"""
    print_header("測試 3: Magic: The Gathering API (scryfall.com)")
    
    url = f"{BASE_URL}/api/get_cards"
    params = {
        'source': 'mtg',
        'keyword': 'black lotus',
        'limit': 5
    }
    
    print(f"📡 請求: {url}")
    print(f"📋 參數: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        print(f"✅ 狀態碼: {response.status_code}")
        print(f"📊 回應:")
        print(f"   - 來源: {data.get('source')}")
        print(f"   - 關鍵字: {data.get('keyword')}")
        print(f"   - 結果數: {data.get('total')}")
        print(f"   - 狀態: {data.get('status')}")
        
        if data.get('status') == 'success' and data.get('results'):
            print(f"\n📋 卡牌示例:")
            for i, card in enumerate(data.get('results')[:2], 1):
                print(f"   {i}. {card.get('title')}")
                print(f"      - ID: {card.get('id')}")
                print(f"      - 法力費: {card.get('mana_cost')}")
        else:
            print(f"\n❌ 錯誤: {data.get('error')}")
            print(f"   詳情: {data.get('details')}")
        
        return data.get('status') == 'success'
    
    except Exception as e:
        print(f"❌ 請求失敗: {str(e)}")
        return False

def test_error_handling():
    """測試錯誤處理"""
    print_header("測試 4: 錯誤處理")
    
    # 測試 1: 缺少參數
    print("📋 情況 1: 缺少 source 參數")
    try:
        response = requests.get(f"{BASE_URL}/api/get_cards", params={'keyword': 'test'}, timeout=5)
        data = response.json()
        print(f"   狀態碼: {response.status_code}")
        print(f"   錯誤: {data.get('error')}")
        test1_pass = response.status_code == 400
    except Exception as e:
        print(f"   ❌ 請求失敗: {str(e)}")
        test1_pass = False
    
    # 測試 2: 無效的 source
    print("\n📋 情況 2: 無效的 source 參數")
    try:
        response = requests.get(f"{BASE_URL}/api/get_cards", 
                               params={'source': 'invalid', 'keyword': 'test'}, 
                               timeout=5)
        data = response.json()
        print(f"   狀態碼: {response.status_code}")
        print(f"   錯誤: {data.get('error')}")
        test2_pass = response.status_code == 400
    except Exception as e:
        print(f"   ❌ 請求失敗: {str(e)}")
        test2_pass = False
    
    # 測試 3: 缺少 keyword
    print("\n📋 情況 3: 缺少 keyword 參數")
    try:
        response = requests.get(f"{BASE_URL}/api/get_cards", 
                               params={'source': 'pokemon'}, 
                               timeout=5)
        data = response.json()
        print(f"   狀態碼: {response.status_code}")
        print(f"   錯誤: {data.get('error')}")
        test3_pass = response.status_code == 400
    except Exception as e:
        print(f"   ❌ 請求失敗: {str(e)}")
        test3_pass = False
    
    return test1_pass and test2_pass and test3_pass

def main():
    """運行所有測試"""
    print("\n" + "="*60)
    print("🎴 後端 Proxy 路由測試套件")
    print("="*60)
    print(f"📍 測試 URL: {BASE_URL}")
    print(f"⏰ 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'Pokemon TCG': test_pokemon_api(),
        'YuGiOh': test_yugioh_api(),
        'Magic: The Gathering': test_mtg_api(),
        '錯誤處理': test_error_handling(),
    }
    
    # 總結
    print_header("📊 測試結果總結")
    pass_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{status} - {test_name}")
    
    print(f"\n📈 成功率: {pass_count}/{total_count} ({pass_count*100//total_count}%)")
    
    if pass_count == total_count:
        print("\n🎉 所有測試通過！後端 Proxy 路由正常工作。")
        return 0
    else:
        print("\n⚠️ 有些測試失敗。請檢查以下內容:")
        print("   1. Flask 應用是否正在運行?")
        print("   2. 網路連接是否正常?")
        print("   3. 第三方 API 是否可訪問?")
        return 1

if __name__ == '__main__':
    # 檢查 Flask 應用是否運行
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"\n✅ Flask 應用已啟動 (狀態碼: {response.status_code})\n")
    except Exception as e:
        print(f"\n❌ 無法連接到 Flask 應用: {str(e)}")
        print(f"請先運行: python app.py\n")
        sys.exit(1)
    
    # 運行測試
    exit_code = main()
    sys.exit(exit_code)
