"""
卡牌價格監控系統 - 網頁爬蟲模組
"""
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CardScraper:
    """卡牌爬蟲類"""
    
    def __init__(self, base_url: str = "https://www.catfootprint.com/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_cards(self) -> List[Dict[str, Optional[str]]]:
        """爬取卡牌資訊"""
        try:
            cards = self._scrape_from_website()
            if not cards:
                logger.info("無法從網站取得卡牌, 使用示例數據")
                cards = self._get_sample_cards()
            return cards
        except Exception as e:
            logger.error(f"爬蟲錯誤: {str(e)}")
            return self._get_sample_cards()
    
    def _scrape_from_website(self) -> List[Dict[str, Optional[str]]]:
        """從網站爬取真實數據"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            cards = []
            
            card_containers = soup.find_all('div', class_=['card', 'product', 'item'])
            
            if card_containers:
                for container in card_containers:
                    card_data = self._extract_card_info(container)
                    if card_data and card_data.get('name'):
                        cards.append(card_data)
            
            time.sleep(1)
            return cards
        
        except requests.RequestException as e:
            logger.error(f"網路請求錯誤: {str(e)}")
            return []
    
    def _extract_card_info(self, container) -> Optional[Dict[str, Optional[str]]]:
        """從容器元素中提取卡牌信息"""
        try:
            card_data = {}
            
            name_elem = container.find('h3', class_='card-name') or \
                       container.find('h4') or \
                       container.find('a', class_='product-name')
            card_data['name'] = name_elem.get_text(strip=True) if name_elem else None
            
            price_elem = container.find('span', class_=['price', 'product-price']) or \
                        container.find('div', class_='price')
            price_text = price_elem.get_text(strip=True) if price_elem else None
            card_data['price'] = self._parse_price(price_text) if price_text else 0
            
            img_elem = container.find('img', class_=['card-image', 'product-image'])
            if img_elem:
                img_url = img_elem.get('src') or img_elem.get('data-src')
                if img_url:
                    card_data['image_url'] = self._resolve_url(img_url)
            
            desc_elem = container.find('p', class_=['description', 'card-description'])
            card_data['description'] = desc_elem.get_text(strip=True) if desc_elem else ""
            
            return card_data if card_data.get('name') else None
        
        except Exception as e:
            logger.warning(f"提取卡牌信息時出錯: {str(e)}")
            return None
    
    def _parse_price(self, price_text: str) -> float:
        """解析價格字符串為浮點數"""
        try:
            price_text = price_text.replace('NT$', '').replace('$', '').replace(',', '').strip()
            return float(price_text)
        except ValueError:
            logger.warning(f"無法解析價格: {price_text}")
            return 0.0
    
    def _resolve_url(self, url: str) -> str:
        """解析相對 URL 為絕對 URL"""
        if url.startswith(('http://', 'https://')):
            return url
        elif url.startswith('/'):
            return self.base_url.rstrip('/') + url
        else:
            return self.base_url.rstrip('/') + '/' + url
    
    def _get_sample_cards(self) -> List[Dict[str, Optional[str]]]:
        """返回示例卡牌數據"""
        return [
            {
                'name': '藍眼白龍 (Blue-Eyes White Dragon)',
                'price': 1500,
                'image_url': 'https://via.placeholder.com/200x280?text=Blue-Eyes+White+Dragon',
                'description': '傳說中的強力卡牌，具有高度攻擊力'
            },
            {
                'name': '黑魔法師 (Dark Magician)',
                'price': 1200,
                'image_url': 'https://via.placeholder.com/200x280?text=Dark+Magician',
                'description': '經典法術師卡牌，能使用強力魔法'
            },
            {
                'name': '青眼亞白龍 (Blue-Eyes Alternative White Dragon)',
                'price': 800,
                'image_url': 'https://via.placeholder.com/200x280?text=Blue-Eyes+Alternative',
                'description': '藍眼白龍的姐妹卡，具有不同的效果'
            },
            {
                'name': '混沌儀式 (Chaos Ritual)',
                'price': 600,
                'image_url': 'https://via.placeholder.com/200x280?text=Chaos+Ritual',
                'description': '強力的儀式卡，能召喚高級怪獸'
            },
            {
                'name': '無限深淵 (Bottomless Abyss)',
                'price': 500,
                'image_url': 'https://via.placeholder.com/200x280?text=Bottomless+Abyss',
                'description': '陷阱卡牌，能夠攔截敵方怪獸'
            }
        ]
    
    def close(self):
        """關閉爬蟲會話"""
        self.session.close()


def scrape_cards() -> List[Dict[str, Optional[str]]]:
    """爬取卡牌數據"""
    scraper = CardScraper()
    try:
        return scraper.fetch_cards()
    finally:
        scraper.close()
