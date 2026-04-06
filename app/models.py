# app/models.py
from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    stock_history = db.relationship('StockHistory', backref='item', lazy=True,
                                    cascade='all, delete-orphan',
                                    order_by='StockHistory.recorded_at')

    @property
    def value(self):
        return self.quantity * self.price


class StockHistory(db.Model):
    """Records a stock snapshot every time an item quantity changes."""
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'quantity': self.quantity,
            'recorded_at': self.recorded_at.strftime('%Y-%m-%d %H:%M') if self.recorded_at else 'N/A'
        }


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending, paid, cancelled
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    customer = db.relationship('Customer', backref=db.backref('invoices', lazy=True))

