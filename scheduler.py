"""
自動更新定時器
"""
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_cards
from models import Card
import logging

logger = logging.getLogger(__name__)

def update_all_cards():
    """更新所有卡牌"""
    try:
        logger.info("自動更新開始...")
        cards_data = scrape_cards()
        updated_count = 0
        
        for card_data in cards_data:
            Card.create_or_update(
                name=card_data['name'],
                price=card_data.get('price', 0),
                image_url=card_data.get('image_url'),
                description=card_data.get('description', '')
            )
            updated_count += 1
        
        logger.info(f"自動更新完成，共更新 {updated_count} 張卡牌")
    except Exception as e:
        logger.error(f"自動更新失敗: {str(e)}")

def start_scheduler():
    """啟動自動更新排程"""
    scheduler = BackgroundScheduler()
    
    # 每 6 小時更新一次
    scheduler.add_job(
        update_all_cards,
        'interval',
        hours=6,
        id='auto_update',
        name='自動更新卡牌價格'
    )
    
    scheduler.start()
    logger.info("自動更新排程已啟動（每 6 小時更新一次）")
    
    return scheduler
