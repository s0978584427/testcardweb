"""
卡牌價格監控系統 - 網頁爬蟲模組
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
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
        """
        爬取卡牌資訊
        由於目標網站為資訊型網站，此函數使用示例數據
        實際使用時可根據網站結構修改選擇器
        
        Returns:
            包含卡牌信息的字典列表，含 name, price, image_url, description
        """
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
        """
        從網站爬取真實數據
        此方法為模板，可根據實際網站結構修改
        """
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            cards = []
            
            # 以下是示例選擇器，需根據實際網站HTML結構調整
            # 查找可能包含卡牌的容器
            card_containers = soup.find_all('div', class_=['card', 'product', 'item'])
            
            if card_containers:
                for container in card_containers:
                    card_data = self._extract_card_info(container)
                    if card_data and card_data.get('name'):
                        cards.append(card_data)
            
            # 加入延遲以避免對伺服器造成壓力
            time.sleep(1)
            
            return cards
        
        except requests.RequestException as e:
            logger.error(f"網路請求錯誤: {str(e)}")
            return []
    
    def _extract_card_info(self, container) -> Optional[Dict[str, Optional[str]]]:
        """
        從容器元素中提取卡牌信息
        
        Args:
            container: BeautifulSoup 容器元素
        
        Returns:
            包含卡牌信息的字典或 None
        """
        try:
            card_data = {}
            
            # 嘗試提取卡牌名稱
            name_elem = container.find('h3', class_='card-name') or \
                       container.find('h4') or \
                       container.find('a', class_='product-name')
            card_data['name'] = name_elem.get_text(strip=True) if name_elem else None
            
            # 嘗試提取價格
            price_elem = container.find('span', class_=['price', 'product-price']) or \
                        container.find('div', class_='price')
            price_text = price_elem.get_text(strip=True) if price_elem else None
            card_data['price'] = self._parse_price(price_text) if price_text else 0
            
            # 嘗試提取圖片 URL
            img_elem = container.find('img', class_=['card-image', 'product-image'])
            if img_elem:
                img_url = img_elem.get('src') or img_elem.get('data-src')
                if img_url:
                    card_data['image_url'] = self._resolve_url(img_url)
            
            # 嘗試提取描述
            desc_elem = container.find('p', class_=['description', 'card-description'])
            card_data['description'] = desc_elem.get_text(strip=True) if desc_elem else ""
            
            return card_data if card_data.get('name') else None
        
        except Exception as e:
            logger.warning(f"提取卡牌信息時出錯: {str(e)}")
            return None
    
    def _parse_price(self, price_text: str) -> float:
        """
        解析價格字符串為浮點數
        
        Args:
            price_text: 價格文本，可能包含符號
        
        Returns:
            浮點數價格
        """
        try:
            # 移除常見的貨幣符號和空格
            price_text = price_text.replace('NT$', '').replace('$', '').replace(',', '').strip()
            return float(price_text)
        except ValueError:
            logger.warning(f"無法解析價格: {price_text}")
            return 0.0
    
    def _resolve_url(self, url: str) -> str:
        """
        解析相對 URL 為絕對 URL
        
        Args:
            url: 可能是相對或絕對 URL
        
        Returns:
            絕對 URL
        """
        if url.startswith(('http://', 'https://')):
            return url
        elif url.startswith('/'):
            return self.base_url.rstrip('/') + url
        else:
            return self.base_url.rstrip('/') + '/' + url
    
    def _get_sample_cards(self) -> List[Dict[str, Optional[str]]]:
        """
        返回示例卡牌數據以供開發和測試
        """
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


def scrape_cards_and_update_db(db_session, Card, PriceHistory) -> int:
    """
    爬取卡牌並更新資料庫
    
    Args:
        db_session: SQLAlchemy 資料庫會話
        Card: 卡牌模型類
        PriceHistory: 價格歷史模型類
    
    Returns:
        更新的卡牌數量
    """
    scraper = CardScraper()
    try:
        cards_data = scraper.fetch_cards()
        updated_count = 0
        
        for card_data in cards_data:
            # 檢查卡牌是否已存在
            existing_card = db_session.query(Card).filter_by(name=card_data['name']).first()
            
            if existing_card:
                # 更新現有卡牌
                if card_data.get('price', 0) != existing_card.current_price:
                    # 新增價格歷史記錄
                    price_record = PriceHistory(
                        card_id=existing_card.id,
                        price=card_data.get('price', 0)
                    )
                    db_session.add(price_record)
                    existing_card.current_price = card_data.get('price', 0)
                
                if card_data.get('image_url'):
                    existing_card.image_url = card_data['image_url']
                if card_data.get('description'):
                    existing_card.description = card_data['description']
            else:
                # 新增卡牌
                new_card = Card(
                    name=card_data['name'],
                    current_price=card_data.get('price', 0),
                    image_url=card_data.get('image_url'),
                    description=card_data.get('description', '')
                )
                db_session.add(new_card)
                db_session.flush()  # 取得 ID
                
                # 新增初始價格歷史記錄
                price_record = PriceHistory(
                    card_id=new_card.id,
                    price=card_data.get('price', 0)
                )
                db_session.add(price_record)
            
            updated_count += 1
        
        db_session.commit()
        logger.info(f"成功更新/新增 {updated_count} 張卡牌")
        return updated_count
    
    except Exception as e:
        db_session.rollback()
        logger.error(f"資料庫更新失敗: {str(e)}")
        return 0
    finally:
        scraper.close()
