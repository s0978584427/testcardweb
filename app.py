"""
卡牌價格監控系統 - 優化版本 (只保留必要功能)
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
import os

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# 初始化 Flask 應用
app = Flask(__name__)
CORS(app)


# ==================== 主頁 ====================
@app.route('/')
def index():
    """首頁 - 卡牌查詢系統"""
    return render_template('index.html')


# ==================== 搜尋 API ====================
@app.route('/api/search', methods=['GET'])
def search_cards():
    """搜索卡牌 - 使用 PChome 官方 API"""
    try:
        from scraper import search_pchome
        
        keyword = request.args.get('keyword', '').strip()
        if not keyword or len(keyword) < 2:
            return jsonify({'error': '搜索關鍵字至少 2 個字符'}), 400
        
        logger.info(f"PChome 搜尋: {keyword}")
        pchome_results = search_pchome(keyword, pages=20)
        
        return jsonify({
            'keyword': keyword,
            'results': {'pchome': pchome_results},
            'total_results': len(pchome_results)
        })
    
    except Exception as e:
        logger.error(f"搜尋失敗: {str(e)}")
        return jsonify({'error': '搜尋失敗'}), 500


@app.route('/api/recommended', methods=['GET'])
def get_recommended():
    """首頁推薦商品"""
    try:
        from scraper import search_pchome
        
        logger.info("取得推薦商品...")
        pchome_results = search_pchome('遊戲王', pages=1)
        
        return jsonify({
            'results': {'pchome': pchome_results[:5] if pchome_results else []},
            'total': len(pchome_results)
        })
    
    except Exception as e:
        logger.error(f"取得推薦失敗: {str(e)}")
        return jsonify({'error': '取得推薦失敗'}), 500


# ==================== 卡牌參考資料 API ====================
@app.route('/api/card-references', methods=['GET'])
def get_card_references():
    """取得國際卡牌參考資料 (YGOProDeck, PokeAPI, Scryfall)"""
    try:
        from card_apis import get_all_card_sources
        
        keyword = request.args.get('keyword', '').strip()
        if not keyword or len(keyword) < 2:
            return jsonify({'error': '搜索關鍵字至少 2 個字符'}), 400
        
        logger.info(f"搜尋卡牌資料: {keyword}")
        card_data = get_all_card_sources(keyword)
        
        return jsonify({
            'keyword': keyword,
            'references': {
                'yugioh': card_data.get('yugioh', []),
                'pokemon': card_data.get('pokemon', []),
                'mtg': card_data.get('mtg', [])
            },
            'total_references': sum(len(cards) for cards in card_data.values())
        })
    
    except Exception as e:
        logger.error(f"取得卡牌資料失敗: {str(e)}")
        return jsonify({'error': '取得卡牌資料失敗'}), 500


# ==================== 組合搜尋 ====================
@app.route('/api/combined-search', methods=['GET'])
def combined_search():
    """台灣價格 + 國際卡牌資料"""
    try:
        from scraper import search_pchome
        from card_apis import get_all_card_sources
        
        keyword = request.args.get('keyword', '').strip()
        if not keyword or len(keyword) < 2:
            return jsonify({'error': '搜索關鍵字至少 2 個字符'}), 400
        
        logger.info(f"組合搜尋: {keyword}")
        
        # 台灣商品
        pchome_results = search_pchome(keyword, pages=20)
        
        # 國際卡牌資料
        card_refs = get_all_card_sources(keyword)
        
        return jsonify({
            'keyword': keyword,
            'taipei_prices': {'pchome': pchome_results[:5] if pchome_results else []},
            'international_references': {
                'yugioh': card_refs.get('yugioh', []),
                'pokemon': card_refs.get('pokemon', []),
                'mtg': card_refs.get('mtg', [])
            },
            'summary': {
                'pchome_count': len(pchome_results),
                'reference_count': sum(len(cards) for cards in card_refs.values())
            }
        })
    
    except Exception as e:
        logger.error(f"組合搜尋失敗: {str(e)}")
        return jsonify({'error': '組合搜尋失敗'}), 500


# ==================== 錯誤處理 ====================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '資源未找到'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"伺服器錯誤: {str(error)}")
    return jsonify({'error': '伺服器內部錯誤'}), 500


if __name__ == '__main__':
    # 開發環境配置
    app.run(
        debug=os.environ.get('FLASK_ENV') == 'development',
        host='0.0.0.0',
        port=5000
    )
