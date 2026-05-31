import cv2
import numpy as np
import os
import glob
import logging

logger = logging.getLogger(__name__)

# 初始化 ORB 特徵偵測器 (可針對需求提昇保留的特徵點數量)
orb = cv2.ORB_create(nfeatures=1000)

# 建立特徵匹配器 (ORB 使用 Hamming Distance 做為基準是最好的)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

# 全域預載的卡牌影像資料庫
IMAGE_DB = {}

def load_image_database(db_path='card_images'):
    """加載資料庫中的卡牌並提取特徵"""
    global IMAGE_DB
    
    if not os.path.exists(db_path):
        os.makedirs(db_path, exist_ok=True)
        logger.info(f"[Image DB] 建立圖像庫夾: {db_path}，請將測試實體原圖放入此處 (例: 皮卡丘.jpg)")
        return

    logger.info(f"[Image DB] 正在從 {db_path} 讀取實體卡原圖...")
    
    # 清空以備重新載入
    IMAGE_DB = {}
    
    loaded_count = 0
    for file_path in glob.glob(os.path.join(db_path, '*.*')):
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        if ext.lower() not in ['.jpg', '.jpeg', '.png']:
            continue
            
        # 以灰階讀取影像
        img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        
        # 為了比對效率可以縮放一下過大的原圖
        height, width = img.shape
        if max(height, width) > 1000:
            scale = 1000 / max(height, width)
            img = cv2.resize(img, (0, 0), fx=scale, fy=scale)
            
        # 計算特徵點與特徵描述子
        kp, des = orb.detectAndCompute(img, None)
        
        if des is not None:
            # 以檔名直接當作識別結果，例如 "皮卡丘"
            IMAGE_DB[name] = {
                'keypoints': kp,
                'descriptors': des,
                'name': name
            }
            loaded_count += 1
            logger.info(f"[Image DB] 已註冊特徵: {name}")

    logger.info(f"[Image DB] 初始化完成，已載入 {loaded_count} 張卡牌特徵")

# 初始化時自動加載
load_image_database()

def match_card_image(client_image_bytes):
    """
    接收 Base64 解析出的圖檔 Bytes 並回傳最近似的卡名與置信度 (0~100)
    """
    global IMAGE_DB
    if not IMAGE_DB:
        logger.warning("[Image DB] 電腦視覺庫目前為空，請在 'card_images/' 加入圖檔！")
        return None, 0.0

    # 將 bytes 轉為 numpy array 再由 opencv 解碼成影像 (灰階)
    nparr = np.frombuffer(client_image_bytes, np.uint8)
    client_img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    if client_img is None:
        logger.error("[Image DB] 無法解析此相機傳來的圖像 bytes")
        return None, 0.0

    # 計算相機畫面的特徵點
    kp_client, des_client = orb.detectAndCompute(client_img, None)
    
    if des_client is None or len(des_client) == 0:
        return None, 0.0

    best_match_name = None
    max_good_matches = 0
    
    # 和資料庫內的每張卡片輪流過招
    for name, db_data in IMAGE_DB.items():
        des_db = db_data['descriptors']
        if des_db is None or len(des_db) == 0:
            continue
            
        # 計算特徵點的距離
        matches = bf.match(des_client, des_db)
        # 基於 Hamming Distance 排序 (越低越好)
        matches = sorted(matches, key=lambda x: x.distance)
        
        # 篩選掉相似度差的點 (這是一個魔法數字，依照光線環境大約定在 40~50)
        # ORB 在 NORM_HAMMING 下，distance 小於 45 表示點的長相極度雷同
        good_matches = [m for m in matches if m.distance < 45]
        
        # 如果過濾後的匹配點大於現在保存的最高紀錄
        if len(good_matches) > max_good_matches:
            max_good_matches = len(good_matches)
            best_match_name = name

    # 由於 ORB 找 1000 個點，我們定義超過 15 個極端好的點就是認出了卡片
    # 最高算 100% 分數（這個公式可以隨意調整寬容度）
    confidence = min(100.0, (max_good_matches / 15.0) * 100)
    
    logger.debug(f"[CV Engine] 最高配對: {best_match_name}，吻合特徵點數: {max_good_matches}，置信度 {confidence:.1f}%")
        
    return best_match_name, confidence
