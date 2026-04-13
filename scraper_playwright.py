"""
使用 Playwright 的增強爬蟲 - 支持 JavaScript 動態渲染
適用於: Shopee, Ruten, Yahoo
"""
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import quote
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_ruten_playwright(keyword: str, limit: int = 10) -> List[Dict]:
    """
    使用 Playwright 爬取 Ruten 商品
    """
    logger.info(f"[Ruten Playwright] 開始爬蟲: {keyword}")
    results = []
    
    try:
        with sync_playwright() as p:
            # 啟動瀏覽器
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # 設定超時
            page.set_default_timeout(15000)
            
            # 訪問頁面
            url = f"https://www.ruten.com.tw/find/?q={quote(keyword)}"
            logger.info(f"[Ruten Playwright] 訪問: {url}")
            
            page.goto(url, wait_until='networkidle')
            
            # 等待商品列表加載
            try:
                page.wait_for_selector('li.item, li.good, [class*="product-item"]', timeout=5000)
            except:
                logger.warning("[Ruten Playwright] 無法找到商品列表")
                browser.close()
                return results
            
            # 提取商品信息（延遲以確保 JavaScript 執行）
            time.sleep(2)
            
            # 查找所有商品
            items = page.locator('li.item, li.good, [class*="product"]').all()
            
            for item in items[:limit]:
                try:
                    # 提取標題
                    title_elem = item.locator('h3, h4, a').first
                    title = title_elem.text_content().strip() if title_elem else ''
                    
                    # 提取價格
                    price_text = item.locator('span[class*="price"], div[class*="price"]').first.text_content() if item.locator('span[class*="price"]').count() > 0 else ''
                    
                    # 解析價格
                    price = 0
                    if price_text:
                        digits = ''.join(filter(str.isdigit, price_text))
                        price = int(digits) if digits else 0
                    
                    # 提取圖片
                    img_elem = item.locator('img').first
                    img_src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ''
                    
                    # 修復相對 URL
                    if img_src and not img_src.startswith('http'):
                        img_src = f'https://www.ruten.com.tw{img_src}' if img_src.startswith('/') else f'https:{img_src}' if img_src.startswith('//') else ''
                    
                    if title and price > 0 and img_src:
                        results.append({
                            'title': title[:200],
                            'price': price,
                            'img_url': img_src,
                            'platform': 'ruten'
                        })
                        logger.info(f"[Ruten Playwright] 抓取: {title} - {price}")
                
                except Exception as e:
                    logger.debug(f"[Ruten Playwright] 商品解析失敗: {e}")
                    continue
            
            browser.close()
            logger.info(f"[Ruten Playwright] 成功抓取 {len(results)} 個商品")
    
    except Exception as e:
        logger.error(f"[Ruten Playwright] 爬蟲失敗: {e}")
    
    return results


def scrape_shopee_playwright(keyword: str, limit: int = 10) -> List[Dict]:
    """
    使用 Playwright 爬取 Shopee 商品 (隱身模式)
    """
    logger.info(f"[Shopee Playwright] 開始爬蟲: {keyword}")
    results = []
    
    try:
        with sync_playwright() as p:
            # 啟動瀏覽器 (隱身模式以避免追蹤)
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1366, 'height': 768}
            )
            
            # 設定超時和額外延遲
            page.set_default_timeout(20000)
            
            # 訪問搜尋頁面
            url = f"https://shopee.tw/search?keyword={quote(keyword)}"
            logger.info(f"[Shopee Playwright] 訪問: {url}")
            
            # 添加延遲以避免被偵測
            time.sleep(2)
            page.goto(url, wait_until='networkidle')
            
            # 等待商品加載
            try:
                page.wait_for_selector('[data-testid="product-item"], [class*="product"]', timeout=8000)
            except:
                logger.warning("[Shopee Playwright] 無法找到商品列表")
                browser.close()
                return results
            
            # 額外延遲確保內容完全加載
            time.sleep(3)
            
            # 提取商品信息
            items = page.locator('[data-testid="product-item"], [class*="product"]').all()
            
            for item in items[:limit]:
                try:
                    # 提取標題
                    name_elem = item.locator('[class*="name"], h2, a').first
                    title = name_elem.text_content().strip() if name_elem else ''
                    
                    # 提取價格
                    price_elems = item.locator('[class*="price"]').all()
                    price = 0
                    if price_elems:
                        price_text = price_elems[-1].text_content()  # 通常最後一個是實際價格
                        digits = ''.join(filter(str.isdigit, price_text))
                        price = int(digits) if digits else 0
                    
                    # 提取圖片
                    img_elem = item.locator('img').first
                    img_src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ''
                    
                    if title and price > 0:
                        results.append({
                            'title': title[:200],
                            'price': price,
                            'img_url': img_src or '',
                            'platform': 'shopee'
                        })
                        logger.info(f"[Shopee Playwright] 抓取: {title} - {price}")
                
                except Exception as e:
                    logger.debug(f"[Shopee Playwright] 商品解析失敗: {e}")
                    continue
            
            browser.close()
            logger.info(f"[Shopee Playwright] 成功抓取 {len(results)} 個商品")
    
    except Exception as e:
        logger.error(f"[Shopee Playwright] 爬蟲失敗: {e}")
    
    return results


def scrape_yahoo_playwright(keyword: str, limit: int = 10) -> List[Dict]:
    """
    使用 Playwright 爬取 Yahoo 奇摩拍賣商品
    """
    logger.info(f"[Yahoo Playwright] 開始爬蟲: {keyword}")
    results = []
    
    try:
        with sync_playwright() as p:
            # 啟動瀏覽器
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # 設定超時
            page.set_default_timeout(15000)
            
            # 訪問搜尋頁面
            url = f"https://tw.bid.yahoo.com/search/auction/product?p={quote(keyword)}"
            logger.info(f"[Yahoo Playwright] 訪問: {url}")
            
            page.goto(url, wait_until='networkidle')
            
            # 等待商品加載
            try:
                page.wait_for_selector('[class*="product"], [class*="item"], li', timeout=8000)
            except:
                logger.warning("[Yahoo Playwright] 無法找到商品列表")
                browser.close()
                return results
            
            # 延遲確保加載完成
            time.sleep(2)
            
            # 提取所有可能的商品容器
            items = page.locator('li[data-clk*="auction"], li[class*="product"], ul li').all()
            
            for item in items[:limit]:
                try:
                    # 提取標題
                    title_elem = item.locator('h2, h3, a').first
                    title = title_elem.text_content().strip() if title_elem else ''
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # 提取價格
                    price_text = item.locator('[class*="price"]').first.text_content() if item.locator('[class*="price"]').count() > 0 else ''
                    
                    # 解析價格
                    price = 0
                    if price_text:
                        digits = ''.join(filter(str.isdigit, price_text))
                        price = int(digits) if digits else 0
                    
                    # 提取圖片
                    img_elem = item.locator('img').first
                    img_src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ''
                    
                    if title and price > 0:
                        results.append({
                            'title': title[:200],
                            'price': price,
                            'img_url': img_src or '',
                            'platform': 'yahoo'
                        })
                        logger.info(f"[Yahoo Playwright] 抓取: {title} - {price}")
                
                except Exception as e:
                    logger.debug(f"[Yahoo Playwright] 商品解析失敗: {e}")
                    continue
            
            browser.close()
            logger.info(f"[Yahoo Playwright] 成功抓取 {len(results)} 個商品")
    
    except Exception as e:
        logger.error(f"[Yahoo Playwright] 爬蟲失敗: {e}")
    
    return results


if __name__ == '__main__':
    # 測試三個平台
    print("\n=== 測試 Ruten ===")
    ruten_results = scrape_ruten_playwright('卡牌', limit=3)
    for r in ruten_results:
        print(f"  {r['title']} - {r['price']}")
    
    print("\n=== 測試 Shopee ===")
    shopee_results = scrape_shopee_playwright('卡牌', limit=3)
    for r in shopee_results:
        print(f"  {r['title']} - {r['price']}")
    
    print("\n=== 測試 Yahoo ===")
    yahoo_results = scrape_yahoo_playwright('卡牌', limit=3)
    for r in yahoo_results:
        print(f"  {r['title']} - {r['price']}")
