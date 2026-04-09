"""
卡牌價格監控系統 - 資料庫模型
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()

class Card(db.Model):
    """卡牌表"""
    __tablename__ = 'cards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    current_price = db.Column(db.Float, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 關係
    price_history = db.relationship('PriceHistory', backref='card', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Card {self.name}>'
    
    def to_dict(self):
        """轉換為字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image_url': self.image_url,
            'current_price': self.current_price,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PriceHistory(db.Model):
    """價格歷史記錄表"""
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<PriceHistory card_id={self.card_id}, price={self.price}>'
    
    def to_dict(self):
        """轉換為字典格式"""
        return {
            'id': self.id,
            'card_id': self.card_id,
            'price': self.price,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


def init_db(app):
    """初始化資料庫"""
    with app.app_context():
        db.create_all()


def get_database_path():
    """取得資料庫路徑"""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_dir, 'cards.db')
