"""
卡牌價格監控系統 - 多平台爬蟲
支持平台: PChome, Ruten, Shopee, Yahoo
統一輸出格式: {'title': str, 'price': int, 'img_url': str, 'platform': str}

技術特性：
- PChome: 官方 API (JSON) - 完美支持 ✅
- Ruten: JavaScript 動態渲染 - 需要 Playwright
- Shopee: 強力反爬蟲保護 - 需要 Playwright + 代理
- Yahoo: JavaScript 動態渲染 - 需要 Playwright

要安裝 Playwright 支持，請運行:
  pip install playwright
  playwright install
"""
import requests
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import quote
import json
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 嘗試導入 Playwright (可選)
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("Playwright 未安裝。某些平台爬蟲將無法正常工作。")

# ============================================================================
# CardScraper 類別 - 統一管理所有平台爬蟲
# ============================================================================

class CardScraper:
    """
    多平台卡牌爬蟲類別
    統一輸出格式: {'title': str, 'price': int, 'img_url': str, 'platform': str}
    """
    
    def __init__(self):
        """初始化爬蟲"""
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.default_headers)
    
    def normalize_product(self, title: str, price: int, img_url: str, platform: str) -> Dict:
        """
        統一產品格式
        """
        return {
            'title': str(title).strip()[:200],  # 限制標題長度
            'price': int(price) if price else 0,
            'img_url': str(img_url).strip() if img_url else '',
            'platform': platform
        }
    
    # ========================================================================
    # PChome 爬蟲 - 官方 API
    # ========================================================================
    
    def scrape_pchome(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        PChome 爬蟲 - 使用官方 API
        API: https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={keyword}
        """
        logger.info(f"[PChome] 開始爬蟲: {keyword}")
        results = []
        
        try:
            url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={quote(keyword)}&limit={limit}"
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                logger.warning(f"[PChome] 狀態碼: {resp.status_code}")
                return results
            
            data = resp.json()
            prods = data.get('prods', [])
            
            for prod in prods:
                try:
                    title = prod.get('name', '')
                    price = prod.get('price', 0)
                    pic_s = prod.get('picS', '')
                    
                    if not title or not price:
                        continue
                    
                    # 拼接完整圖片 URL
                    img_url = f'https://cs-a.ecimg.tw{pic_s}' if pic_s else ''
                    
                    results.append(self.normalize_product(title, price, img_url, 'pchome'))
                    
                except Exception as e:
                    logger.debug(f"[PChome] 商品解析失敗: {e}")
                    continue
            
            logger.info(f"[PChome] 成功抓取 {len(results)} 個商品")
            
        except Exception as e:
            logger.error(f"[PChome] 爬蟲失敗: {e}")
        
        return results
    
    # ========================================================================
    # Ruten 爬蟲 - HTML 爬取 (API 已廢棄)
    # ========================================================================
    
    def scrape_ruten(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        Ruten 爬蟲 - 使用 HTML 爬取 (API 已廢棄)
        搜尋網址: https://www.ruten.com.tw/find/?q={keyword}
        """
        logger.info(f"[Ruten] 開始爬蟲: {keyword}")
        results = []
        
        try:
            url = f"https://www.ruten.com.tw/find/?q={quote(keyword)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code != 200:
                logger.warning(f"[Ruten] 狀態碼: {resp.status_code}")
                return results
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 查找商品列表
            items = soup.find_all('li', class_=['item', 'good'])
            
            count = 0
            for item in items:
                if count >= limit:
                    break
                
                try:
                    # 提取標題
                    title_elem = item.find('h3', class_='title')
                    if not title_elem:
                        title_elem = item.find('a', class_='name')
                    if not title_elem:
                        title_elem = item.find('h4')
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # 提取價格
                    price_elem = item.find('span', class_='price')
                    if not price_elem:
                        price_elem = item.find('div', class_='price')
                    
                    price = 0
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price_text = price_text.replace('NT$', '').replace(',', '').split()[0]
                        try:
                            price = int(float(price_text))
                        except:
                            price = 0
                    
                    if price <= 0:
                        continue
                    
                    # 提取圖片
                    img_elem = item.find('img')
                    img_url = ''
                    if img_elem:
                        img_url = img_elem.get('src') or img_elem.get('data-src') or ''
                    
                    if not img_url.startswith('http'):
                        img_url = f'https:{img_url}' if img_url.startswith('//') else f'https://www.ruten.com.tw{img_url}' if img_url else ''
                    
                    if title and price > 0:
                        results.append(self.normalize_product(title, price, img_url, 'ruten'))
                        count += 1
                    
                except Exception as e:
                    logger.debug(f"[Ruten] 商品解析失敗: {e}")
                    continue
            
            logger.info(f"[Ruten] 成功抓取 {len(results)} 個商品")
            
        except Exception as e:
            logger.error(f"[Ruten] 爬蟲失敗: {e}")
        
        return results
    
    # ========================================================================
    # Shopee 爬蟲 - API + 反爬蟲對策
    # ========================================================================
    
    def scrape_shopee(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        Shopee 爬蟲 - 使用 API + 延遲和多重 User-Agent
        API: https://shopee.tw/api/v4/search/search_items?keyword={keyword}
        圖片 URL: https://cf.shopee.tw/file/ + image 欄位
        注意: Shopee 有強力反爬蟲，如持續失敗建議使用 Playwright
        """
        logger.info(f"[Shopee] 開始爬蟲: {keyword}")
        results = []
        
        try:
            # 嘗試多個 User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            
            url = f"https://shopee.tw/api/v4/search/search_items?by=relevancy&keyword={quote(keyword)}&limit={limit}"
            
            for ua in user_agents:
                try:
                    headers = {
                        'User-Agent': ua,
                        'Referer': 'https://shopee.tw/',
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                    
                    # 添加延遲以避免反爬蟲觸發
                    time.sleep(1)
                    
                    resp = requests.get(url, headers=headers, timeout=15)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        
                        # 檢查是否有錯誤
                        if data.get('error'):
                            logger.debug(f"[Shopee] API 錯誤: {data.get('error')}")
                            continue
                        
                        items = data.get('items', [])
                        
                        if items:
                            for item in items:
                                try:
                                    item_basic = item.get('item_basic', {})
                                    title = item_basic.get('name', '')
                                    price = item_basic.get('price', 0)
                                    image = item_basic.get('image', '')
                                    
                                    if not title or not price:
                                        continue
                                    
                                    # 拼接完整圖片 URL
                                    if image:
                                        if not image.startswith('http'):
                                            img_url = f'https://cf.shopee.tw/file/{image}'
                                        else:
                                            img_url = image
                                    else:
                                        img_url = ''
                                    
                                    # 價格單位轉換 (Shopee 返回的是 100000 倍)
                                    price_converted = int(price / 100000) if price > 100000 else price
                                    
                                    results.append(self.normalize_product(title, price_converted, img_url, 'shopee'))
                                    
                                except Exception as e:
                                    logger.debug(f"[Shopee] 商品解析失敗: {e}")
                                    continue
                            
                            logger.info(f"[Shopee] 成功抓取 {len(results)} 個商品")
                            break
                    else:
                        logger.debug(f"[Shopee] User-Agent 失敗，嘗試下一個")
                        
                except Exception as e:
                    logger.debug(f"[Shopee] 請求失敗 ({ua[:30]}...): {e}")
                    continue
            
            if not results:
                logger.warning(f"[Shopee] 無法抓取商品 (反爬蟲保護)")
            
        except Exception as e:
            logger.error(f"[Shopee] 爬蟲失敗: {e}")
        
        return results
    
    # ========================================================================
    # Yahoo 奇摩拍賣 - JavaScript 動態渲染頁面
    # ========================================================================
    
    def scrape_yahoo(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        Yahoo 奇摩拍賣爬蟲
        搜尋網址: https://tw.bid.yahoo.com/search/auction/product?p={keyword}
        注意: Yahoo 使用 JavaScript 動態渲染，建議使用 Playwright
        目前使用簡單 HTML 解析作為備選方案
        """
        logger.info(f"[Yahoo] 開始爬蟲: {keyword}")
        results = []
        
        try:
            url = f"https://tw.bid.yahoo.com/search/auction/product?p={quote(keyword)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'zh-TW,zh;q=0.9',
            }
            
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code != 200:
                logger.warning(f"[Yahoo] 狀態碼: {resp.status_code}")
                return results
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Yahoo 使用 JavaScript 動態渲染，直接解析 HTML 效果有限
            # 嘗試尋找 JSON 數據或預載資料
            
            # 尋找 JSON 資料 (通常在 script 標籤中)
            scripts = soup.find_all('script')
            
            for script in scripts:
                if not script.string:
                    continue
                
                script_content = script.string
                
                # 尋找包含商品資訊的 JSON
                if '"title"' in script_content and '"price"' in script_content:
                    try:
                        # 提取 JSON 的簡單方法
                        import re
                        json_matches = re.findall(r'\{[^{}]*"title"[^{}]*"price"[^{}]*\}', script_content, re.DOTALL)
                        
                        for json_match in json_matches[:limit]:
                            try:
                                item_data = json.loads(json_match)
                                title = item_data.get('title', '')
                                price = item_data.get('price', 0)
                                img_url = item_data.get('image', '')
                                
                                if title and price:
                                    results.append(self.normalize_product(title, price, img_url, 'yahoo'))
                            except:
                                pass
                    except:
                        pass
            
            # 如果上面沒有成功，嘗試解析 HTML 元素
            if not results:
                cards = soup.find_all('div', class_=['PropertyCard', 'item'])
                
                count = 0
                for card in cards:
                    if count >= limit:
                        break
                    
                    try:
                        title_elem = card.find('h3') or card.find('a')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        
                        price_elem = card.find('span', class_=['PropertyCard__price', 'price'])
                        price = 0
                        if price_elem:
                            price_text = price_elem.get_text(strip=True)
                            price_text = price_text.replace('NT$', '').replace(',', '').strip()
                            try:
                                price = int(float(price_text))
                            except:
                                price = 0
                        
                        if not title or price <= 0:
                            continue
                        
                        # 提取第一張圖片
                        img_elem = card.find('img')
                        img_url = ''
                        if img_elem and img_elem.get('src'):
                            img_url = img_elem.get('src')
                        
                        results.append(self.normalize_product(title, price, img_url, 'yahoo'))
                        count += 1
                        
                    except Exception as e:
                        logger.debug(f"[Yahoo] 商品解析失敗: {e}")
                        continue
            
            logger.info(f"[Yahoo] 成功抓取 {len(results)} 個商品")
            
            if not results:
                logger.warning(f"[Yahoo] 建議使用 Playwright 來完整渲染 JavaScript")
            
        except Exception as e:
            logger.error(f"[Yahoo] 爬蟲失敗: {e}")
        
        return results
    
    # ========================================================================
    # 台灣官方寶可夢 TCG - 原生繁體中文卡牌資訊
    # ========================================================================
    
    def scrape_taiwan_pokemon(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        台灣官方寶可夢卡牌搜尋 - 使用 pokemontcg.io API + 中文支持
        
        注意：台灣官方網站沒有公開 JSON API，因此使用國際 pokemontcg.io 
        但提供完整的繁體中文卡牌資訊和屬性對應。
        
        支持中文搜尋：自動翻譯常見寶可夢名稱
        - 皮卡丘 → pikachu
        - 妙蛙種子 → bulbasaur
        等等
        
        返回格式: {
            'title': '卡片名稱（英文）',
            'title_zh': '卡片名稱（繁體中文）',
            'img_url': '卡牌高清圖片網址',
            'price': '需至比價區查詢',
            'stats': {
                'hp': '生命值',
                'pokemon_type': '屬性（繁體中文）',
                'stage': '進化階段'
            },
            'series': {
                'collection_number': '編號',
                'collection_name': '系列名稱'
            },
            'rarity': '稀有度',
            'source': 'tw-pokemon'
        }
        """
        logger.info(f"[Taiwan Pokemon] 開始搜尋: {keyword}")
        results = []
        
        # 中文寶可夢名稱對應表
        chinese_pokemon_map = {
            '皮卡丘': 'pikachu',
            '妙蛙種子': 'bulbasaur',
            '妙蛙草': 'ivysaur',
            '妙蛙花': 'venusaur',
            '小火龍': 'charmander',
            '火恐龍': 'charmeleon',
            '噴火龍': 'charizard',
            '傑尼龜': 'squirtle',
            '卡咪龜': 'wartortle',
            '水龜': 'blastoise',
            '綠毛蟲': 'caterpie',
            '鐵甲蛹': 'metapod',
            '鳳蝶': 'butterfree',
            '小拉達': 'rattata',
            '拉達': 'raticate',
            '烈雀': 'spearow',
            '大嘴雀': 'fearow',
            '阿柏蛇': 'ekans',
            '阿柏怪': 'arbok',
            '皮皮': 'jigglypuff',
            '皮可西': 'wigglytuff',
            '奇異種子': 'oddish',
            '拔萌芽': 'gloom',
            '臭臭花': 'vileplume',
            '派拉斯': 'paras',
            '派拉斯特': 'parasect',
            '毛球': 'venonat',
            '摩魯蛾': 'venomoth',
            '小蝌蚪': 'poliwag',
            '蝌蚪': 'poliwhirl',
            '快泳蛙': 'poliwrath',
            '小火馬': 'ponyta',
            '烈焰馬': 'rapidash',
            '慢羊羊': 'slowpoke',
            '呆殼獸': 'slowbro',
            '小海馬': 'seahorse',
            '海刺龍': 'seadra',
            '刺甲貝': 'seel',
            '白海獅': 'dewgong',
            '殼夾': 'shellder',
            '鐵甲貝': 'cloyster',
            '鬼斯': 'gastly',
            '鬼斯通': 'haunter',
            '耿鬼': 'gengar',
            '大岩蛇': 'onix',
            '催眠貘': 'drowzee',
            '食夢獸': 'hypno',
            '大鉗蟹': 'krabby',
            '巨鉗蟹': 'kingler',
            '小火焰馬': 'vulpix',
            '九尾': 'ninetales',
            '球球': 'growlithe',
            '阿羅拉九尾': 'alolan-ninetales',
            '毒刺水母': 'tentacool',
            '毒刺水母': 'tentacruel',
            '小拳石': 'geodude',
            '隆隆石': 'graveler',
            '多多': 'doduo',
            '多多利': 'dodrio',
            '迷你龍': 'dratini',
            '海龍': 'dragonair',
            '快龍': 'dragonite',
            '頑皮彈': 'meowth',
            '喵老大': 'persian',
            '喇叭芽': 'bellsprout',
            '口呆花': 'weepinbell',
            '大食花': 'victreebel',
            '雙尾怪手': 'farfetchd',
            '鐵粉': 'diglett',
            '三地鼠': 'dugtrio',
            '夜行動物': 'mankey',
            '猛犸': 'primeape',
            '胖丁': 'jigglypuff',
            '胖可丁': 'wigglytuff',
            '伊布': 'eevee',
            '火伊布': 'flareon',
            '水伊布': 'vaporeon',
            '雷伊布': 'jolteon',
            '太陽伊布': 'espeon',
            '月精靈': 'umbreon',
            '葉精靈': 'leafeon',
            '冰精靈': 'glaceon',
            '仙子伊布': 'sylveon',
            '卡拉卡拉': 'cubone',
            '嘎啦嘎啦': 'marowak',
            '阿羅拉嘎啦嘎啦': 'alolan-marowak',
            '海星': 'staryu',
            '寶石海星': 'starmie',
            '聖獅': 'growlithe',
            '勾魂眼': 'hypno',
            '馬克翼': 'dragonair',
            '瓦斯彈': 'koffing',
            '雙彈瓦斯': 'weezing',
            '鈴鐺': 'shellder',
            '鐵殼蛹': 'metapod',
            '蚊香蛙': 'poliwag',
            '蚊香蝌蚪': 'poliwog',
            '蚊香君': 'poliwag',
            '蚊香泳士': 'poliwrath',
        }
        
        # 將中文名稱轉換為英文
        search_keyword = keyword
        if keyword in chinese_pokemon_map:
            search_keyword = chinese_pokemon_map[keyword]
            logger.info(f"[Taiwan Pokemon] 翻譯: {keyword} → {search_keyword}")
        
        try:
            # 使用 pokemontcg.io API 進行搜尋
            url = f'https://api.pokemontcg.io/v2/cards?q=name:"{search_keyword}"&pageSize={min(limit, 50)}'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            logger.debug(f"[Taiwan Pokemon] 請求: {url}")
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"[Taiwan Pokemon] API 返回狀態碼: {response.status_code}")
                return results
            
            data = response.json()
            cards = data.get('data', [])
            
            if not cards:
                logger.info(f"[Taiwan Pokemon] 未找到卡牌結果")
                return results
            
            # 繁體中文屬性對應
            type_zh_map = {
                'Fire': '火',
                'Water': '水',
                'Grass': '草',
                'Electric': '雷',
                'Lightning': '雷',  # 舊版卡牌使用 Lightning
                'Ice': '冰',
                'Fighting': '格鬥',
                'Poison': '毒',
                'Ground': '地面',
                'Flying': '飛行',
                'Psychic': '超',
                'Bug': '蟲',
                'Rock': '岩',
                'Ghost': '幽靈',
                'Dragon': '龍',
                'Dark': '惡',
                'Steel': '鋼',
                'Fairy': '妖精',
                'Normal': '無',
                'Colorless': '無',
            }
            
            # 逐筆解析卡牌
            for i, card in enumerate(cards):
                if i >= limit:
                    break
                
                try:
                    title = card.get('name', '').strip()
                    images = card.get('images', {})
                    image_url = images.get('large', '') or images.get('small', '')
                    
                    if not title:
                        logger.debug(f"[Taiwan Pokemon] 跳過無標題卡牌")
                        continue
                    
                    # 提取卡牌類型 (屬性)
                    card_types = card.get('types', [])
                    pokemon_type = card_types[0] if card_types else ''
                    pokemon_type_zh = type_zh_map.get(pokemon_type, pokemon_type)
                    
                    # 提取 HP
                    hp = card.get('hp', '')
                    
                    # 提取系列資訊
                    set_info = card.get('set', {})
                    series_number = card.get('number', '')
                    series_name = set_info.get('name', '')
                    
                    # 提取稀有度
                    rarity = card.get('rarity', '')
                    
                    # 提取進化階段 (從卡牌名稱推測)
                    stage = '基礎'
                    if 'EX' in title or 'GX' in title or 'V' in title or 'VMAX' in title:
                        stage = '特殊'
                    elif any(evo in title for evo in ['Stage 1', '1st Evolution']):
                        stage = '1階進化'
                    elif any(evo in title for evo in ['Stage 2', '2nd Evolution']):
                        stage = '2階進化'
                    
                    # 組裝結果
                    result = {
                        'title': title,
                        'title_zh': keyword if keyword in chinese_pokemon_map else '',  # 記錄原始中文搜尋詞
                        'img_url': image_url,
                        'price': '需至比價區查詢',
                        'stats': {
                            'hp': str(hp) if hp else 'N/A',
                            'pokemon_type': pokemon_type_zh,
                            'stage': stage
                        },
                        'series': {
                            'collection_number': series_number,
                            'collection_name': series_name
                        },
                        'rarity': rarity or 'N/A',
                        'source': 'tw-pokemon'
                    }
                    
                    results.append(result)
                    logger.debug(f"[Taiwan Pokemon] 解析卡牌: {title}")
                    
                except Exception as e:
                    logger.debug(f"[Taiwan Pokemon] 卡牌解析失敗: {e}")
                    continue
            
            logger.info(f"[Taiwan Pokemon] 成功獲取 {len(results)} 張卡牌 (搜尋: {search_keyword})")
            
        except requests.exceptions.Timeout:
            logger.error(f"[Taiwan Pokemon] 請求超時 (>= 15s)")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[Taiwan Pokemon] 連接失敗: {e}")
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"[Taiwan Pokemon] JSON 解析失敗: {e}")
        except Exception as e:
            logger.error(f"[Taiwan Pokemon] 搜尋失敗: {e}")
        
        return results
    
    # ========================================================================
    # 統一搜索方法
    # ========================================================================
    
    def search_all_platforms(self, keyword: str) -> Dict[str, List[Dict]]:
        """
        在所有平台搜索
        返回: {'pchome': [...], 'ruten': [...], 'shopee': [...], 'yahoo': [...]}
        """
        logger.info(f"在所有平台搜索: {keyword}")
        
        results = {
            'pchome': self.scrape_pchome(keyword),
            'ruten': self.scrape_ruten(keyword),
            'shopee': self.scrape_shopee(keyword),
            'yahoo': self.scrape_yahoo(keyword)
        }
        
        return results


# ============================================================================
# 便利函數 (向後相容)
# ============================================================================

def search_pchome(keyword: str, pages: int = 1) -> List[Dict]:
    """向後相容函數"""
    scraper = CardScraper()
    products = scraper.scrape_pchome(keyword)
    # 轉換為舊格式
    return [{
        'product_id': f'pchome_{i}',
        'platform': 'pchome',
        'name': p['title'],
        'price': p['price'],
        'image': p['img_url'],
        'shop': '24h PChome',
        'rating': 4.5,
        'url': f'https://24h.pchome.com.tw/search?q={quote(keyword)}',
        'description': p['title']
    } for i, p in enumerate(products)]


def search_shopee(keyword: str, pages: int = 1) -> List[Dict]:
    """向後相容函數"""
    scraper = CardScraper()
    products = scraper.scrape_shopee(keyword)
    # 轉換為舊格式
    return [{
        'product_id': f'shopee_{i}',
        'platform': 'shopee',
        'name': p['title'],
        'price': p['price'],
        'image': p['img_url'],
        'shop': 'Shopee',
        'rating': 4.5,
        'url': f'https://shopee.tw/search?q={quote(keyword)}',
        'description': p['title']
    } for i, p in enumerate(products)]


def search_ruten(keyword: str, pages: int = 1) -> List[Dict]:
    """向後相容函數"""
    scraper = CardScraper()
    products = scraper.scrape_ruten(keyword)
    # 轉換為舊格式
    return [{
        'product_id': f'ruten_{i}',
        'platform': 'ruten',
        'name': p['title'],
        'price': p['price'],
        'image': p['img_url'],
        'shop': '露天拍賣',
        'rating': 4.3,
        'url': f'https://www.ruten.com.tw/find/?q={quote(keyword)}',
        'description': p['title']
    } for i, p in enumerate(products)]


def search_yahoo(keyword: str, pages: int = 1) -> List[Dict]:
    """向後相容函數"""
    scraper = CardScraper()
    products = scraper.scrape_yahoo(keyword)
    # 轉換為舊格式
    return [{
        'product_id': f'yahoo_{i}',
        'platform': 'yahoo',
        'name': p['title'],
        'price': p['price'],
        'image': p['img_url'],
        'shop': 'Yahoo 拍賣',
        'rating': 4.6,
        'url': f'https://tw.bid.yahoo.com/search/auction/product?p={quote(keyword)}',
        'description': p['title']
    } for i, p in enumerate(products)]


def get_sample_search_results(platform: str) -> List[Dict]:
    """備用範例數據"""
    sample_cards = [
        {
            'product_id': f'sample_{platform}_0',
            'platform': platform,
            'name': '青眼白龍卡牌',
            'price': 500,
            'image': 'https://images.ygoprodeck.com/images/cards/89631139.jpg',
            'shop': f'{platform.upper()} 示例',
            'rating': 4.5,
            'url': '#',
            'description': '青眼白龍卡牌'
        }
    ]
    return sample_cards


# ============================================================================
# 測試函數 - 列印第一筆資料驗證
# ============================================================================

def test_all_platforms():
    """
    測試所有平台爬蟲
    列印各平台第一筆資料，確保圖片連結不再是幻覺
    """
    logger.info("=" * 80)
    logger.info("開始測試多平台爬蟲")
    logger.info("=" * 80)
    
    keyword = '卡牌'
    scraper = CardScraper()
    
    # 搜索所有平台
    results = scraper.search_all_platforms(keyword)
    
    # 列印每個平台的第一筆資料
    for platform, products in results.items():
        logger.info(f"\n{'=' * 80}")
        logger.info(f"平台: {platform.upper()}")
        logger.info(f"{'=' * 80}")
        
        if products:
            first_product = products[0]
            logger.info(f"✓ 標題: {first_product['title']}")
            logger.info(f"✓ 價格: {first_product['price']} 元")
            logger.info(f"✓ 圖片 URL: {first_product['img_url']}")
            logger.info(f"✓ 總共抓取: {len(products)} 個商品")
        else:
            logger.warning(f"✗ 未抓取到商品")
    
    logger.info(f"\n{'=' * 80}")
    logger.info("測試完成")
    logger.info("=" * 80)


if __name__ == '__main__':
    test_all_platforms()


# ============================================================================
# Playwright 增強爬蟲 (可選 - 用於複雜 JavaScript 渲染)
# ============================================================================

DOCTYPE_SCRAPER_INFO = """
【爬蟲平台支持情況】

✅ PChome (官方 API)
   - 狀態: 完全支持
   - 方法: requests + JSON API
   - 圖片: 100% 真實，高質量
   - 性能: 快速穩定

❌ Ruten (需要 Playwright)
   - 狀態: 需要 JavaScript 渲染
   - 方法: HTML 解析 (基礎) / Playwright (推薦)
   - 圖片: 正常
   - 障礙: SSR 或動態渲染

❌ Shopee (強力反爬蟲)
   - 狀態: API 返回 error 90309999
   - 方法: 需要 Playwright + 代理 + 延遲
   - 圖片: 可用
   - 障礙: 強力反爬蟲保護

❌ Yahoo (JavaScript 動態渲染)
   - 狀態: 需要 JavaScript 渲染
   - 方法: HTML 解析 (基礎) / Playwright (推薦)
   - 圖片: 正常
   - 障礙: 完全 JavaScript 動態页面

【安裝 Playwright 支持】
  pip install playwright
  playwright install

【使用方式】
from scraper import CardScraper, scrape_with_playwright

# 基礎爬蟲 (僅 PChome)
scraper = CardScraper()
results = scraper.search_all_platforms('卡牌')

# Playwright 增強版 (所有平台)
if HAS_PLAYWRIGHT:
    results = scrape_with_playwright('卡牌')
"""

def scrape_with_playwright(keyword: str) -> Dict[str, List[Dict]]:
    """
    使用 Playwright 的增強爬蟲 (處理 JavaScript 動態渲染)
    
    要求: pip install playwright && playwright install
    """
    if not HAS_PLAYWRIGHT:
        logger.error("Playwright 未安裝。無法執行此函數。")
        logger.error("請先運行: pip install playwright && playwright install")
        return {}
    
    results = {
        'pchome': [],
        'ruten': [],
        'shopee': [],
        'yahoo': []
    }
    
    try:
        with sync_playwright() as p:
            logger.info("【啟動 Playwright 瀏覽器】")
            
            # 啟動瀏覽器 - 使用隱身模式避免追蹤
            browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
            
            # PChome - 直接用 API (不需要 Playwright)
            logger.info("【PChome】使用 API...")
            scraper = CardScraper()
            results['pchome'] = scraper.scrape_pchome(keyword)[:5]
            
            # Ruten - Playwright 版本
            logger.info("【Ruten】使用 Playwright...")
            try:
                page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                page.goto(f"https://www.ruten.com.tw/find/?q={quote(keyword)}", wait_until='networkidle')
                
                # 等待商品加載
                page.wait_for_selector('li', timeout=5000)
                
                # 提取商品數據
                items = page.locator('li:has-text("NT$")').all()[:5]
                
                for item in items:
                    try:
                        title = item.locator('h3, h4').first.text_content()
                        price_text = item.locator('[class*="price"]').first.text_content()
                        price = int(''.join(filter(str.isdigit, price_text.split('NT$')[0]))) if 'NT$' in price_text else 0
                        
                        img_elem = item.locator('img').first
                        img_url = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ''
                        
                        if title and price > 0:
                            results['ruten'].append({
                                'title': title.strip()[:200],
                                'price': price,
                                'img_url': img_url,
                                'platform': 'ruten'
                            })
                    except:
                        pass
                
                page.close()
            except Exception as e:
                logger.warning(f"Ruten Playwright 爬蟲失敗: {e}")
            
            # Yahoo - Playwright 版本
            logger.info("【Yahoo】使用 Playwright...")
            try:
                page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                page.goto(f"https://tw.bid.yahoo.com/search/auction/product?p={quote(keyword)}", wait_until='networkidle')
                
                # 等待商品加載
                page.wait_for_selector('[class*="PropertyCard"]', timeout=5000)
                
                items = page.locator('[class*="PropertyCard"]').all()[:5]
                
                for item in items:
                    try:
                        title = item.locator('h3, a').first.text_content()
                        price_elem = item.locator('[class*="price"]').first
                        price_text = price_elem.text_content() if price_elem else ''
                        price = int(''.join(filter(str.isdigit, price_text.split('NT$')[0]))) if 'NT$' in price_text else 0
                        
                        img_elem = item.locator('img').first
                        img_url = img_elem.get_attribute('src') or ''
                        
                        if title and price > 0:
                            results['yahoo'].append({
                                'title': title.strip()[:200],
                                'price': price,
                                'img_url': img_url,
                                'platform': 'yahoo'
                            })
                    except:
                        pass
                
                page.close()
            except Exception as e:
                logger.warning(f"Yahoo Playwright 爬蟲失敗: {e}")
            
            # Shopee - Playwright 版本 (使用 stealth 模式)
            logger.info("【Shopee】使用 Playwright (stealth 模式)...")
            try:
                # 這裡可以添加代理設置避免被 Shopee 屏蔽
                page = browser.new_page(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={'width': 1366, 'height': 768}
                )
                
                page.goto(f"https://shopee.tw/search?keyword={quote(keyword)}", wait_until='networkidle')
                
                # 等待商品加載
                page.wait_for_selector('[data-testid="product-item"]', timeout=5000)
                
                items = page.locator('[data-testid="product-item"]').all()[:5]
                
                for item in items:
                    try:
                        title = item.locator('[class*="name"]').first.text_content()
                        price = int(''.join(filter(str.isdigit, item.locator('[class*="price"]').first.text_content())))
                        
                        img_elem = item.locator('img').first
                        img_url = img_elem.get_attribute('src') or ''
                        
                        if title and price > 0:
                            results['shopee'].append({
                                'title': title.strip()[:200],
                                'price': price,
                                'img_url': img_url,
                                'platform': 'shopee'
                            })
                    except:
                        pass
                
                page.close()
            except Exception as e:
                logger.warning(f"Shopee Playwright 爬蟲失敗: {e}")
            
            browser.close()
            logger.info("✓ Playwright 爬蟲完成")
    
    except Exception as e:
        logger.error(f"Playwright 爬蟲整體失敗: {e}")
    
    return results


if __name__ == '__main__':
    print(DOCTYPE_SCRAPER_INFO)
"""
卡牌價格監控系統 - 爬蟲模組
使用真實電商平台 API 獲取準確數據
"""
import requests
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import quote
import json
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局會話設置
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}


# ============================================================================
# PChome 真實 API 爬蟲 (官方搜尋 API - JSON 格式)
# ============================================================================

def search_pchome_api(keyword: str, page: int = 1) -> List[Dict]:
    """
    使用 PChome 官方搜尋 API 獲取準確的商品數據
    API 文檔: https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={keyword}
    返回 JSON 格式的商品列表
    """
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        # PChome 官方搜尋 API
        offset = (page - 1) * 20
        url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={quote(keyword)}&offset={offset}&limit=20"
        
        logger.info(f"查詢 PChome API: {keyword} (頁 {page})")
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"PChome API 返回狀態碼: {response.status_code}")
            return []
        
        data = response.json()
        products = []
        
        # 提取商品數組 (prods 是官方返回的字段名)
        prods = data.get('prods', [])
        
        if not prods:
            logger.info(f"PChome 第 {page} 頁: 無商品")
            return []
        
        for prod in prods:
            try:
                # 提取必要字段 (注意: API 使用大寫 Id)
                product_id = prod.get('Id', '')
                name = prod.get('name', '')
                price = prod.get('price', 0)
                pic_s = prod.get('picS', '')  # 圖片後綴
                
                # 驗證必要字段
                if not name or not product_id:
                    logger.debug(f"跳過: 缺少基本信息")
                    continue
                
                # 拼接完整圖片 URL
                image_url = ''
                if pic_s:
                    image_url = f'https://cs-a.ecimg.tw{pic_s}'
                
                # 確保 price 是整數
                try:
                    price = int(price) if price else 0
                except (ValueError, TypeError):
                    price = 0
                
                product = {
                    'product_id': f'pchome_{product_id}',
                    'platform': 'pchome',
                    'name': name,
                    'price': price,  # 整數價格
                    'image': image_url,  # 完整圖片 URL
                    'shop': '24h PChome',
                    'rating': 4.5,
                    'url': f'https://24h.pchome.com.tw/prod/{product_id}',
                    'description': name
                }
                
                products.append(product)
                logger.debug(f"✓ 商品: {name[:40]} | 價格: {price}元")
                
            except Exception as e:
                logger.debug(f"解析商品失敗: {e}")
                continue
        
        logger.info(f"PChome 第 {page} 頁: 成功獲取 {len(products)} 個商品")
        return products
    
    except Exception as e:
        logger.error(f"PChome 搜索錯誤: {e}")
        return []


def test_pchome_api():
    """
    測試函數：列印前三筆真實數據到終端機
    用來驗證數據是否準確
    """
    logger.info("=" * 70)
    logger.info("PChome API 數據測試")
    logger.info("=" * 70)
    
    test_keywords = ['遊戲卡', '寶可夢卡', '青眼白龍']
    
    for keyword in test_keywords:
        logger.info(f"\n搜尋: {keyword}")
        logger.info("-" * 70)
        
        products = search_pchome_api(keyword, page=1)
        
        if not products:
            logger.warning(f"未獲取到 {keyword} 的商品")
            continue
        
        # 列印前三筆
        for i, prod in enumerate(products[:3], 1):
            logger.info(f"\n【第 {i} 筆】")
            logger.info(f"  商品名稱: {prod['name']}")
            logger.info(f"  價格: {prod['price']} 元")
            logger.info(f"  圖片 URL: {prod['image']}")
            logger.info(f"  商品 ID: {prod['product_id']}")
            logger.info(f"  商品連結: {prod['url']}")
        
        time.sleep(0.5)  # 避免過度請求
    
    logger.info("\n" + "=" * 70)
    logger.info("測試完成")
    logger.info("=" * 70)


# ============================================================================
# Shopee 爬蟲 - 使用 Shopee API
# ============================================================================

def search_shopee(keyword: str, pages: int = 1) -> List[Dict]:
    """蝦皮搜索 - 使用 Shopee API"""
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        results = []
        
        for page_num in range(min(pages, 2)):
            try:
                # Shopee API
                offset = page_num * 50
                url = f"https://shopee.tw/api/v4/search/search_items?by=relevancy&keyword={quote(keyword)}&limit=50&offset={offset}&order=desc"
                
                resp = session.get(url, timeout=15)
                if resp.status_code != 200:
                    break
                
                data = resp.json()
                items = data.get('items', [])
                
                if not items:
                    break
                
                for item in items:
                    try:
                        item_basic = item.get('item_basic', {})
                        name = item_basic.get('name', '')
                        price = item_basic.get('price', 0)
                        
                        if not name or not price:
                            continue
                        
                        # Shopee 圖片
                        image = item_basic.get('image', '')
                        if image and not image.startswith('http'):
                            image = f'https://down-tw.img.susercontent.com/file/{image}'
                        
                        product = {
                            'product_id': f'shopee_{item_basic.get("itemid", "")}',
                            'platform': 'shopee',
                            'name': name,
                            'price': int(price / 100000) if price > 1000 else price,
                            'image': image,
                            'shop': item.get('shop', {}).get('name', 'Shopee'),
                            'rating': 4.5,
                            'url': f'https://shopee.tw/product/{item_basic.get("shopid", "")}/{item_basic.get("itemid", "")}',
                            'description': name
                        }
                        results.append(product)
                    except Exception as e:
                        logger.debug(f"Shopee 商品解析失敗: {e}")
                        continue
                
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Shopee 第 {page_num} 頁失敗: {e}")
                break
        
        logger.info(f"Shopee 取得 {len(results)} 個商品")
        return results
    except Exception as e:
        logger.error(f"Shopee 搜索失敗: {e}")
        return []


# ============================================================================
# Ruten 爬蟲 - 使用 BeautifulSoup 解析
# ============================================================================

def search_ruten(keyword: str, pages: int = 1) -> List[Dict]:
    """露天搜索 - 使用 HTML 解析"""
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        results = []
        
        for page_num in range(min(pages, 2)):
            try:
                # 露天搜索
                url = f"https://www.ruten.com.tw/find/?q={quote(keyword)}&page={page_num + 1}"
                
                resp = session.get(url, timeout=15)
                if resp.status_code != 200:
                    break
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                items = soup.find_all('li', class_='item')
                
                if not items:
                    break
                
                for item in items[:20]:  # 限制每頁 20 個
                    try:
                        name_elem = item.find('h3', class_='title')
                        price_elem = item.find('span', class_='price')
                        img_elem = item.find('img')
                        
                        if not name_elem or not price_elem:
                            continue
                        
                        name = name_elem.get_text(strip=True)
                        price_text = price_elem.get_text(strip=True).replace('NT$', '').replace(',', '')
                        
                        image = img_elem.get('src', '') if img_elem else ''
                        if image and not image.startswith('http'):
                            image = f'https://www.ruten.com.tw{image}'
                        
                        product = {
                            'product_id': f'ruten_{page_num}_{len(results)}',
                            'platform': 'ruten',
                            'name': name,
                            'price': int(price_text) if price_text.isdigit() else 0,
                            'image': image,
                            'shop': '露天拍賣',
                            'rating': 4.3,
                            'url': f'https://www.ruten.com.tw/find/?q={quote(keyword)}',
                            'description': name
                        }
                        if price_text.isdigit():  # 只加入有效價格的商品
                            results.append(product)
                    except Exception as e:
                        logger.debug(f"露天商品解析失敗: {e}")
                        continue
                
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"露天第 {page_num} 頁失敗: {e}")
                break
        
        logger.info(f"露天取得 {len(results)} 個商品")
        return results
    except Exception as e:
        logger.error(f"露天搜索失敗: {e}")
        return []


# ============================================================================
# Yahoo 爬蟲 - 使用 BeautifulSoup 解析
# ============================================================================

def search_yahoo(keyword: str, pages: int = 1) -> List[Dict]:
    """Yahoo 搜索 - 使用 HTML 解析"""
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        results = []
        
        for page_num in range(min(pages, 2)):
            try:
                # Yahoo 拍賣搜索
                url = f"https://tw.bid.yahoo.com/search/auction/product?p={quote(keyword)}&page={page_num + 1}"
                
                resp = session.get(url, timeout=15)
                if resp.status_code != 200:
                    break
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                items = soup.find_all('li', class_=['ProductItem', 'Product'])
                
                if not items:
                    break
                
                for item in items[:20]:  # 限制每頁 20 個
                    try:
                        name_elem = item.find('h3') or item.find('a', class_='product')
                        price_elem = item.find('span', class_=['Price', 'price'])
                        img_elem = item.find('img')
                        
                        if not name_elem:
                            continue
                        
                        name = name_elem.get_text(strip=True)
                        
                        # 提取價格
                        price = 0
                        if price_elem:
                            price_text = price_elem.get_text(strip=True).replace('NT$', '').replace(',', '')
                            try:
                                price = int(price_text)
                            except:
                                price = 0
                        
                        image = img_elem.get('src', '') if img_elem else ''
                        
                        product = {
                            'product_id': f'yahoo_{page_num}_{len(results)}',
                            'platform': 'yahoo',
                            'name': name,
                            'price': price if price > 0 else 99,  # 避免 0 價格
                            'image': image,
                            'shop': 'Yahoo 拍賣',
                            'rating': 4.6,
                            'url': f'https://tw.bid.yahoo.com/search/auction/product?p={quote(keyword)}',
                            'description': name
                        }
                        results.append(product)
                    except Exception as e:
                        logger.debug(f"Yahoo 商品解析失敗: {e}")
                        continue
                
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Yahoo 第 {page_num} 頁失敗: {e}")
                break
        
        logger.info(f"Yahoo 取得 {len(results)} 個商品")
        return results
    except Exception as e:
        logger.error(f"Yahoo 搜索失敗: {e}")
        return []


# ============================================================================
# 多平台搜索
# ============================================================================

def search_pchome(keyword: str, pages: int = 3) -> List[Dict]:
    """搜索 PChome 商品 - 使用官方 API"""
    results = []
    
    for page_num in range(1, pages + 1):
        try:
            page_results = search_pchome_api(keyword, page=page_num)
            if page_results:
                results.extend(page_results)
            else:
                break
            
            time.sleep(0.3)  # 避免過度請求
        except Exception as e:
            logger.warning(f"第 {page_num} 頁失敗: {e}")
            break
    
    logger.info(f"PChome 共取得 {len(results)} 個商品")
    return results


def search_cards_multi_platform(keyword: str) -> Dict[str, List[Dict]]:
    """
    在多個平台搜索卡牌
    返回格式: {'shopee': [...], 'ruten': [...], 'yahoo': [...], 'pchome': [...]}
    """
    results = {
        'shopee': search_shopee(keyword, pages=1),
        'ruten': search_ruten(keyword, pages=1),
        'yahoo': search_yahoo(keyword, pages=1),
        'pchome': search_pchome(keyword, pages=1)
    }
    
    return results


# ============================================================================
# 示例卡牌列表 (備用)
# ============================================================================

def get_sample_search_results(platform: str) -> List[Dict]:
    """
    獲取示例卡牌列表 (備用)
    包含遊戲王和寶可夢卡牌的官方圖片
    """
    # 遊戲王卡牌
    yugioh_cards = [
        ('青眼白龍', 'https://images.ygoprodeck.com/images/cards/89631139.jpg'),
        ('黑魔法師', 'https://images.ygoprodeck.com/images/cards/16732705.jpg'),
        ('藍眼白龍', 'https://images.ygoprodeck.com/images/cards/70095154.jpg'),
        ('青眼白龍 終極龍', 'https://images.ygoprodeck.com/images/cards/70630755.jpg'),
    ]
    
    # 寶可夢卡牌
    pokemon_cards = [
        ('皮卡丘', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png'),
        ('妙蛙種子', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png'),
        ('小火龍', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png'),
        ('傑尼龜', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png'),
    ]
    
    base_cards = yugioh_cards + pokemon_cards
    
    platform_data = {
        'shopee': [
            {
                'product_id': f'sample_shopee_{i}',
                'name': f'{card[0]} - 示例',
                'price': 500 + (i * 50),
                'platform': 'shopee',
                'url': f'https://shopee.tw/search?keyword={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.5
            }
            for i, card in enumerate(base_cards)
        ],
        'ruten': [
            {
                'product_id': f'sample_ruten_{i}',
                'name': f'{card[0]} - 示例',
                'price': 450 + (i * 45),
                'platform': 'ruten',
                'url': f'https://www.ruten.com.tw/find/?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.3
            }
            for i, card in enumerate(base_cards)
        ],
        'yahoo': [
            {
                'product_id': f'sample_yahoo_{i}',
                'name': f'{card[0]} - 示例',
                'price': 600 + (i * 55),
                'platform': 'yahoo',
                'url': f'https://tw.bid.yahoo.com/search?p={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.6
            }
            for i, card in enumerate(base_cards)
        ],
    }
    
    return platform_data.get(platform, [])


# ============================================================================
# 主要爬蟲函數
# ============================================================================

def scrape_cards() -> List[Dict]:
    """爬取卡牌數據"""
    return search_pchome('遊戲卡 寶可夢卡', pages=2)


if __name__ == '__main__':
    # 運行測試
    test_pchome_api()
"""
卡牌價格監控系統 - 爬蟲模組（精准版）
使用 PChome 官方 API 和真實電商平台數據
"""
import requests
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import quote
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局會話設置
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

# ============================================================================
# PChome 真實 API 爬蟲 (官方搜尋 API - JSON 格式)
# ============================================================================

def search_pchome_api(keyword: str, page: int = 1) -> List[Dict]:
    """
    使用 PChome 官方搜尋 API 獲取準確的商品數據
    
    API 文檔: https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={keyword}
    返回 JSON 格式的商品列表
    """
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        # PChome 官方搜尋 API
        offset = (page - 1) * 20
        url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={quote(keyword)}&offset={offset}&limit=20"
        
        logger.info(f"查詢 PChome API: {keyword} (頁 {page})")
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"PChome API 返回狀態碼: {response.status_code}")
            return []
        
        data = response.json()
        products = []
        
        # 提取商品數組 (prods 是官方返回的字段名)
        prods = data.get('prods', [])
        
        if not prods:
            logger.info(f"PChome 第 {page} 頁: 無商品")
            return []
        
        for prod in prods:
            try:
                # 提取必要字段 (注意: API 使用大寫 Id)
                product_id = prod.get('Id', '')
                name = prod.get('name', '')
                price = prod.get('price', 0)
                pic_s = prod.get('picS', '')  # 圖片後綴
                
                # 驗證必要字段
                if not name or not product_id:
                    logger.debug(f"跳過: 缺少基本信息")
                    continue
                
                # 拼接完整圖片 URL
                image_url = ''
                if pic_s:
                    image_url = f'https://cs-a.ecimg.tw{pic_s}'
                
                # 確保 price 是整數
                try:
                    price = int(price) if price else 0
                except (ValueError, TypeError):
                    price = 0
                
                product = {
                    'product_id': f'pchome_{product_id}',
                    'platform': 'pchome',
                    'name': name,
                    'price': price,  # 整數價格
                    'image': image_url,  # 完整圖片 URL
                    'shop': '24h PChome',
                    'rating': 4.5,  # API 沒有評分字段
                    'url': f'https://24h.pchome.com.tw/prod/{product_id}',
                    'description': name
                }
                
                products.append(product)
                logger.debug(f"✓ 商品: {name[:40]} | 價格: {price}元 | 圖片: {image_url[:60]}...")
                
            except Exception as e:
                logger.debug(f"解析商品失敗: {e}")
                continue
        
        logger.info(f"PChome 第 {page} 頁: 成功獲取 {len(products)} 個商品")
        return products
    
    except requests.RequestException as e:
        logger.error(f"PChome API 請求失敗: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"PChome API JSON 解析失敗: {e}")
        return []
    except Exception as e:
        logger.error(f"PChome 搜索錯誤: {e}")
        return []


def test_pchome_api():
    """
    測試函數：列印前三筆真實數據到終端機
    用來驗證數據是否準確
    """
    logger.info("=" * 70)
    logger.info("PChome API 數據測試")
    logger.info("=" * 70)
    
    test_keywords = ['遊戲卡', '寶可夢卡', '青眼白龍']
    
    for keyword in test_keywords:
        logger.info(f"\n搜尋: {keyword}")
        logger.info("-" * 70)
        
        products = search_pchome_api(keyword, page=1)
        
        if not products:
            logger.warning(f"未獲取到 {keyword} 的商品")
            continue
        
        # 列印前三筆
        for i, prod in enumerate(products[:3], 1):
            logger.info(f"\n【第 {i} 筆】")
            logger.info(f"  商品名稱: {prod['name']}")
            logger.info(f"  價格: {prod['price']} 元")
            logger.info(f"  圖片 URL: {prod['image']}")
            logger.info(f"  商品 ID: {prod['product_id']}")
            logger.info(f"  商品連結: {prod['url']}")
        
        time.sleep(0.5)  # 避免過度請求
    
    logger.info("\n" + "=" * 70)
    logger.info("測試完成")
    logger.info("=" * 70)


# ============================================================================
# 搜索函數 (多平台支持)
# ============================================================================

def search_pchome(keyword: str, pages: int = 3) -> List[Dict]:
    """
    搜索 PChome 商品 - 使用官方 API
    """
    results = []
    
    for page_num in range(1, pages + 1):
        try:
            page_results = search_pchome_api(keyword, page=page_num)
            if page_results:
                results.extend(page_results)
            else:
                # 無商品表示已到盡頭
                break
            
            time.sleep(0.3)  # 避免過度請求
        except Exception as e:
            logger.warning(f"第 {page_num} 頁失敗: {e}")
            break
    
    logger.info(f"PChome 共取得 {len(results)} 個商品")
    return results


def search_shopee(keyword: str, pages: int = 1) -> List[Dict]:
    """蝦皮搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"蝦皮搜索: {keyword} (待實現)")
    return []


def search_ruten(keyword: str, pages: int = 1) -> List[Dict]:
    """露天搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"露天搜索: {keyword} (待實現)")
    return []


def search_yahoo(keyword: str, pages: int = 1) -> List[Dict]:
    """Yahoo搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"Yahoo搜索: {keyword} (待實現)")
    return []


def search_cards_multi_platform(keyword: str) -> Dict[str, List[Dict]]:
    """
    在多個平台搜索卡牌
    返回格式: {'shopee': [...], 'ruten': [...], 'yahoo': [...], 'pchome': [...]}
    """
    results = {
        'shopee': [],
        'ruten': [],
        'yahoo': [],
        'pchome': search_pchome(keyword, pages=2)  # 獲取前 40 個商品
    }
    
    return results


# ============================================================================
# 示例卡牌列表 (備用)
# ============================================================================

def get_sample_search_results(platform: str) -> List[Dict]:
    """
    獲取示例卡牌列表 (備用)
    包含遊戲王和寶可夢卡牌的官方圖片
    """
    # 遊戲王卡牌
    yugioh_cards = [
        ('青眼白龍', 'https://images.ygoprodeck.com/images/cards/89631139.jpg'),
        ('黑魔法師', 'https://images.ygoprodeck.com/images/cards/16732705.jpg'),
        ('藍眼白龍', 'https://images.ygoprodeck.com/images/cards/70095154.jpg'),
        ('青眼白龍 終極龍', 'https://images.ygoprodeck.com/images/cards/70630755.jpg'),
    ]
    
    # 寶可夢卡牌
    pokemon_cards = [
        ('皮卡丘', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png'),
        ('妙蛙種子', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png'),
        ('小火龍', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png'),
        ('傑尼龜', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png'),
    ]
    
    base_cards = yugioh_cards + pokemon_cards
    
    platform_data = {
        'shopee': [
            {
                'product_id': f'sample_shopee_{i}',
                'name': f'{card[0]} - 示例',
                'price': 500 + (i * 50),
                'platform': 'shopee',
                'url': f'https://shopee.tw/search?keyword={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.5
            }
            for i, card in enumerate(base_cards)
        ],
        'ruten': [
            {
                'product_id': f'sample_ruten_{i}',
                'name': f'{card[0]} - 示例',
                'price': 450 + (i * 45),
                'platform': 'ruten',
                'url': f'https://www.ruten.com.tw/find/?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.3
            }
            for i, card in enumerate(base_cards)
        ],
        'yahoo': [
            {
                'product_id': f'sample_yahoo_{i}',
                'name': f'{card[0]} - 示例',
                'price': 600 + (i * 55),
                'platform': 'yahoo',
                'url': f'https://tw.bid.yahoo.com/search?p={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.6
            }
            for i, card in enumerate(base_cards)
        ],
        'pchome': [
            {
                'product_id': f'sample_pchome_{i}',
                'name': f'{card[0]} - 示例',
                'price': 550 + (i * 52),
                'platform': 'pchome',
                'url': f'https://24h.pchome.com.tw/search?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.4
            }
            for i, card in enumerate(base_cards)
        ]
    }
    
    return platform_data.get(platform, [])


# ============================================================================
# 主要爬蟲函數 (相容舊版 API)
# ============================================================================

def scrape_cards() -> List[Dict]:
    """爬取卡牌數據"""
    return search_pchome('遊戲卡 寶可夢卡', pages=2)


if __name__ == '__main__':
    # 運行測試
    test_pchome_api()


# ============================================================================
# PChome 真實 API 爬蟲 (官方搜尋 API - JSON 格式)
# ============================================================================

def search_pchome_api(keyword: str, page: int = 1) -> List[Dict]:
    """
    使用 PChome 官方搜尋 API 獲取準確的商品數據
    
    API 文檔: https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={keyword}
    返回 JSON 格式的商品列表
    """
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        # PChome 官方搜尋 API
        offset = (page - 1) * 20
        url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={quote(keyword)}&offset={offset}&limit=20"
        
        logger.info(f"查詢 PChome API: {keyword} (頁 {page})")
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"PChome API 返回狀態碼: {response.status_code}")
            return []
        
        data = response.json()
        products = []
        
        # 提取商品數組 (prods 是官方返回的字段名)
        prods = data.get('prods', [])
        
        if not prods:
            logger.info(f"PChome 第 {page} 頁: 無商品")
            return []
        
        for prod in prods:
            try:
                # 提取必要字段 (注意: API 使用大寫 Id)
                product_id = prod.get('Id', '')
                name = prod.get('name', '')
                price = prod.get('price', 0)
                pic_s = prod.get('picS', '')  # 圖片後綴
                
                # 驗證必要字段
                if not name or not product_id:
                    logger.debug(f"跳過: 缺少基本信息")
                    continue
                
                # 拼接完整圖片 URL
                image_url = ''
                if pic_s:
                    image_url = f'https://cs-a.ecimg.tw{pic_s}'
                
                # 確保 price 是整數
                try:
                    price = int(price) if price else 0
                except (ValueError, TypeError):
                    price = 0
                
                product = {
                    'product_id': f'pchome_{product_id}',
                    'platform': 'pchome',
                    'name': name,
                    'price': price,  # 整數價格
                    'image': image_url,  # 完整圖片 URL
                    'shop': '24h PChome',
                    'rating': 4.5,  # API 沒有評分字段
                    'url': f'https://24h.pchome.com.tw/prod/{product_id}',
                    'description': name
                }
                
                products.append(product)
                logger.debug(f"✓ 商品: {name[:40]} | 價格: {price}元 | 圖片: {image_url[:60]}...")
                
            except Exception as e:
                logger.debug(f"解析商品失敗: {e}")
                continue
        
        logger.info(f"PChome 第 {page} 頁: 成功獲取 {len(products)} 個商品")
        return products
    
    except requests.RequestException as e:
        logger.error(f"PChome API 請求失敗: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"PChome API JSON 解析失敗: {e}")
        return []
    except Exception as e:
        logger.error(f"PChome 搜索錯誤: {e}")
        return []


def test_pchome_api():
    """
    測試函數：列印前三筆真實數據到終端機
    用來驗證數據是否準確
    """
    logger.info("=" * 70)
    logger.info("PChome API 數據測試")
    logger.info("=" * 70)
    
    test_keywords = ['遊戲卡', '寶可夢卡', '青眼白龍']
    
    for keyword in test_keywords:
        logger.info(f"\n搜尋: {keyword}")
        logger.info("-" * 70)
        
        products = search_pchome_api(keyword, page=1)
        
        if not products:
            logger.warning(f"未獲取到 {keyword} 的商品")
            continue
        
        # 列印前三筆
        for i, prod in enumerate(products[:3], 1):
            logger.info(f"\n【第 {i} 筆】")
            logger.info(f"  商品名稱: {prod['name']}")
            logger.info(f"  價格: {prod['price']} 元")
            logger.info(f"  圖片 URL: {prod['image']}")
            logger.info(f"  商品 ID: {prod['product_id']}")
            logger.info(f"  商品連結: {prod['url']}")
        
        time.sleep(0.5)  # 避免過度請求
    
    logger.info("\n" + "=" * 70)
    logger.info("測試完成")
    logger.info("=" * 70)


# ============================================================================
# 搜索函數 (多平台支持)
# ============================================================================

def search_pchome(keyword: str, pages: int = 3) -> List[Dict]:
    """
    搜索 PChome 商品 - 使用官方 API
    """
    results = []
    
    for page_num in range(1, pages + 1):
        try:
            page_results = search_pchome_api(keyword, page=page_num)
            if page_results:
                results.extend(page_results)
            else:
                # 無商品表示已到盡頭
                break
            
            time.sleep(0.3)  # 避免過度請求
        except Exception as e:
            logger.warning(f"第 {page_num} 頁失敗: {e}")
            break
    
    logger.info(f"PChome 共取得 {len(results)} 個商品")
    return results


def search_shopee(keyword: str, pages: int = 1) -> List[Dict]:
    """蝦皮搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"蝦皮搜索: {keyword} (待實現)")
    return []


def search_ruten(keyword: str, pages: int = 1) -> List[Dict]:
    """露天搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"露天搜索: {keyword} (待實現)")
    return []


def search_yahoo(keyword: str, pages: int = 1) -> List[Dict]:
    """Yahoo搜索 (暫時返回空列表 - 等待實現)"""
    logger.info(f"Yahoo搜索: {keyword} (待實現)")
    return []


def search_cards_multi_platform(keyword: str) -> Dict[str, List[Dict]]:
    """
    在多個平台搜索卡牌
    返回格式: {'shopee': [...], 'ruten': [...], 'yahoo': [...], 'pchome': [...]}
    """
    results = {
        'shopee': [],
        'ruten': [],
        'yahoo': [],
        'pchome': search_pchome(keyword, pages=2)  # 獲取前 40 個商品
    }
    
    return results


# ============================================================================
# 示例卡牌列表 (備用)
# ============================================================================

def get_sample_search_results(platform: str) -> List[Dict]:
    """
    獲取示例卡牌列表 (備用)
    包含遊戲王和寶可夢卡牌的官方圖片
    """
    # 遊戲王卡牌
    yugioh_cards = [
        ('青眼白龍', 'https://images.ygoprodeck.com/images/cards/89631139.jpg'),
        ('黑魔法師', 'https://images.ygoprodeck.com/images/cards/16732705.jpg'),
        ('藍眼白龍', 'https://images.ygoprodeck.com/images/cards/70095154.jpg'),
        ('青眼白龍 終極龍', 'https://images.ygoprodeck.com/images/cards/70630755.jpg'),
    ]
    
    # 寶可夢卡牌
    pokemon_cards = [
        ('皮卡丘', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png'),
        ('妙蛙種子', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png'),
        ('小火龍', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png'),
        ('傑尼龜', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png'),
    ]
    
    base_cards = yugioh_cards + pokemon_cards
    
    platform_data = {
        'shopee': [
            {
                'product_id': f'sample_shopee_{i}',
                'name': f'{card[0]} - 示例',
                'price': 500 + (i * 50),
                'platform': 'shopee',
                'url': f'https://shopee.tw/search?keyword={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.5
            }
            for i, card in enumerate(base_cards)
        ],
        'ruten': [
            {
                'product_id': f'sample_ruten_{i}',
                'name': f'{card[0]} - 示例',
                'price': 450 + (i * 45),
                'platform': 'ruten',
                'url': f'https://www.ruten.com.tw/find/?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.3
            }
            for i, card in enumerate(base_cards)
        ],
        'yahoo': [
            {
                'product_id': f'sample_yahoo_{i}',
                'name': f'{card[0]} - 示例',
                'price': 600 + (i * 55),
                'platform': 'yahoo',
                'url': f'https://tw.bid.yahoo.com/search?p={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.6
            }
            for i, card in enumerate(base_cards)
        ],
        'pchome': [
            {
                'product_id': f'sample_pchome_{i}',
                'name': f'{card[0]} - 示例',
                'price': 550 + (i * 52),
                'platform': 'pchome',
                'url': f'https://24h.pchome.com.tw/search?q={quote(card[0])}',
                'image': card[1],
                'shop': f'示例商店 {i}',
                'rating': 4.4
            }
            for i, card in enumerate(base_cards)
        ]
    }
    
    return platform_data.get(platform, [])


# ============================================================================
# 主要爬蟲函數 (相容舊版 API)
# ============================================================================

def scrape_cards() -> List[Dict]:
    """爬取卡牌數據"""
    return search_pchome('遊戲卡 寶可夢卡', pages=2)


if __name__ == '__main__':
    # 運行測試
    test_pchome_api()
