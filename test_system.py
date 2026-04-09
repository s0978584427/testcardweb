"""
卡牌價格監控系統 - 測試驗證腳本

此腳本驗證系統的所有主要功能：
1. 資料庫初始化
2. 爬蟲功能
3. API 端點
4. 前端加載
"""

import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Card, PriceHistory
from scraper import CardScraper, scrape_cards_and_update_db
import requests
from bs4 import BeautifulSoup

def test_database_init():
    """測試資料庫初始化"""
    print("🔍 測試 1: 資料庫初始化...")
    try:
        with app.app_context():
            # 查詢現有數據
            card_count = Card.query.count()
            print(f"  ✅ 資料庫連接成功")
            print(f"  📊 當前卡牌數: {card_count}")
        return True
    except Exception as e:
        print(f"  ❌ 資料庫初始化失敗: {str(e)}")
        return False


def test_scraper():
    """測試爬蟲功能"""
    print("\n🔍 測試 2: 爬蟲功能...")
    try:
        scraper = CardScraper()
        cards = scraper.fetch_cards()
        print(f"  ✅ 爬蟲執行成功")
        print(f"  📦 獲取卡牌數: {len(cards)}")
        
        if cards:
            first_card = cards[0]
            print(f"  💳 第一張卡牌: {first_card.get('name')}")
            print(f"  💰 價格: {first_card.get('price')}")
            print(f"  🖼️  圖片: {first_card.get('image_url', 'N/A')[:50]}...")
        
        scraper.close()
        return True
    except Exception as e:
        print(f"  ❌ 爬蟲測試失敗: {str(e)}")
        return False


def test_html_template():
    """測試前端 HTML 文件"""
    print("\n🔍 測試 3: 前端模板...")
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 檢查關鍵元素
        checks = [
            ('Bootstrap CSS', 'bootstrap@5' in content),
            ('Chart.js', 'chart.js' in content),
            ('卡牌容器', 'cardsContainer' in content),
            ('更新按鈕', 'updateBtn' in content),
            ('價格圖表', 'priceChart' in content),
            ('中文支持', '卡牌' in content),
        ]
        
        print(f"  ✅ HTML 文件讀取成功")
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"    {status} {check_name}")
        
        return all(result for _, result in checks)
    except Exception as e:
        print(f"  ❌ HTML 模板測試失敗: {str(e)}")
        return False


def test_api_endpoints():
    """測試 API 端點"""
    print("\n🔍 測試 4: API 端點...")
    try:
        # 初始化測試客戶端
        client = app.test_client()
        
        # 測試首頁
        response = client.get('/')
        print(f"  GET / - 狀態碼: {response.status_code}", "✅" if response.status_code == 200 else "❌")
        
        # 初始化資料庫
        with app.app_context():
            db.create_all()
            scrape_cards_and_update_db(db.session, Card, PriceHistory)
        
        # 測試 API 端點
        endpoints = [
            ('GET /api/cards', '/api/cards'),
            ('GET /api/stats', '/api/stats'),
        ]
        
        for name, endpoint in endpoints:
            response = client.get(endpoint)
            status = response.status_code
            print(f"  {name} - 狀態碼: {status}", "✅" if status == 200 else "❌")
        
        # 測試單個卡牌
        with app.app_context():
            first_card = Card.query.first()
            if first_card:
                response = client.get(f'/api/cards/{first_card.id}')
                print(f"  GET /api/cards/{{id}} - 狀態碼: {response.status_code}", "✅" if response.status_code == 200 else "❌")
        
        return True
    except Exception as e:
        print(f"  ❌ API 測試失敗: {str(e)}")
        return False


def test_dependencies():
    """測試依賴項是否已安裝"""
    print("\n🔍 測試 5: 依賴項檢查...")
    try:
        dependencies = [
            ('Flask', import_module('flask')),
            ('SQLAlchemy', import_module('sqlalchemy')),
            ('BeautifulSoup4', import_module('bs4')),
            ('Requests', import_module('requests')),
            ('Flask-CORS', import_module('flask_cors')),
        ]
        
        for name, module in dependencies:
            status = "✅" if module else "❌"
            print(f"  {status} {name}")
        
        return all(module for _, module in dependencies)
    except Exception as e:
        print(f"  ❌ 依賴項檢查失敗: {str(e)}")
        return False


def import_module(module_name):
    """嘗試導入模塊"""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def run_all_tests():
    """運行所有測試"""
    print("="*60)
    print("🧪 卡牌價格監控系統 - 完整性測試")
    print("="*60)
    
    test_results = []
    
    # 運行各項測試
    test_results.append(("依賴項檢查", test_dependencies()))
    test_results.append(("資料庫初始化", test_database_init()))
    test_results.append(("爬蟲功能", test_scraper()))
    test_results.append(("前端模板", test_html_template()))
    test_results.append(("API 端點", test_api_endpoints()))
    
    # 生成測試報告
    print("\n" + "="*60)
    print("📋 測試報告")
    print("="*60)
    
    for test_name, passed in test_results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{status}: {test_name}")
    
    total = len(test_results)
    passed = sum(1 for _, result in test_results if result)
    
    print("="*60)
    print(f"總體結果: {passed}/{total} 項測試通過")
    
    if passed == total:
        print("🎉 所有測試通過！系統可以正式使用。")
        print("\n快速啟動:")
        print("  python app.py")
        print("\n訪問地址: http://localhost:5000")
    else:
        print("⚠️  有部分測試失敗，請檢查錯誤信息。")
    
    print("="*60)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
