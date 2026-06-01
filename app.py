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

# ===== 增強 CORS 配置 - 支持 Render 和本地開發 =====
cors_config = {
    "origins": [
        "http://localhost:5000",
        "http://localhost:3000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:3000",
    ],
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True,
    "max_age": 3600,
}

# 在 Render 上運行時，動態添加 Render 域名
render_url = os.environ.get('RENDER_EXTERNAL_URL')
if render_url:
    cors_config['origins'].append(render_url)
    logger.info(f"✅ Render 環境檢測: {render_url}")

CORS(app, resources={r"/api/*": cors_config})

# 全局錯誤處理 - 自動響應 CORS 預檢請求
@app.before_request
def handle_preflight():
    """處理 CORS 預檢請求"""
    if request.method == "OPTIONS":
        return "", 204

@app.after_request
def after_request(response):
    """添加額外 CORS 頭"""
    origin = request.headers.get('Origin')
    # 檢查 origin 是否在允許列表中
    if origin and (origin in cors_config['origins'] or (render_url and render_url in origin)):
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# ===== 全局錯誤處理 =====
@app.errorhandler(404)
def not_found(e):
    """404 錯誤處理"""
    logger.warning(f"❌ 404 Not Found: {request.path}")
    return jsonify({'error': '資源不存在', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(e):
    """500 錯誤處理"""
    logger.error(f"❌ 500 Internal Server Error: {str(e)}", exc_info=True)
    return jsonify({'error': '伺服器錯誤', 'details': str(e) if app.debug else None}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """通用異常處理"""
    logger.error(f"❌ 未預期的錯誤 [{type(e).__name__}]: {str(e)}", exc_info=True)
    return jsonify({
        'error': '處理請求時出錯',
        'type': type(e).__name__,
        'details': str(e) if app.debug else None
    }), 500


# ==================== OpenCV 影像辨識 API ====================
@app.route('/api/cards/image-match', methods=['POST'])
def image_match():
    """接收前端傳來的 Base64 圖像，進行 OpenCV 特徵比對並自動查詢官方"""
    try:
        data = request.json
        client_image = data.get('image')
        image_data = client_image # 保留向下相容性或直接取代均可
        
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400
            
        # 處理前端傳來的 Base64 頭部 (如: "data:image/jpeg;base64,/9j/4...")
        if ',' in image_data:
            image_data = image_data.split(',')[1]
            
        import base64
        from database import match_card_image
        
        img_bytes = base64.b64decode(image_data)
        
        # 進行 OpenCV 辨識
        matched_detail, confidence = match_card_image(img_bytes)
        
        if matched_detail and confidence >= 70.0:
            logger.info(f"📸 影像辨識成功: {matched_detail.get('name')} (置信度: {confidence:.2f}%)，直接回傳記憶體快取詳情")
            
            return jsonify({
                'status': 'success',
                'match': matched_detail, # 將整個物件回傳，以匹配前端 data.match.name 的預期
                'confidence': round(confidence, 2),
                'cards': [matched_detail]
            })
        else:
            best_name = matched_detail.get('name') if matched_detail else "None"
            logger.info(f"📸 影像辨識置信度不足或找不到 (最佳: {best_name}, 置信度: {confidence:.2f}%)")
            return jsonify({
                'status': 'fail',
                'error': '找不到匹配的卡面或環境過暗',
                'confidence': round(confidence, 2),
                'match': matched_detail if matched_detail else best_name # 提供有拿到字串就回傳字串，否則如果有結構就盡量提供結構
            }), 200 # 避免 404 造成前端報錯，不夠明確就拋出 200 跟 fail status 給前端繼續 scanning 就好
            
    except Exception as e:
        logger.error(f"📸 影像比對失敗: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

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
        pchome_results = search_pchome(keyword, pages=1)
        
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


# ==================== 後端 Proxy: 卡牌資料獲取 (避免前端 CORS 問題) ====================
@app.route('/api/get_cards', methods=['GET'])
def get_cards_proxy():
    """
    ⭐ 核心路由：後端 Proxy 轉發卡牌資料
    前端不直接請求 pokemontcg.io、ygoprodeck.com、scryfall.com
    改由後端 Python 使用 requests 獲取，規避 CORS 和 IP 封鎖
    
    查詢參數:
        source: 卡牌來源 ('pokemon' | 'yugioh' | 'mtg' | 'tw-pokemon')
        keyword: 搜尋關鍵字
        limit: 結果數 (預設 20)
    """
    import requests
    
    try:
        source = request.args.get('source', '').lower()
        keyword = request.args.get('keyword', '').strip()
        limit = min(int(request.args.get('limit', '20')), 50)  # 最多 50 筆
        
        if not source or not keyword:
            return jsonify({
                'error': '缺少必要參數',
                'required': ['source', 'keyword'],
                'status': 'error'
            }), 400
        
        # 驗證 source 參數
        valid_sources = ['pokemon', 'pokemon-en', 'yugioh', 'mtg', 'tw-pokemon']
        if source not in valid_sources:
            return jsonify({
                'error': f'無效的來源: {source}',
                'valid_sources': valid_sources,
                'status': 'error'
            }), 400
        
        logger.info(f"🌐 [後端 Proxy] 請求卡牌資料: source={source}, keyword={keyword}")
        
        # 模擬 Chrome 瀏覽器請求頭（規避反爬蟲檢測）
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
        }
        
        results = []
        
        # =============== 寶可夢 TCG (pokemontcg.io) ===============
        if source == 'pokemon':
            try:
                import re
                # 檢查是否有中文 (簡單範圍即可: \u4e00-\u9fa5)
                if re.search(r'[\u4e00-\u9fa5]', keyword):
                    return jsonify({
                        'error': '國際 API 僅支援英文關鍵字搜尋，請輸入英文名稱（例如：Pikachu）',
                        'status': 'error',
                        'source': source
                    }), 400
                
                # 若包含 id:xxx 或 number:xxx，改用精準搜尋
                query_str = f'name:"{keyword}"'
                # 國際 API 路線優化：如果在國際 API 輸入 id:sv4a-127 或 number:127
                if re.match(r'^(id|number):', keyword.strip(), re.IGNORECASE):
                    query_str = keyword.strip()
                
                url = f'https://api.pokemontcg.io/v2/cards?q={query_str}&pageSize={limit}'
                logger.debug(f"🌐 [後端 Proxy] 請求 Pokemon TCG: {url}")
                
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()  # 如果狀態碼 >= 400，拋出異常
                
                data = resp.json()
                cards = data.get('data', [])
                
                for card in cards[:limit]:
                    try:
                        images = card.get('images', {})
                        results.append({
                            'id': card.get('id'),
                            'title': card.get('name'),
                            'source': 'pokemon',
                            'img_url': images.get('small', ''),
                            'img_large': images.get('large', ''),
                            'set': card.get('set', {}).get('name', ''),
                            'rarity': card.get('rarity', 'N/A'),
                            'hp': card.get('hp', ''),
                        })
                    except Exception as e:
                        logger.debug(f"❌ [後端 Proxy] 卡牌解析失敗: {e}")
                        continue
                
                logger.info(f"✅ [後端 Proxy] Pokemon TCG 獲取 {len(results)} 張卡牌")
                
            except requests.exceptions.Timeout:
                error_msg = "Pokemon TCG API 請求超時 (>= 10s)"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'timeout',
                    'source': source
                }), 503
            except requests.exceptions.ConnectionError as e:
                error_msg = f"無法連接到 Pokemon TCG API: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'connection_error',
                    'source': source,
                    'details': str(e)
                }), 503
            except Exception as e:
                error_msg = f"Pokemon TCG API 請求失敗: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'api_error',
                    'source': source,
                    'details': str(e)
                }), 500
        
        # =============== 國際英文寶可夢 TCG (新多語系格式) ===============
        elif source == 'pokemon-en':
            try:
                from scraper import CardScraper
                
                logger.info(f"🌐 [後端 Proxy] 請求國際英文寶可夢: {keyword}")
                
                scraper = CardScraper()
                cards = scraper.scrape_pokemon_en(keyword, limit=limit)
                
                # 使用統一的新格式
                for card in cards:
                    try:
                        result = {
                            'id': card.get('id'),
                            'name': card.get('name'),
                            'source': 'pokemon-en',
                            'image_url': card.get('image_url'),
                            'type': card.get('type'),
                            'hp': card.get('hp'),
                            'series': card.get('series'),
                            'number': card.get('number'),
                            'rarity': card.get('rarity'),
                            'skills': card.get('skills', []),
                            'price': card.get('price'),
                        }
                        
                        results.append(result)
                    except Exception as e:
                        logger.debug(f"❌ [後端 Proxy] 英文寶可夢卡牌解析失敗: {e}")
                        continue
                
                logger.info(f"✅ [後端 Proxy] 國際英文寶可夢 獲取 {len(results)} 張卡牌")
                
            except Exception as e:
                error_msg = f"國際英文寶可夢搜尋失敗: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'api_error',
                    'source': source,
                    'details': str(e)
                }), 500
        
        # =============== 遊戲王 (ygoprodeck.com) ===============
        elif source == 'yugioh':
            try:
                url = f'https://db.ygoprodeck.com/api/v7/cardinfo.php?fname={keyword}'
                logger.debug(f"🌐 [後端 Proxy] 請求 YuGiOh: {url}")
                
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                
                data = resp.json()
                cards = data if isinstance(data, list) else data.get('data', [])
                
                for card in cards[:limit]:
                    try:
                        results.append({
                            'id': card.get('id'),
                            'title': card.get('name'),
                            'source': 'yugioh',
                            'img_url': card.get('card_images', [{}])[0].get('image_url', ''),
                            'type': card.get('type'),
                            'attribute': card.get('attribute'),
                            'level': card.get('level'),
                            'atk': card.get('atk'),
                            'def': card.get('def'),
                        })
                    except Exception as e:
                        logger.debug(f"❌ [後端 Proxy] 卡牌解析失敗: {e}")
                        continue
                
                logger.info(f"✅ [後端 Proxy] YuGiOh 獲取 {len(results)} 張卡牌")
                
            except requests.exceptions.Timeout:
                error_msg = "YuGiOh API 請求超時 (>= 10s)"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'timeout',
                    'source': source
                }), 503
            except requests.exceptions.ConnectionError as e:
                error_msg = f"無法連接到 YuGiOh API: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'connection_error',
                    'source': source,
                    'details': str(e)
                }), 503
            except Exception as e:
                error_msg = f"YuGiOh API 請求失敗: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'api_error',
                    'source': source,
                    'details': str(e)
                }), 500
        
        # =============== Magic: The Gathering (scryfall.com) ===============
        elif source == 'mtg':
            try:
                url = f'https://api.scryfall.com/cards/search?q={keyword}&unique=prints'
                logger.debug(f"🌐 [後端 Proxy] 請求 MTG: {url}")
                
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                
                data = resp.json()
                cards = data.get('data', [])
                
                for card in cards[:limit]:
                    try:
                        results.append({
                            'id': card.get('id'),
                            'title': card.get('name'),
                            'source': 'mtg',
                            'img_url': card.get('image_uris', {}).get('normal', ''),
                            'mana_cost': card.get('mana_cost'),
                            'type_line': card.get('type_line'),
                            'power': card.get('power'),
                            'toughness': card.get('toughness'),
                            'rarity': card.get('rarity'),
                        })
                    except Exception as e:
                        logger.debug(f"❌ [後端 Proxy] 卡牌解析失敗: {e}")
                        continue
                
                logger.info(f"✅ [後端 Proxy] MTG 獲取 {len(results)} 張卡牌")
                
            except requests.exceptions.Timeout:
                error_msg = "MTG API 請求超時 (>= 10s)"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'timeout',
                    'source': source
                }), 503
            except requests.exceptions.ConnectionError as e:
                error_msg = f"無法連接到 MTG API: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'connection_error',
                    'source': source,
                    'details': str(e)
                }), 503
            except Exception as e:
                error_msg = f"MTG API 請求失敗: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'api_error',
                    'source': source,
                    'details': str(e)
                }), 500
        
        # =============== 台灣官方寶可夢 TCG (原生繁體中文) ===============
        elif source == 'tw-pokemon':
            try:
                from scraper import CardScraper
                
                logger.info(f"🌐 [後端 Proxy] 請求台灣官方寶可夢: {keyword}")
                
                scraper = CardScraper()
                cards = scraper.scrape_taiwan_pokemon(keyword, limit=limit)
                
                # 使用統一的新格式
                for card in cards:
                    try:
                        # 根據 type (繁中屬性) 設定顏色漸層
                        pokemon_type = card.get('type', '').lower()
                        
                        # 屬性色彩映射 (RGB 漸層)
                        type_colors = {
                            '火': {'primary': '#f08030', 'secondary': '#a81828'},
                            '水': {'primary': '#6890f0', 'secondary': '#38609c'},
                            '草': {'primary': '#78c850', 'secondary': '#486838'},
                            '雷': {'primary': '#f8d030', 'secondary': '#a8a820'},
                            '冰': {'primary': '#98d8d8', 'secondary': '#686860'},
                            '格鬥': {'primary': '#c03028', 'secondary': '#90210e'},
                            '毒': {'primary': '#a040a0', 'secondary': '#782a58'},
                            '地面': {'primary': '#e0c068', 'secondary': '#804020'},
                            '飛行': {'primary': '#a890f0', 'secondary': '#6858a8'},
                            '超': {'primary': '#f85888', 'secondary': '#a82860'},
                            '蟲': {'primary': '#a8b820', 'secondary': '#6d7815'},
                            '岩': {'primary': '#b8a038', 'secondary': '#786824'},
                            '幽靈': {'primary': '#705898', 'secondary': '#493963'},
                            '龍': {'primary': '#7038f8', 'secondary': '#4924a8'},
                            '惡': {'primary': '#705848', 'secondary': '#49392f'},
                            '鋼': {'primary': '#b8b8d0', 'secondary': '#78787c'},
                            '妖精': {'primary': '#ee99ac', 'secondary': '#c23e5b'},
                        }
                        
                        # 預設色彩（如果未找到類型）
                        type_color = type_colors.get(pokemon_type, {
                            'primary': '#a8a878',
                            'secondary': '#6d6d4f'
                        })
                        
                        result = {
                            'id': card.get('id'),
                            'name': card.get('name'),
                            'source': 'tw-pokemon',
                            'image_url': card.get('image_url'),
                            'type': card.get('type'),
                            'hp': card.get('hp'),
                            'series': card.get('series'),
                            'number': card.get('number'),
                            'rarity': card.get('rarity'),
                            'skills': card.get('skills', []),
                            'price': card.get('price'),
                            'type_color': type_color,  # 前端用於 Modal 背景漸層
                            'text_style': {
                                'color': 'white',
                                'text_shadow': '1px 1px 2px rgba(0, 0, 0, 0.8)'  # 黑影效果
                            }
                        }
                        
                        results.append(result)
                    except Exception as e:
                        logger.debug(f"❌ [後端 Proxy] 台灣寶可夢卡牌解析失敗: {e}")
                        continue
                
                logger.info(f"✅ [後端 Proxy] 台灣官方寶可夢 獲取 {len(results)} 張卡牌")
                
            except Exception as e:
                error_msg = f"台灣官方寶可夢搜尋失敗: {str(e)}"
                logger.error(f"❌ [後端 Proxy] {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'status': 'api_error',
                    'source': source,
                    'details': str(e)
                }), 500
        
        # ✅ 成功返回結果
        return jsonify({
            'source': source,
            'keyword': keyword,
            'results': results,
            'total': len(results),
            'status': 'success',
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"❌ [後端 Proxy] 未預期的錯誤: {str(e)}", exc_info=True)
        return jsonify({
            'error': '後端處理錯誤',
            'details': str(e),
            'type': type(e).__name__,
            'status': 'error'
        }), 500


# ==================== 新版分頁搜尋 (支持三個平台) ====================
@app.route('/api/cards/search', methods=['GET'])
def search_cards_paginated():
    """
    新版卡牌搜尋 API - 支持分頁、詳細信息、發行版本清單
    
    查詢參數:
        keyword: 搜尋關鍵字
        source: 卡牌來源 ('pokemon' | 'yugioh' | 'mtg' | 'all')
        page: 頁碼 (預設 1)
        limit: 每頁結果數 (預設 20)
    """
    try:
        from card_apis import (
            get_pokemon_tcg_cards, 
            get_yugioh_cards, 
            get_magic_cards,
            search_all_cards_paginated
        )
        
        keyword = request.args.get('keyword', '').strip()
        source = request.args.get('source', 'all').lower()
        page = int(request.args.get('page', '1'))
        limit = min(int(request.args.get('limit', '20')), 20)  # 最多 20 筆
        
        if not keyword or len(keyword) < 2:
            return jsonify({'error': '搜索關鍵字至少 2 個字符'}), 400
        
        if page < 1:
            page = 1
        
        # 驗證 source 參數
        valid_sources = ['pokemon', 'pokemon-en', 'yugioh', 'mtg', 'tw-pokemon', 'all']
        if source not in valid_sources:
            logger.warning(f"⚠️ 無效的卡牌來源: {source}. 有效選項: {valid_sources}")
            return jsonify({
                'error': f'無效的卡牌來源: {source}',
                'valid_sources': valid_sources
            }), 400
        
        logger.info(f"🔍 搜尋卡牌: keyword={keyword}, source={source}, page={page}, limit={limit}")
        
        # 根據來源進行搜索
        if source == 'pokemon':
            result = get_pokemon_tcg_cards(keyword, limit, page)
            return jsonify({
                'keyword': keyword,
                'source': 'pokemon',
                **result
            })
        
        elif source == 'pokemon-en':
            # 國際英文寶可夢 - 新多語系格式
            from scraper import CardScraper
            scraper = CardScraper()
            cards = scraper.scrape_pokemon_en(keyword, limit=limit*2)  # 額外獲取以備分頁
            
            # 應用分頁
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_cards = cards[start_idx:end_idx]
            
            return jsonify({
                'keyword': keyword,
                'source': 'pokemon-en',
                'cards': paginated_cards,
                'total': len(cards),
                'current_page': page,
                'pages': (len(cards) + limit - 1) // limit  # 向上取整
            })
        
        elif source == 'tw-pokemon':
            # 台灣官方寶可夢
            from scraper import CardScraper
            scraper = CardScraper()
            cards = scraper.scrape_taiwan_pokemon(keyword, limit=limit*2)  # 額外獲取以備分頁
            
            # 應用分頁
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_cards = cards[start_idx:end_idx]
            
            return jsonify({
                'keyword': keyword,
                'source': 'tw-pokemon',
                'cards': paginated_cards,
                'total': len(cards),
                'current_page': page,
                'pages': (len(cards) + limit - 1) // limit  # 向上取整
            })
        
        elif source == 'yugioh':
            result = get_yugioh_cards(keyword, limit, page)
            return jsonify({
                'keyword': keyword,
                'source': 'yugioh',
                **result
            })
        
        elif source == 'mtg':
            result = get_magic_cards(keyword, limit, page)
            return jsonify({
                'keyword': keyword,
                'source': 'mtg',
                **result
            })
        
        else:  # 'all' - 搜尋所有來源
            results = search_all_cards_paginated(keyword, limit, page)
            return jsonify({
                'keyword': keyword,
                'source': 'all',
                'results': results
            })
    
    except Exception as e:
        logger.error(f"❌ 卡牌搜尋異常 [{type(e).__name__}]: {str(e)}", exc_info=True)
        error_msg = str(e)
        return jsonify({
            'error': '搜尋失敗',
            'details': error_msg,  # 始終返回詳細錯誤信息（便於客戶端調試）
            'type': type(e).__name__,
            'keyword': keyword,
            'source': source,
            'status': 'error'
        }), 500


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
        pchome_results = search_pchome(keyword, pages=1)
        
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



# 在伺服器啟動時於背景載入特徵
import threading
from database import initialize_online_features
threading.Thread(target=initialize_online_features, daemon=True).start()

if __name__ == '__main__':

    # 動態讀取環境變數 Port (相容 Render)
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=os.environ.get('FLASK_ENV') == 'development',
        host='0.0.0.0',
        port=port
    )
