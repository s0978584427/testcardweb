"""測試各平台爬蟲"""
from scraper import CardScraper

scraper = CardScraper()

print("\n" + "="*80)
print("【Ruten 露天拍賣】")
print("="*80)
ruten_results = scraper.scrape_ruten('卡牌', limit=5)
if ruten_results:
    r = ruten_results[0]
    print(f"✓ 標題: {r['title']}")
    print(f"✓ 價格: {r['price']} 元")
    print(f"✓ 圖片: {r['img_url']}")
else:
    print("✗ 未取得商品")

print("\n" + "="*80)
print("【Shopee 蝦皮】")
print("="*80)
shopee_results = scraper.scrape_shopee('卡牌', limit=5)
if shopee_results:
    r = shopee_results[0]
    print(f"✓ 標題: {r['title']}")
    print(f"✓ 價格: {r['price']} 元")
    print(f"✓ 圖片: {r['img_url']}")
else:
    print("✗ 未取得商品 (反爬蟲保護)")

print("\n" + "="*80)
print("【Yahoo 奇摩拍賣】")
print("="*80)
yahoo_results = scraper.scrape_yahoo('卡牌', limit=5)
if yahoo_results:
    r = yahoo_results[0]
    print(f"✓ 標題: {r['title']}")
    print(f"✓ 價格: {r['price']} 元")
    print(f"✓ 圖片: {r['img_url']}")
else:
    print("✗ 未取得商品 (JavaScript 動態渲染)")

print("\n" + "="*80)
print("【PChome 24h】")
print("="*80)
pchome_results = scraper.scrape_pchome('卡牌', limit=5)
if pchome_results:
    r = pchome_results[0]
    print(f"✓ 標題: {r['title']}")
    print(f"✓ 價格: {r['price']} 元")
    print(f"✓ 圖片: {r['img_url']}")
else:
    print("✗ 未取得商品")

print("\n" + "="*80)
print("測試完成")
print("="*80)
