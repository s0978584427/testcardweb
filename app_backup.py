"""
卡牌價格監控系統 - Flask 主應用程式
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from models import Card, PriceHistory, Stats, Product, SearchCache, init_db
from scraper import scrape_cards, search_cards_multi_platform
from scheduler import start_scheduler
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

# 啟動自動更新排程
scheduler = None
if os.environ.get('FLASK_ENV') != 'development':
    try:
        scheduler = start_scheduler()
    except Exception as e:
        logger.warning(f"排程啟動失敗（本地開發可忽略）: {str(e)}")

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


@app.route('/api/recommended', methods=['GET'])
def get_recommended_cards():
    """
    API 端點 - 取得推薦卡牌 (首頁展示)
    方案 B: 只使用 PChome (官方 API)
    """
    try:
        from scraper import search_pchome, get_sample_search_results
        
        logger.info("從 PChome 獲取推薦卡牌...")
        
        # PChome - 真實 API (唯一的來源)
        pchome_results = search_pchome('卡牌', pages=1)
        
        logger.info(f"PChome: {len(pchome_results)} 個商品")
        
        # 構建推薦卡牌
        recommended = {
            'pchome': pchome_results[:5] if pchome_results else get_sample_search_results('pchome')[:5],
        }
        
        return jsonify({
            'recommended': recommended,
            'total_featured': len(pchome_results),
            'has_real_data': len(pchome_results) > 0,
            'note': '方案 B: 只提供 PChome 官方 API 商品 + 國際卡牌參考'
        })
    
    except Exception as e:
        logger.error(f"取得推薦卡牌失敗: {str(e)}")
        return jsonify({'error': '取得推薦卡牌失敗'}), 500


@app.route('/api/search', methods=['GET'])
def search_cards():
    """
    API 端點 - 搜索卡牌 (方案 B: 只使用 PChome)
    參數: keyword (搜索關鍵字)
    返回: PChome 搜索結果
    """
    try:
        from scraper import search_pchome
        
        keyword = request.args.get('keyword', '').strip()
        
        if not keyword or len(keyword) < 2:
            return jsonify({'error': '搜索關鍵字至少 2 個字符'}), 400
        
        logger.info(f"搜尋 PChome: {keyword}")
        
        # 只搜索 PChome
        pchome_results = search_pchome(keyword, pages=1)
        
        results = {
            'pchome': pchome_results
        }
        
        return jsonify({
            'keyword': keyword,
            'results': results,
            'total_results': len(pchome_results),
            'note': '方案 B: 只提供 PChome 官方 API 商品。若需多平台支援，請使用組合搜尋。'
        })
    
    except Exception as e:
        logger.error(f"搜索卡牌失敗: {str(e)}")
        return jsonify({'error': '搜索失敗，請稍後重試'}), 500


@app.route('/api/product/<product_id>', methods=['GET'])
def get_product_detail(product_id):
    """
    API 端點 - 取得商品詳情
    """
    try:
        product = Product.get_by_id(product_id)
        
        if not product:
            return jsonify({'error': '商品未找到'}), 404
        
        return jsonify(product)
    
    except Exception as e:
        logger.error(f"取得商品詳情失敗: {str(e)}")
        return jsonify({'error': '取得商品詳情失敗'}), 500


@app.route('/api/stats/products', methods=['GET'])
def get_product_stats():
    """
    API 端點 - 取得商品統計信息
    """
    try:
        total = Product.count()
        by_platform = Product.count_by_platform()
        
        return jsonify({
            'total_products': total,
            'by_platform': by_platform
        })
    
    except Exception as e:
        logger.error(f"取得商品統計失敗: {str(e)}")
        return jsonify({'error': '取得統計失敗'}), 500


@app.route('/api/card-references', methods=['GET'])
def get_card_references():
    """
    API 端點 - 取得卡牌參考資料
    整合 YGOProDeck, PokeAPI, Scryfall
    參數: keyword (搜索關鍵字)
    """
    try:
        from card_apis import get_all_card_sources
        
        keyword = request.args.get('keyword', '').strip()
        
        if not keyword or len(keyword) < 2:
            return jsonify({'error': '搜索關鍵字至少 2 個字符'}), 400
        
        logger.info(f"搜索卡牌參考資料: {keyword}")
        
        # 從所有卡牌 API 獲取數據
        card_data = get_all_card_sources(keyword)
        
        return jsonify({
            'keyword': keyword,
            'references': {
                'yugioh': card_data.get('yugioh', []),
                'pokemon': card_data.get('pokemon', []),
                'mtg': card_data.get('mtg', [])
            },
            'total_references': sum(len(cards) for cards in card_data.values()),
            'sources': {
                'yugioh': 'YGOProDeck API',
                'pokemon': 'PokeAPI',
                'mtg': 'Scryfall API'
            }
        })
    
    except Exception as e:
        logger.error(f"取得卡牌參考資料失敗: {str(e)}")
        return jsonify({'error': '取得卡牌參考資料失敗'}), 500


@app.route('/api/combined-search', methods=['GET'])
def combined_search():
    """
    API 端點 - 組合搜索
    同時搜索台灣平台價格 + 國際卡牌資料庫
    參數: keyword (搜索關鍵字)
    """
    try:
        from card_apis import get_all_card_sources
        
        keyword = request.args.get('keyword', '').strip()
        
        if not keyword or len(keyword) < 2:
            return jsonify({'error': '搜索關鍵字至少 2 個字符'}), 400
        
        logger.info(f"組合搜索: {keyword}")
        
        # 1. 台灣平台商品 (PChome)
        pchome_results = search_pchome(keyword, pages=1)
        
        # 2. 國際卡牌資料庫
        card_references = get_all_card_sources(keyword)
        
        return jsonify({
            'keyword': keyword,
            'taipei_prices': {
                'pchome': pchome_results[:5] if pchome_results else get_sample_search_results('pchome')[:3],
            },
            'international_references': {
                'yugioh': card_references.get('yugioh', []),
                'pokemon': card_references.get('pokemon', []),
                'mtg': card_references.get('mtg', [])
            },
            'summary': {
                'pchome_count': len(pchome_results),
                'reference_count': sum(len(cards) for cards in card_references.values()),
                'total': len(pchome_results) + sum(len(cards) for cards in card_references.values())
            }
        })
    
    except Exception as e:
        logger.error(f"組合搜索失敗: {str(e)}")
        return jsonify({'error': '組合搜索失敗'}), 500


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
