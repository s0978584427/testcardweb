"""
卡牌價格監控系統 - 資料庫模型 (簡化版)
"""
import sqlite3
from datetime import datetime
import os
import json

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'cards.db')

def get_db_connection():
    """取得資料庫連接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化資料庫"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 建立卡牌表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            image_url TEXT,
            current_price REAL NOT NULL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 建立價格歷史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            price REAL NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id) REFERENCES cards(id)
        )
    ''')
    
    # 建立商品表 (用於存儲來自各平台的商品詳情)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT,
            shop_name TEXT,
            rating REAL,
            url TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(product_id, platform)
        )
    ''')
    
    # 建立搜索歷史表 (用於快速查詢)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            platform TEXT NOT NULL,
            results_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(keyword, platform)
        )
    ''')
    
    conn.commit()
    conn.close()

class Card:
    """卡牌類"""
    
    @staticmethod
    def get_all():
        """取得所有卡牌"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cards')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_id(card_id):
        """根據 ID 取得卡牌"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def create_or_update(name, price, image_url=None, description=None):
        """新增或更新卡牌"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 檢查是否已存在
        cursor.execute('SELECT id FROM cards WHERE name = ?', (name,))
        existing = cursor.fetchone()
        
        if existing:
            card_id = existing[0]
            cursor.execute(
                'UPDATE cards SET current_price = ?, image_url = ?, description = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?',
                (price, image_url, description, card_id)
            )
        else:
            cursor.execute(
                'INSERT INTO cards (name, description, image_url, current_price) VALUES (?, ?, ?, ?)',
                (name, description, image_url, price)
            )
            card_id = cursor.lastrowid
        
        conn.commit()
        
        # 新增價格歷史記錄
        cursor.execute(
            'INSERT INTO price_history (card_id, price) VALUES (?, ?)',
            (card_id, price)
        )
        conn.commit()
        conn.close()
        
        return card_id
    
    @staticmethod
    def to_dict(row=None, card_id=None):
        """轉換為字典"""
        if not row:
            row = Card.get_by_id(card_id)
        if not row:
            return None
        
        return {
            'id': row.get('id') or row[0],
            'name': row.get('name') or row[1],
            'description': row.get('description') or row[2],
            'image_url': row.get('image_url') or row[3],
            'current_price': row.get('current_price') or row[4],
            'last_updated': row.get('last_updated') or row[5],
            'created_at': row.get('created_at') or row[6]
        }

class PriceHistory:
    """價格歷史類"""
    
    @staticmethod
    def get_by_card(card_id, days=30):
        """取得卡牌的價格歷史"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM price_history 
            WHERE card_id = ? 
            AND recorded_at >= datetime('now', '-' || ? || ' days')
            ORDER BY recorded_at ASC
        ''', (card_id, days))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def count():
        """統計價格歷史記錄總數"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM price_history')
        count = cursor.fetchone()[0]
        conn.close()
        return count

class Stats:
    """統計類"""
    
    @staticmethod
    def get_all():
        """取得統計信息"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM cards')
        total_cards = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM price_history')
        price_history_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(current_price) FROM cards')
        avg_price = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_cards': total_cards,
            'price_history_count': price_history_count,
            'average_price': round(float(avg_price), 2)
        }


class Product:
    """商品類 - 存儲各平台的商品信息"""
    
    @staticmethod
    def add_or_update(product_id, platform, name, price, image_url=None, shop_name=None, rating=None, url=None, description=None):
        """新增或更新商品"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (product_id, platform, name, price, image_url, shop_name, rating, url, description, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (product_id, platform, name, price, image_url, shop_name, rating, url, description))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"錯誤: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def search(keyword, platform=None):
        """搜索商品"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if platform:
            cursor.execute('''
                SELECT * FROM products 
                WHERE (name LIKE ? OR description LIKE ?)
                AND platform = ?
                ORDER BY rating DESC, updated_at DESC
                LIMIT 50
            ''', (f'%{keyword}%', f'%{keyword}%', platform))
        else:
            cursor.execute('''
                SELECT * FROM products 
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY rating DESC, updated_at DESC
                LIMIT 50
            ''', (f'%{keyword}%', f'%{keyword}%'))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_id(product_id):
        """根據 ID 取得商品詳情"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def count():
        """統計商品總數"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    @staticmethod
    def count_by_platform():
        """按平台統計商品數"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT platform, COUNT(*) as count
            FROM products
            GROUP BY platform
        ''')
        rows = cursor.fetchall()
        conn.close()
        return {row['platform']: row['count'] for row in rows}


class SearchCache:
    """搜索快取類 - 加快搜索速度"""
    
    @staticmethod
    def get(keyword, platform):
        """取得快取的搜索結果"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT results_json FROM search_cache 
            WHERE keyword = ? AND platform = ? 
            AND expires_at > CURRENT_TIMESTAMP
        ''', (keyword, platform))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    @staticmethod
    def set(keyword, platform, results, ttl_hours=6):
        """存儲搜索結果"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO search_cache 
                (keyword, platform, results_json, expires_at)
                VALUES (?, ?, ?, datetime('now', '+' || ? || ' hours'))
            ''', (keyword, platform, json.dumps(results), ttl_hours))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"快取錯誤: {e}")
            return False
        finally:
            conn.close()

