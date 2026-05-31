import cv2
import numpy as np
import logging
import requests
from scraper import CardScraper

logger = logging.getLogger(__name__)

# 初始化 ORB 特徵偵測器 (提昇特徵點數量)
orb = cv2.ORB_create(nfeatures=1000)

# 建立特徵匹配器 (ORB 使用 Hamming Distance 做為基準)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

# 全域預載的線上卡牌影像資料庫
ONLINE_CARD_FEATURES = {}

def initialize_online_features():
    """啟動時自動呼叫爬蟲，獲取熱門卡牌並在記憶體建立特徵庫"""
    global ONLINE_CARD_FEATURES
    ONLINE_CARD_FEATURES = {}
    
    logger.info("[CV Engine] 開始從官方爬蟲抓取線上卡牌圖片建立動態特徵庫...")
    
    scraper = CardScraper()
    # 熱門關鍵字，可隨需求擴增。利用這些關鍵字到台灣官方找尋卡片。
    keywords = ["皮卡丘", "噴火龍", "伊布", "超夢", "蒼炎刃鬼", "奇魯莉安"]
    
    for kw in keywords:
        logger.info(f"[CV Engine] 網路抓取熱門關鍵字: '{kw}'")
        cards = scraper.scrape_taiwan_pokemon(kw, limit=5)
        
        for card in cards:
            name = card.get('name', '未命名')
            # 將搜尋字眼改為顯示其卡號或真正的特徵名字
            display_name = f"{name} ({card.get('number', '未知')})"
            
            img_url = card.get('image_url')
            if not img_url:
                continue
                
            card_id = card.get('id', img_url)
            
            if card_id in ONLINE_CARD_FEATURES:
                continue
                
            try:
                # 串流讀取線上圖片，不落地
                resp = requests.get(img_url, stream=True, timeout=10)
                if resp.status_code == 200:
                    img_array = np.asarray(bytearray(resp.raw.read()), dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
                    
                    if img is None:
                        logger.warning(f"[CV Engine] 圖片解碼失敗: {img_url}")
                        continue
                        
                    height, width = img.shape
                    if max(height, width) > 1000:
                        scale = 1000 / max(height, width)
                        img = cv2.resize(img, (0, 0), fx=scale, fy=scale)
                        
                    kp, des = orb.detectAndCompute(img, None)
                    
                    if des is not None:
                        ONLINE_CARD_FEATURES[card_id] = {
                            'keypoints': kp,
                            'descriptors': des,
                            'name': display_name,
                            'detail': card  # 將官方繁中詳情儲存
                        }
                        logger.info(f"[CV Engine] 成功快取線上特徵: {display_name} (特徵點數: {len(kp)})")
            except Exception as e:
                logger.error(f"[CV Engine] 讀取線上圖片失敗 {img_url}: {e}")

    logger.info(f"[CV Engine] 動態特徵庫初始化完成！共緩存 {len(ONLINE_CARD_FEATURES)} 張官方卡牌。")

def match_card_image(client_image_bytes):
    """
    接收 Base64 表單 Bytes，對比記憶體內動態爬取的特徵點，直接回傳最佳相符的官方詳情 (JSON dict)
    """
    global ONLINE_CARD_FEATURES
    if not ONLINE_CARD_FEATURES:
        logger.warning("[CV Engine] 線上特徵庫尚未準備就緒或為空。")
        return None, 0.0

    nparr = np.frombuffer(client_image_bytes, np.uint8)
    client_img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    if client_img is None:
        logger.error("[CV Engine] 無法解析相機傳來的圖像 bytes")
        return None, 0.0

    kp_client, des_client = orb.detectAndCompute(client_img, None)
    
    if des_client is None or len(des_client) == 0:
        return None, 0.0

    best_match_detail = None
    best_match_name = "None"
    max_good_matches = 0
    
    for card_id, db_data in ONLINE_CARD_FEATURES.items():
        des_db = db_data['descriptors']
        if des_db is None or len(des_db) == 0:
            continue
            
        matches = bf.match(des_client, des_db)
        matches = sorted(matches, key=lambda x: x.distance)
        
        # distance 小於 45 表特徵極度雷同
        good_matches = [m for m in matches if m.distance < 45]
        
        if len(good_matches) > max_good_matches:
            max_good_matches = len(good_matches)
            best_match_detail = db_data['detail']
            best_match_name = db_data['name']

    # 超過 15 個極端好的點就是認出了卡片
    confidence = min(100.0, (max_good_matches / 15.0) * 100)
    
    if best_match_detail:
        logger.debug(f"[CV Engine] 最高配對: {best_match_name}，吻合特徵數: {max_good_matches}，置信度 {confidence:.1f}%")
        
    return best_match_detail, confidence
