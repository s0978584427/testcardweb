"""
卡牌價格監控系統 - Flask 主應用程式
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from models import Card, PriceHistory, Stats, init_db
from scraper import scrape_cards
import logging
from datetime import datetime
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 Flask 應用
app = Flask(__name__)

# 初始化擴展
CORS(app)

# 初始化資料庫
init_db()

@app.route('/')
def index():
    """首頁 - 顯示所有卡牌"""
    try:
        cards = Card.get_all()
        return render_template('index.html', cards=cards)
    except Exception as e:
        logger.error(f"載入首頁失敗: {str(e)}")
        return render_template('index.html', cards=[])


@app.route('/api/cards', methods=['GET'])
def get_cards():
    """API 端點 - 取得所有卡牌"""
    try:
        cards = Card.get_all()
        return jsonify(cards)
    except Exception as e:
        logger.error(f"取得卡牌失敗: {str(e)}")
        return jsonify({'error': '取得卡牌失敗'}), 500


@app.route('/api/cards/<int:card_id>', methods=['GET'])
def get_card(card_id):
    """API 端點 - 取得特定卡牌的詳細信息"""
    try:
        card = Card.get_by_id(card_id)
        if not card:
            return jsonify({'error': '卡牌未找到'}), 404
        
        return jsonify(card)
    except Exception as e:
        logger.error(f"取得卡牌詳情失敗: {str(e)}")
        return jsonify({'error': '取得卡牌詳情失敗'}), 500


@app.route('/api/cards/<int:card_id>/price-history', methods=['GET'])
def get_price_history(card_id):
    """API 端點 - 取得卡牌的價格歷史"""
    try:
        # 驗證卡牌是否存在
        card = Card.get_by_id(card_id)
        if not card:
            return jsonify({'error': '卡牌未找到'}), 404
        
        # 取得過去 30 天的價格歷史（如果沒有指定時間範圍）
        days = request.args.get('days', default=30, type=int)
        
        price_history = PriceHistory.get_by_card(card_id, days)
        
        # 格式化數據供圖表使用
        history_data = [
            {
                'date': record['recorded_at'][:16],
                'price': record['price']
            }
            for record in price_history
        ]
        
        return jsonify({
            'card_id': card_id,
            'card_name': card['name'],
            'history': history_data
        })
    except Exception as e:
        logger.error(f"取得價格歷史失敗: {str(e)}")
        return jsonify({'error': '取得價格歷史失敗'}), 500


@app.route('/update', methods=['POST', 'GET'])
def update_cards():
    """更新卡牌價格 - 觸發爬蟲"""
    try:
        logger.info("開始更新卡牌...")
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
        
        logger.info(f"成功更新/新增 {updated_count} 張卡牌")
        
        return jsonify({
            'success': True,
            'message': f'成功更新 {updated_count} 張卡牌',
            'updated_count': updated_count,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"卡牌更新失敗: {str(e)}")
        return jsonify({
            'success': False,
            'error': '卡牌更新失敗',
            'details': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """API 端點 - 取得統計信息"""
    try:
        stats = Stats.get_all()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"取得統計信息失敗: {str(e)}")
        return jsonify({'error': '取得統計信息失敗'}), 500


@app.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return jsonify({'error': '資源未找到'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    logger.error(f"伺服器錯誤: {str(error)}")
    return jsonify({'error': '伺服器內部錯誤'}), 500


@app.before_request
def log_request():
    """記錄請求信息"""
    logger.debug(f"{request.method} {request.path}")


if __name__ == '__main__':
    # 初始化資料庫
    init_db()
    
    # 檢查資料庫是否為空，如果為空則執行初始爬取
    if len(Card.get_all()) == 0:
        logger.info("資料庫為空，執行初始卡牌爬取...")
        cards_data = scrape_cards()
        for card_data in cards_data:
            Card.create_or_update(
                name=card_data['name'],
                price=card_data.get('price', 0),
                image_url=card_data.get('image_url'),
                description=card_data.get('description', '')
            )
    
    # 啟動應用
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
