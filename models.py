from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    sub_county = db.Column(db.String(255), nullable=False)
    landmarks = db.Column(db.Text, nullable=False)
    availability = db.Column(db.String(20), nullable=False)
    viewing_schedule = db.Column(db.String(255), nullable=False)
    features = db.Column(db.Text, nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    is_manager = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, sender_id, recipient_id, property_id, content, timestamp=None, is_manager=False):
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.property_id = property_id
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.is_manager = is_manager