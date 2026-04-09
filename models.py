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

