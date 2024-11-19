from datetime import datetime
from app import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def generate_order_number(cls):
        year = datetime.now().year
        last_order = cls.query.filter(
            cls.order_number.like(f'{year}-%')
        ).order_by(cls.id.desc()).first()
        
        if last_order:
            last_sequence = int(last_order.order_number.split('-')[1])
            new_sequence = str(last_sequence + 1).zfill(3)
        else:
            new_sequence = '001'
            
        return f"{year}-{new_sequence}"

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product', backref='order_items')
    purchase_order = db.relationship('PurchaseOrder', backref='items')
