"""
卡牌價格監控系統 - Flask 主應用程式
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from models import db, Card, PriceHistory, init_db, get_database_path
from scraper import scrape_cards_and_update_db
import logging
from datetime import datetime, timedelta
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 Flask 應用
app = Flask(__name__)

# 配置
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{get_database_path()}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False  # 支持中文

# 初始化擴展
db.init_app(app)
CORS(app)

# 初始化資料庫
init_db(app)


@app.route('/')
def index():
    """首頁 - 顯示所有卡牌"""
    try:
        cards = Card.query.all()
        return render_template('index.html', cards=cards)
    except Exception as e:
        logger.error(f"載入首頁失敗: {str(e)}")
        return render_template('index.html', cards=[])


@app.route('/api/cards', methods=['GET'])
def get_cards():
    """API 端點 - 取得所有卡牌"""
    try:
        cards = Card.query.all()
        return jsonify([card.to_dict() for card in cards])
    except Exception as e:
        logger.error(f"取得卡牌失敗: {str(e)}")
        return jsonify({'error': '取得卡牌失敗'}), 500


@app.route('/api/cards/<int:card_id>', methods=['GET'])
def get_card(card_id):
    """API 端點 - 取得特定卡牌的詳細信息"""
    try:
        card = Card.query.get(card_id)
        if not card:
            return jsonify({'error': '卡牌未找到'}), 404
        
        return jsonify(card.to_dict())
    except Exception as e:
        logger.error(f"取得卡牌詳情失敗: {str(e)}")
        return jsonify({'error': '取得卡牌詳情失敗'}), 500


@app.route('/api/cards/<int:card_id>/price-history', methods=['GET'])
def get_price_history(card_id):
    """API 端點 - 取得卡牌的價格歷史"""
    try:
        # 驗證卡牌是否存在
        card = Card.query.get(card_id)
        if not card:
            return jsonify({'error': '卡牌未找到'}), 404
        
        # 取得過去 30 天的價格歷史（如果沒有指定時間範圍）
        days = request.args.get('days', default=30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        price_history = PriceHistory.query.filter(
            PriceHistory.card_id == card_id,
            PriceHistory.recorded_at >= cutoff_date
        ).order_by(PriceHistory.recorded_at.asc()).all()
        
        # 格式化數據供圖表使用
        history_data = [
            {
                'date': record.recorded_at.strftime('%Y-%m-%d %H:%M'),
                'price': record.price
            }
            for record in price_history
        ]
        
        return jsonify({
            'card_id': card_id,
            'card_name': card.name,
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
        updated_count = scrape_cards_and_update_db(db.session, Card, PriceHistory)
        
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
        total_cards = Card.query.count()
        price_history_count = PriceHistory.query.count()
        
        # 計算平均價格變動
        avg_price = db.session.query(db.func.avg(Card.current_price)).scalar()
        
        return jsonify({
            'total_cards': total_cards,
            'price_history_count': price_history_count,
            'average_price': round(float(avg_price) if avg_price else 0, 2)
        })
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
    with app.app_context():
        # 初始化資料庫
        db.create_all()
        
        # 檢查資料庫是否為空，如果為空則執行初始爬取
        if Card.query.count() == 0:
            logger.info("資料庫為空，執行初始卡牌爬取...")
            scrape_cards_and_update_db(db.session, Card, PriceHistory)
    
    # 啟動應用
    app.run(debug=True, host='0.0.0.0', port=5000)
